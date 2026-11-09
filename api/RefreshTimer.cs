using Microsoft.Azure.Functions.Worker;

namespace StationProxy;

/// <summary>
/// Fetches new measurements every 5 minutes, also while nobody asks, so the list stays complete.
/// HungaroMet writes its files just after every full 10 minutes, hence one minute past.
/// </summary>
public sealed class RefreshTimer(StationRefresher refresher)
{
    /// <summary>Timer entry point.</summary>
    [Function(nameof(RefreshTimer))]
    public Task Run([TimerTrigger("0 1/5 * * * *")] TimerInfo timer) => refresher.RefreshAsync();
}
