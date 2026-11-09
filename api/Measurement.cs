namespace StationProxy;

/// <summary>Air temperatures of one station in one 10 min slot, in °C; null where the station sent none.</summary>
/// <param name="Time">Slot in UTC.</param>
/// <param name="Temperature">Air temperature at the end of the slot.</param>
/// <param name="Minimum">Lowest temperature within the slot.</param>
/// <param name="Maximum">Highest temperature within the slot.</param>
public readonly record struct Measurement(DateTime Time, double? Temperature, double? Minimum, double? Maximum)
{
    /// <summary>True if the slot holds at least one value.</summary>
    public bool HasValues => Temperature.HasValue || Minimum.HasValue || Maximum.HasValue;
}
