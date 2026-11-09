using System.Globalization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Azure.Functions.Worker;

namespace StationProxy;

/// <summary>
/// The endpoints of the GeoSphere Austria data hub the web app uses, for the Hungarian stations.
/// Docs of the original: https://dataset.api.hub.geosphere.at/v1/docs/
/// </summary>
public sealed class StationFunctions(StationCache cache, StationRefresher refresher)
{
    private const string Dataset = "hungaromet-10min";
    private const string HubTimeFormat = "yyyy-MM-dd'T'HH:mm";
    private const string TemperatureParameter = "TL";
    private static readonly TimeSpan Slot = TimeSpan.FromMinutes(10);

    /// <summary>A current value older than this counts as missing: the station has stopped sending.</summary>
    private static readonly TimeSpan MaxCurrentAge = TimeSpan.FromHours(1);

    /// <summary>The value of a measurement per parameter name of the data hub.</summary>
    private static readonly Dictionary<string, Func<Measurement, double?>> ParameterValues = new()
    {
        [TemperatureParameter] = measurement => measurement.Temperature,
        ["TLMIN"] = measurement => measurement.Minimum,
        ["TLMAX"] = measurement => measurement.Maximum,
    };

    /// <summary>The stations with their positions.</summary>
    [Function(nameof(Metadata))]
    public async Task<IActionResult> Metadata(
        [HttpTrigger(AuthorizationLevel.Anonymous, "get", Route = $"v1/station/current/{Dataset}/metadata")] HttpRequest request)
    {
        await refresher.EnsureLoadedAsync();
        return Json(request, DataHubResponses.Metadata(cache.Stations()));
    }

    /// <summary>10 min values of stations between two times; a slot without measurement is null.</summary>
    [Function(nameof(Historical))]
    public async Task<IActionResult> Historical(
        [HttpTrigger(AuthorizationLevel.Anonymous, "get", Route = $"v1/station/historical/{Dataset}")] HttpRequest request)
    {
        if (!TryParseTime(request.Query["start"], out var start) || !TryParseTime(request.Query["end"], out var end))
            return Error(request, "start and end are required, as YYYY-MM-DDTHH:MM in UTC");
        var now = DateTime.UtcNow;
        // The limits keep a request with an absurd span from building millions of time stamps.
        start = Floor(Max(start, now - StationRefresher.Retention));
        end = Floor(end < now ? end : now);
        var parameters = ParameterNames(request);
        var stationIds = StationIds(request);
        await refresher.EnsureLoadedAsync();
        await Task.WhenAll(stationIds.Select(id => refresher.EnsureHistoryAsync(id, start)));

        var times = new List<DateTime>();
        for (var time = start; time <= end; time += Slot)
            times.Add(time);
        var features = stationIds.Select(id =>
        {
            var measurements = cache.Range(id, start, end);
            return new StationSeries(id, parameters.ToDictionary(
                name => name,
                name => times.Select(time => measurements.TryGetValue(time, out var value) ? ParameterValues[name](value) : null).ToArray()));
        }).ToList();
        return Json(request, DataHubResponses.Data(times, features));
    }

    /// <summary>The newest air temperature of several stations, with the time stamp of the newest one among them.</summary>
    [Function(nameof(Current))]
    public async Task<IActionResult> Current(
        [HttpTrigger(AuthorizationLevel.Anonymous, "get", Route = $"v1/station/current/{Dataset}")] HttpRequest request)
    {
        await refresher.EnsureLoadedAsync();
        var oldest = DateTime.UtcNow - MaxCurrentAge;
        var latest = StationIds(request).Select(id => (Id: id, Value: cache.Latest(id))).ToList();
        var fresh = latest.Where(station => station.Value?.Time >= oldest).ToDictionary(station => station.Id, station => station.Value!.Value);
        var features = latest.Select(station => new StationSeries(station.Id, new Dictionary<string, double?[]>
        {
            [TemperatureParameter] = [fresh.TryGetValue(station.Id, out var value) ? value.Temperature : null],
        })).ToList();
        DateTime[] newest = fresh.Count > 0 ? [fresh.Values.Max(value => value.Time)] : [Floor(DateTime.UtcNow)];
        return Json(request, DataHubResponses.Data(newest, features));
    }

    private static string[] StationIds(HttpRequest request) =>
        request.Query["station_ids"].ToString().Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

    private static string[] ParameterNames(HttpRequest request) =>
        [.. request.Query["parameters"].ToString().Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Where(ParameterValues.ContainsKey)];

    private static bool TryParseTime(string? text, out DateTime time) =>
        DateTime.TryParseExact(text, HubTimeFormat, CultureInfo.InvariantCulture,
            DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out time);

    private static DateTime Floor(DateTime time) => new(time.Ticks - time.Ticks % Slot.Ticks, DateTimeKind.Utc);

    private static DateTime Max(DateTime a, DateTime b) => a > b ? a : b;

    private static JsonResult Json(HttpRequest request, object body)
    {
        AllowAnyOrigin(request);
        return new JsonResult(body);
    }

    private static BadRequestObjectResult Error(HttpRequest request, string message)
    {
        AllowAnyOrigin(request);
        return new BadRequestObjectResult(new { message });
    }

    // The read-only data of a public service, requested by a page on another origin (GitHub Pages).
    private static void AllowAnyOrigin(HttpRequest request) =>
        request.HttpContext.Response.Headers.AccessControlAllowOrigin = "*";
}
