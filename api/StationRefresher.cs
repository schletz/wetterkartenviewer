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
    private const int ParallelDownloads = 4;

    private readonly SemaphoreSlim _gate = new(1, 1);
    private readonly ConcurrentDictionary<string, Lazy<Task>> _archiveLoads = new();
    private IReadOnlyDictionary<string, string>? _regions;
    private string _lastFile = "";

    /// <summary>Fetches the files that are new since the last call.</summary>
    public Task RefreshAsync() => UpdateAsync(onlyIfEmpty: false);

    /// <summary>Fills an empty cache, so the first request to a new instance has data; otherwise returns at once.</summary>
    public Task EnsureLoadedAsync() => _lastFile.Length > 0 ? Task.CompletedTask : UpdateAsync(onlyIfEmpty: true);

    /// <summary>
    /// Loads the archive of a station once per instance if a request reaches further back than the 24 hours of
    /// 10 min files. A failure only logs (the request answers with what there is) and is tried again by the next one.
    /// </summary>
    public async Task EnsureHistoryAsync(string stationId, DateTime start)
    {
        if (start >= DateTime.UtcNow - SynopFilesCover || !cache.Contains(stationId))
            return;
        var load = _archiveLoads.GetOrAdd(stationId, id => new Lazy<Task>(() => LoadArchiveAsync(id)));
        try
        {
            await load.Value;
        }
        catch (Exception error) when (error is HttpRequestException or TaskCanceledException or InvalidDataException)
        {
            _archiveLoads.TryRemove(stationId, out _);
            logger.LogWarning(error, "archive of station {Station} not available", stationId);
        }
    }

    private async Task LoadArchiveAsync(string stationId)
    {
        var measurements = await client.ReadStationArchiveAsync(stationId, DateTime.UtcNow - Retention, CancellationToken.None);
        cache.AddHistory(stationId, measurements);
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
