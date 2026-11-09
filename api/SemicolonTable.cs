namespace StationProxy;

/// <summary>
/// Reader for the text tables of HungaroMet: cells separated by semicolons and padded with spaces.
/// Lines before the header start with # or are empty.
/// </summary>
public sealed class SemicolonTable
{
    private readonly TextReader _reader;
    private readonly Dictionary<string, int> _columns = [];

    /// <summary>Reads up to and including the header line.</summary>
    /// <exception cref="InvalidDataException">The text has no header line.</exception>
    public SemicolonTable(TextReader reader)
    {
        _reader = reader;
        var header = NextDataLine() ?? throw new InvalidDataException("table without a header line");
        var names = header.Split(';');
        for (var i = 0; i < names.Length; i++)
            _columns[names[i].Trim()] = i;
    }

    /// <summary>Position of a column in the cells of a row.</summary>
    /// <exception cref="KeyNotFoundException">The table has no such column.</exception>
    public int Column(string name) => _columns[name];

    /// <summary>The remaining rows; cells are not trimmed, so rows that get skipped cost little.</summary>
    public IEnumerable<string[]> Rows()
    {
        while (NextDataLine() is { } line)
        {
            var cells = line.Split(';');
            // A row cut off by a transmission error is shorter than the header.
            if (cells.Length >= _columns.Count)
                yield return cells;
        }
    }

    private string? NextDataLine()
    {
        while (_reader.ReadLine() is { } line)
        {
            if (line.Length > 0 && line[0] != '#' && !string.IsNullOrWhiteSpace(line))
                return line;
        }
        return null;
    }
}
