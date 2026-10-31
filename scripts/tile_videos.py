"""Encode the charts of one tile layer into an AV1 video, one frame per forecast step.

The viewer loads one video per layer instead of 65 single images and seeks
to the frame of a step. The settings come from a comparison of encoders on
z500_t850 against the lossless charts (laut User): libaom at CRF 20 with
cpu-used 6 and tune-content=screen gives the same quality as WebP q90 at
about 40 % of its size; screen tuning switches on palette mode and intra
block copy, which suit flat colours and lines. A keyframe every 8 frames
keeps a seek to any step short.

Requires ffmpeg with libaom-av1 on the PATH and Pillow.
"""

import subprocess
from pathlib import Path

from PIL import Image

from maps_manifest import FPS

WIDTH, HEIGHT = 1200, 690
KEYFRAME_INTERVAL = 8
# libaom-av1, CRF 20, cpu-used 6, tune-content=screen, 4:2:0, keyframe every 8 frames.
CODEC = ["-c:v", "libaom-av1", "-crf", "20", "-b:v", "0", "-cpu-used", "6",
         "-aom-params", "tune-content=screen", "-g", str(KEYFRAME_INTERVAL)]
# The charts are sRGB; tagging BT.709 lets browsers convert the colours back exactly as encoded.
COLOUR = ["-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
          "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]


def encode_video(frames: list[Path], target: Path) -> None:
    """Write the charts ``frames`` in this order as MP4 to ``target``.

    The video is written to <target>.part first, so an interrupted run never
    leaves a file that looks complete.

    Raises:
        RuntimeError: if ffmpeg fails.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-",
               *CODEC, *COLOUR, "-movflags", "+faststart", "-an", "-f", "mp4", str(part)]
    with subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        try:
            for frame in frames:
                with Image.open(frame) as image:
                    process.stdin.write(image.convert("RGB").tobytes())
        finally:
            process.stdin.close()
        errors = process.stderr.read().decode("utf-8", "replace")
    if process.returncode:
        part.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg failed for {target}:\n{errors}")
    part.replace(target)
