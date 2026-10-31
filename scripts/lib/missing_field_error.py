"""Error of a field that a forecast file lacks or holds with missing values only."""


class MissingFieldError(KeyError):
    """A field is not in the file, or the server's message was lost and only a missing value placeholder is there.

    A KeyError, so callers that look fields up keep working; render_charts.py
    draws a "No data available" chart for it.
    """
