namespace StationProxy;

/// <summary>Description of a station as the file of a transmission gives it.</summary>
/// <param name="Id">Station number, e.g. "44527".</param>
/// <param name="Name">Name as HungaroMet spells it.</param>
/// <param name="Latitude">Degrees north.</param>
/// <param name="Longitude">Degrees east.</param>
/// <param name="Altitude">Height in m above sea level.</param>
public sealed record StationInfo(string Id, string Name, double Latitude, double Longitude, double Altitude);
