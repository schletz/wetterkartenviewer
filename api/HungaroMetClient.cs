using System.Globalization;
using System.IO.Compression;
using System.Text.RegularExpressions;

namespace StationProxy;

/// <summary>
/// Reads the open data server of HungaroMet (https://odp.met.hu), which sends no CORS header, so a browser cannot.
/// Terms of use: https://odp.met.hu/ODP_General_Term_of_Use.pdf (the source must be cited).
/// </summary>
public sealed partial class HungaroMetClient(IHttpClientFactory httpClients)
{
    /// <summary>Name of the configured <see cref="HttpClient"/>.</summary>
    public const string HttpClientName = "hungaromet";

    /// <summary>Root of the open data server.</summary>
    public static readonly Uri BaseAddress = new("https://odp.met.hu/");

    private const string SynopFolder = "weather/weather_reports/synoptic/hungary/10_minutes";
    private const string StationArchiveFolder = "climate/observations_hungary/10_minutes/recent";
    private const string TimeFormat = "yyyyMMddHHmm";
    private const double MissingValue = -999;

    /// <summary>A file name carries the second it was written, so only the listing tells the names.</summary>
    [GeneratedRegex(@"HABP_10M_SYNOP_\d{14}\.csv\.zip")]
    private static partial Regex SynopFileName();

    /// <summary>Names of the 10 min files with all stations, one per transmission of the last 24 hours, oldest first.</summary>
    public async Task<IReadOnlyList<string>> ListSynopFilesAsync(CancellationToken cancellation)
    {
        var listing = await Client().GetStringAsync($"{SynopFolder}/csv/", cancellation);
        return [.. SynopFileName().Matches(listing).Select(match => match.Value).Distinct().Order(StringComparer.Ordinal)];
    }

    /// <summary>All stations of one 10 min file; it holds the newest slot of most stations and the slot before of a few.</summary>
    public Task<IReadOnlyList<StationReport>> ReadSynopFileAsync(string name, CancellationToken cancellation) =>
        ReadZippedTableAsync<IReadOnlyList<StationReport>>($"{SynopFolder}/csv/{name}", table =>
        {
            var (id, stationName, latitude, longitude, altitude) = (table.Column("StationNumber"), table.Column("StationName"),
                table.Column("Latitude"), table.Column("Longitude"), table.Column("Elevation"));
            var parse = MeasurementParser(table);
            return [.. table.Rows().Select(cells => new StationReport(
                new StationInfo(cells[id].Trim(), cells[stationName].Trim(), Number(cells[latitude]), Number(cells[longitude]), Number(cells[altitude])),
                parse(cells)))];
        }, cancellation);

    /// <summary>
    /// Measurements of one station since a time, from its archive of the current year
    /// (about 1.3 MB, written once a day, so it ends with the day before or the one before that).
    /// </summary>
    public Task<IReadOnlyList<Measurement>> ReadStationArchiveAsync(string stationId, DateTime since, CancellationToken cancellation) =>
        ReadZippedTableAsync<IReadOnlyList<Measurement>>($"{StationArchiveFolder}/HABP_10M_{stationId}_akt.zip", table =>
        {
            var time = table.Column("Time");
            var first = since.ToString(TimeFormat, CultureInfo.InvariantCulture);
            var parse = MeasurementParser(table);
            // Ordinal order of the time stamps is their order in time.
            return [.. table.Rows().Where(cells => string.CompareOrdinal(cells[time].Trim(), first) >= 0).Select(parse)];
        }, cancellation);

    /// <summary>County of every station; a station with several periods has one row each, the last one counts.</summary>
    public async Task<IReadOnlyDictionary<string, string>> ReadRegionsAsync(CancellationToken cancellation)
    {
        await using var stream = await Client().GetStreamAsync($"{SynopFolder}/station_meta_auto.csv", cancellation);
        using var reader = new StreamReader(stream);
        var table = new SemicolonTable(reader);
        var (id, region) = (table.Column("StationNumber"), table.Column("RegioName"));
        var regions = new Dictionary<string, string>();
        foreach (var cells in table.Rows())
            regions[cells[id].Trim()] = cells[region].Trim();
        return regions;
    }

    private HttpClient Client() => httpClients.CreateClient(HttpClientName);

    private async Task<T> ReadZippedTableAsync<T>(string path, Func<SemicolonTable, T> read, CancellationToken cancellation)
    {
        var bytes = await Client().GetByteArrayAsync(path, cancellation);
        using var archive = new ZipArchive(new MemoryStream(bytes), ZipArchiveMode.Read);
        using var reader = new StreamReader(archive.Entries[0].Open());
        return read(new SemicolonTable(reader));
    }

    private static Func<string[], Measurement> MeasurementParser(SemicolonTable table)
    {
        var (time, temperature, minimum, maximum) = (table.Column("Time"), table.Column("t"), table.Column("tn"), table.Column("tx"));
        return cells => new Measurement(
            DateTime.SpecifyKind(DateTime.ParseExact(cells[time].Trim(), TimeFormat, CultureInfo.InvariantCulture), DateTimeKind.Utc),
            Temperature(cells[temperature]), Temperature(cells[minimum]), Temperature(cells[maximum]));
    }

    private static double Number(string cell) => double.Parse(cell, NumberStyles.Float, CultureInfo.InvariantCulture);

    private static double? Temperature(string cell) =>
        double.TryParse(cell, NumberStyles.Float, CultureInfo.InvariantCulture, out var value) && value > MissingValue ? value : null;
}
