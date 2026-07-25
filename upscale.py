"""Magic Kernel Sharp resampling for text heavy graphics.

Lanczos and bicubic filters blur thin glyph strokes when a chart is
magnified. Magic Kernel Sharp (John Costella, 2013) combines the
magic kernel - the quadratic B-spline

    m(x) = 3/4 - x^2            for |x| <= 1/2
    m(x) = (3/2 - |x|)^2 / 2    for 1/2 < |x| <= 3/2
    m(x) = 0                    otherwise

with a sharpening filter that cancels the blur the kernel introduces.
For magnification the sharpening runs on the source grid, because that
is the coarser of the two grids.
"""

import numpy as np
from PIL import Image

# Sharpening filter of Magic Kernel Sharp 2013, applied on the coarse
# grid; the taps sum to one so overall brightness is preserved.
SHARP_TAPS = np.array([-0.25, 1.5, -0.25])


def _magic_kernel(x):
    """Evaluate the magic kernel for an array of offsets."""
    ax = np.abs(x)
    return np.where(ax <= 0.5, 0.75 - ax ** 2,
                    np.where(ax <= 1.5, 0.5 * (1.5 - ax) ** 2, 0.0))


def _sharpen_axis(data, axis):
    """Apply the sharpening taps along one axis with edge clamping."""
    prev = np.take(data, np.clip(np.arange(data.shape[axis]) - 1, 0, None),
                   axis=axis)
    nxt = np.take(data, np.clip(np.arange(data.shape[axis]) + 1, None,
                                data.shape[axis] - 1), axis=axis)
    return (SHARP_TAPS[0] * prev + SHARP_TAPS[1] * data
            + SHARP_TAPS[2] * nxt)


def _resample_axis(data, axis, out_size):
    """Resample one axis to out_size samples using the magic kernel."""
    in_size = data.shape[axis]
    scale = out_size / in_size
    # Centre of each output pixel expressed in source pixel indices.
    centres = (np.arange(out_size) + 0.5) / scale - 0.5
    # Magnification keeps the kernel support at 1.5 source pixels; for
    # minification it has to grow with the sampling distance.
    radius = 1.5 / min(scale, 1.0)
    offsets = np.arange(-int(np.ceil(radius)), int(np.ceil(radius)) + 1)
    indices = np.clip(np.round(centres)[:, None] + offsets, 0, in_size - 1)
    weights = _magic_kernel((centres[:, None] - (np.round(centres)[:, None]
                                                 + offsets)) * min(scale, 1.0))
    weights /= weights.sum(axis=1, keepdims=True)

    # Gathering replaces the sampled axis by (out_size, taps); move both
    # to the front, contract with the weights, restore the axis order.
    taken = np.take(data, indices.astype(np.intp), axis=axis)
    moved = np.moveaxis(taken, (axis, axis + 1), (0, 1))
    return np.moveaxis(np.einsum("ok...,ok->o...", moved, weights), 0, axis)


def magic_kernel_sharp_resize(image, size):
    """Resize a PIL image with the Magic Kernel Sharp filter.

    Args:
        image: source PIL image (any mode convertible to RGB/RGBA).
        size: target size as (width, height) in pixels.

    Returns:
        A new PIL image of the requested size in the source mode.
    """
    mode = image.mode if image.mode in ("RGB", "RGBA", "L") else "RGB"
    data = np.asarray(image.convert(mode), dtype=np.float64)
    if data.ndim == 2:
        data = data[:, :, None]

    out_w, out_h = size
    # Sharpen on the source grid where the image is magnified, then
    # interpolate; axis 0 is y, axis 1 is x.
    if out_h > data.shape[0]:
        data = _sharpen_axis(data, 0)
    data = _resample_axis(data, 0, out_h)
    if out_w > data.shape[1]:
        data = _sharpen_axis(data, 1)
    data = _resample_axis(data, 1, out_w)

    data = np.clip(data, 0, 255).astype(np.uint8)
    if data.shape[2] == 1:
        data = data[:, :, 0]
    return Image.fromarray(data, mode)
