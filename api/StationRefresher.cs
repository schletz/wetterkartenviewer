using System.Collections.Concurrent;
using Microsoft.Extensions.Logging;

namespace StationProxy;

/// <summary>
/// Keeps <see cref="StationCache"/> filled: new 10 min files on every call, the whole 24 hours
/// of them in a new instance, and older days of a station from its archive when they are asked for.
/// </summary>
public sealed class StationRefresher(HungaroMetClient client, StationCache cache, ILogger<StationRefresher> logger)
{
    /// <summary>Today, the three full days of the station viewer and one more around midnight.</summary>
    public static readonly TimeSpan Retention = TimeSpan.FromDays(5);

    private static readonly TimeSpan SynopFilesCover = TimeSpan.FromHours(24);
    private static readonly TimeSpan Slot = TimeSpan.FromMinutes(10);

    /// <summary>
    /// Least time between two loads of the archive of one station. The archive is written once a day, so a load
    /// that left a gap is repeated this often until the new one is there.
    /// </summary>
    private static readonly TimeSpan ArchiveReloadAfter = TimeSpan.FromMinutes(30);

    private const int ParallelDownloads = 4;

    private readonly SemaphoreSlim _gate = new(1, 1);
    private readonly ConcurrentDictionary<string, ArchiveLoad> _archiveLoads = new();
    private IReadOnlyDictionary<string, string>? _regions;
    private string _lastFile = "";

    /// <summary>Where the 10 min files of the first load begin: the newest slot of the oldest file. The archive has to reach it.</summary>
    private DateTime _synopSince = DateTime.MaxValue;

    /// <summary>One load of a station archive: when it started, and the last slot of the archive once done.</summary>
    private sealed record ArchiveLoad(DateTime Started, Lazy<Task<DateTime>> End);

    /// <summary>Fetches the files that are new since the last call.</summary>
    public Task RefreshAsync() => UpdateAsync(onlyIfEmpty: false);

    /// <summary>Fills an empty cache, so the first request to a new instance has data; otherwise returns at once.</summary>
    public Task EnsureLoadedAsync() => _lastFile.Length > 0 ? Task.CompletedTask : UpdateAsync(onlyIfEmpty: true);

    /// <summary>
    /// Loads the archive of a station if a request reaches further back than the 24 hours of 10 min files.
    /// Once per instance, unless the archive ended before the 10 min files begin: an instance started before the
    /// archive of the day was written loads it again, at most every <see cref="ArchiveReloadAfter"/>, so the gap closes.
    /// A failure only logs (the request answers with what there is) and is tried again by the next one.
    /// </summary>
    public async Task EnsureHistoryAsync(string stationId, DateTime start)
    {
        if (start >= DateTime.UtcNow - SynopFilesCover || !cache.Contains(stationId))
            return;
        // The update factory may run more than once under contention; a Lazy that is not kept never starts.
        var load = _archiveLoads.AddOrUpdate(stationId, NewArchiveLoad, (id, old) => LeftGap(old) ? NewArchiveLoad(id) : old);
        try
        {
            await load.End.Value;
        }
        catch (Exception error) when (error is HttpRequestException or TaskCanceledException or InvalidDataException)
        {
            _archiveLoads.TryRemove(KeyValuePair.Create(stationId, load));
            logger.LogWarning(error, "archive of station {Station} not available", stationId);
        }
    }

    private ArchiveLoad NewArchiveLoad(string stationId) =>
        new(DateTime.UtcNow, new Lazy<Task<DateTime>>(() => LoadArchiveAsync(stationId)));

    /// <summary>True if a finished load ends before the 10 min files begin and is old enough to be repeated.</summary>
    private bool LeftGap(ArchiveLoad load) =>
        load.End.IsValueCreated && load.End.Value.IsCompletedSuccessfully
        && load.End.Value.Result < _synopSince - Slot
        && DateTime.UtcNow - load.Started >= ArchiveReloadAfter;

    /// <summary>Stores the archive of a station and returns its last slot; an empty archive counts as complete.</summary>
    private async Task<DateTime> LoadArchiveAsync(string stationId)
    {
        var measurements = await client.ReadStationArchiveAsync(stationId, DateTime.UtcNow - Retention, CancellationToken.None);
        cache.AddHistory(stationId, measurements);
        // Rows without values count too: the archive ends where its time stamps end, not where the station fell silent.
        var end = measurements.Count > 0 ? measurements[^1].Time : DateTime.MaxValue;
        logger.LogInformation("archive of station {Station} ends {End:u}", stationId, end);
        return end;
    }

    // Not cancelled with a request: the work serves every other request as well.
    private async Task UpdateAsync(bool onlyIfEmpty)
    {
        await _gate.WaitAsync();
        try
        {
            if (onlyIfEmpty && _lastFile.Length > 0)
                return;
            var cancellation = CancellationToken.None;
            _regions ??= await client.ReadRegionsAsync(cancellation);
            var files = await client.ListSynopFilesAsync(cancellation);
            var newFiles = files.Where(name => string.CompareOrdinal(name, _lastFile) > 0).ToList();
            var reports = new IReadOnlyList<StationReport>[newFiles.Count];
            await Parallel.ForEachAsync(
                Enumerable.Range(0, newFiles.Count),
                new ParallelOptions { MaxDegreeOfParallelism = ParallelDownloads, CancellationToken = cancellation },
                async (i, token) => reports[i] = await client.ReadSynopFileAsync(newFiles[i], token));
            foreach (var report in reports.SelectMany(rows => rows))
                cache.Add(report, _regions.GetValueOrDefault(report.Station.Id, ""));
            // The newest slot of the oldest file, which most stations sent. The earliest slot would not do:
            // a station may repeat a slot hours old.
            if (_lastFile.Length == 0 && reports.Length > 0 && reports[0].Count > 0)
                _synopSince = reports[0].Max(report => report.Measurement.Time);
            if (newFiles.Count > 0)
                _lastFile = newFiles[^1];
            cache.Prune(DateTime.UtcNow - Retention);
            logger.LogInformation("{Count} new files, newest {File}", newFiles.Count, _lastFile);
        }
        finally
        {
            _gate.Release();
        }
    }
}
