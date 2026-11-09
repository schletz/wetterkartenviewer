namespace StationProxy;

/// <summary>The values of one station, per parameter name in the order of the time stamps of the response.</summary>
public sealed record StationSeries(string StationId, IReadOnlyDictionary<string, double?[]> Parameters);
