namespace StationProxy;

/// <summary>One row of a 10 min file: a station and what it measured in one slot.</summary>
public sealed record StationReport(StationInfo Station, Measurement Measurement);
