"""Areas between a T850 series and its climate mean, layered in steps of the standard deviation.

The class knows nothing about SVG; vertices come as (x, value) and the
caller maps them onto its drawing.
"""

WARM, COLD = 1, -1


class AnomalyBands:
    """Polygons of the parts of a series beyond mean + k sigma (warm) or below mean - k sigma (cold)."""

    def __init__(self, sigma_steps: tuple):
        """Set the layers.

        Args:
            sigma_steps: the values of k, e.g. (0, 1, 2, 3); 0 is the mean itself.
        """
        self.sigma_steps = sigma_steps

    def polygons(self, points: list) -> list[tuple[int, list[tuple[float, float]]]]:
        """Polygons of the T850 anomaly, layered in steps of the standard deviation.

        For every k of the sigma steps, polygons cover the part of T850 above
        mean + k sigma (WARM) and below mean - k sigma (COLD). Drawn on top of
        each other with some transparency, they shade the anomaly darker with
        every sigma.

        Args:
            points: per valid time (x, t850, mean, std), or None where a value
                is missing, which breaks the areas; x is the horizontal
                position, e.g. the pixel column.

        Returns:
            (side, vertices) per polygon, side WARM or COLD; the vertices run
            along T850 and back along the threshold as (x, value).
        """
        polygons = []
        for step in self.sigma_steps:
            for side in (WARM, COLD):
                series = [None if point is None else (point[0], point[1], point[2] + side * step * point[3])
                          for point in points]
                for run in self._runs_beyond(series, side):
                    vertices = [(x, t850) for x, t850, _ in run] + [(x, threshold) for x, _, threshold in reversed(run)]
                    polygons.append((side, vertices))
        return polygons

    @staticmethod
    def _runs_beyond(series: list, side: int) -> list[list[tuple[float, float, float]]]:
        """Runs of (x, t850, threshold) where T850 lies beyond the threshold on ``side``.

        A segment that crosses the threshold is split at the crossing, so the
        areas end exactly there. Consecutive pieces on the same side form one
        run, which avoids seams between adjacent polygons.
        """
        points = []  # the series with the crossings inserted; None breaks it
        previous = None
        for current in series:
            if current is None:
                points.append(None)
                previous = None
                continue
            if previous is not None:
                before, after = previous[1] - previous[2], current[1] - current[2]
                if before * after < 0:
                    share = before / (before - after)
                    x = previous[0] + share * (current[0] - previous[0])
                    value = previous[1] + share * (current[1] - previous[1])
                    points.append((x, value, value))
            points.append(current)
            previous = current

        runs, run, sign = [], [], 0
        for point in points + [None]:
            difference = 0 if point is None else point[1] - point[2]
            point_sign = (difference > 0) - (difference < 0)
            if point is None or (point_sign and sign and point_sign != sign):
                if sign == side and len(run) >= 2:
                    runs.append(run)
                # The next run starts at the crossing that ended this one.
                run, sign = ([] if point is None else [run[-1]]), 0
            if point is not None:
                run.append(point)
                sign = sign or point_sign
        return runs
