using Microsoft.Azure.Functions.Worker.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using StationProxy;

var builder = FunctionsApplication.CreateBuilder(args);
builder.ConfigureFunctionsWebApplication();
builder.Services.AddHttpClient(HungaroMetClient.HttpClientName, client =>
{
    client.BaseAddress = HungaroMetClient.BaseAddress;
    client.Timeout = TimeSpan.FromSeconds(60);
    client.DefaultRequestHeaders.UserAgent.ParseAdd("wetterkartenviewer");
});
builder.Services.AddSingleton<HungaroMetClient>();
builder.Services.AddSingleton<StationCache>();
builder.Services.AddSingleton<StationRefresher>();
builder.Build().Run();
