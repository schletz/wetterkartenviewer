namespace StationProxy;

/// <summary>
/// The measurements of the last days, held in memory only. A new instance of the function starts empty;
/// <see cref="StationRefresher"/> fills it again. Shared by concurrent requests, hence the lock.
/// </summary>
public sealed class StationCache
{
    private readonly Lock _lock = new();
    private readonly Dictionary<string, CachedStation> _stations = [];

    /// <summary>A station with its county and its measurements in order of time.</summary>
    private sealed record CachedStation(StationInfo Info, string Region, SortedList<DateTime, Measurement> Series);

    /// <summary>Takes one row of a 10 min file. Stations without a temperature sensor (rain gauges) stay out.</summary>
    public void Add(StationReport report, string region)
    {
        lock (_lock)
        {
            if (!_stations.TryGetValue(report.Station.Id, out var station))
            {
                if (report.Measurement.Temperature is null)
                    return;
                station = new CachedStation(report.Station, region, []);
                _stations[report.Station.Id] = station;
            }
            Store(station, report.Measurement);
        }
    }

    /// <summary>Takes older measurements of a station that is already known; slots held already stay as they are.</summary>
    public void AddHistory(string stationId, IEnumerable<Measurement> measurements)
    {
        lock (_lock)
        {
            if (!_stations.TryGetValue(stationId, out var station))
                return;
            foreach (var measurement in measurements.Where(measurement => !station.Series.ContainsKey(measurement.Time)))
                Store(station, measurement);
        }
    }

    /// <summary>True for a station of the list; other ids have nothing to look up.</summary>
    public bool Contains(string stationId)
    {
        lock (_lock)
            return _stations.ContainsKey(stationId);
    }

    /// <summary>All stations with their counties.</summary>
    public IReadOnlyList<(StationInfo Info, string Region)> Stations()
    {
        lock (_lock)
            return [.. _stations.Values.Select(station => (station.Info, station.Region))];
    }

    /// <summary>The measurements of a station between two times, both included, by time.</summary>
    public IReadOnlyDictionary<DateTime, Measurement> Range(string stationId, DateTime start, DateTime end)
    {
        lock (_lock)
        {
            return _stations.TryGetValue(stationId, out var station)
                ? station.Series.Values.Where(value => value.Time >= start && value.Time <= end).ToDictionary(value => value.Time)
                : new Dictionary<DateTime, Measurement>();
        }
    }

    /// <summary>The newest measurement of a station that holds a temperature; null if there is none.</summary>
    public Measurement? Latest(string stationId)
    {
        lock (_lock)
        {
            if (!_stations.TryGetValue(stationId, out var station))
                return null;
            for (var i = station.Series.Count - 1; i >= 0; i--)
            {
                if (station.Series.Values[i].Temperature.HasValue)
                    return station.Series.Values[i];
            }
            return null;
        }
    }

    /// <summary>Forgets the measurements before a time, and the stations left without any.</summary>
    public void Prune(DateTime before)
    {
        lock (_lock)
        {
            foreach (var (id, station) in _stations.ToList())
            {
                while (station.Series.Count > 0 && station.Series.Keys[0] < before)
                    station.Series.RemoveAt(0);
                if (station.Series.Count == 0)
                    _stations.Remove(id);
            }
        }
    }

    private static void Store(CachedStation station, Measurement measurement)
    {
        // An empty row must not wipe out the same slot sent before with values.
        if (measurement.HasValues)
            station.Series[measurement.Time] = measurement;
    }
}
