using System.Globalization;

namespace StationProxy;

/// <summary>
/// Builds the JSON bodies in the shape of the GeoSphere Austria data hub, so that the web app reads
/// both networks with the same code. Property names are the wire format.
/// </summary>
public static class DataHubResponses
{
    /// <summary>Body of the metadata request.</summary>
    public static object Metadata(IEnumerable<(StationInfo Info, string Region)> stations) => new
    {
        stations = stations.Select(station => new
        {
            id = station.Info.Id,
            name = station.Info.Name,
            state = station.Region,
            lat = station.Info.Latitude,
            lon = station.Info.Longitude,
            altitude = station.Info.Altitude,
            is_active = true,
        }),
    };

    /// <summary>Body of a data request: one feature per station, one array per parameter aligned with the time stamps.</summary>
    public static object Data(IEnumerable<DateTime> times, IEnumerable<StationSeries> features) => new
    {
        timestamps = times.Select(Stamp),
        features = features.Select(feature => new
        {
            properties = new
            {
                station = feature.StationId,
                parameters = feature.Parameters.ToDictionary(pair => pair.Key, pair => new { data = pair.Value }),
            },
        }),
    };

    /// <summary>Time stamp as the data hub writes it, e.g. 2026-11-07T18:20+00:00.</summary>
    private static string Stamp(DateTime time) =>
        time.ToString("yyyy-MM-dd'T'HH:mm'+00:00'", CultureInfo.InvariantCulture);
}
