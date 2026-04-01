using System.Net;                            // Fixes 'IPAddress'
using Microsoft.AspNetCore.Server.Kestrel.Core; // Fixes 'HttpProtocols'
using Grpc.Health.V1;                        // Fixes 'HealthCheckResponse'
using Microsoft.Extensions.Diagnostics.HealthChecks; // Best practice for Health Service
using cartservice;

var builder = WebApplication.CreateBuilder(args);

// gRPC
builder.Services.AddGrpc(opts =>
{
    opts.EnableDetailedErrors = true;
});

// Health checks (used by k8s liveness/readiness probes)
builder.Services.AddGrpcHealthChecks().AddCheck("self", () => HealthCheckResult.Healthy());

// HttpClient for Ollama with resilient timeout
builder.Services.AddHttpClient<OllamaCartAgent>(client =>
{
    client.Timeout = TimeSpan.FromSeconds(30);
});

// Register agent and gRPC service
builder.Services.AddSingleton<OllamaCartAgent>();
builder.Services.AddSingleton<CartServiceImpl>();

// Bind on all interfaces, port from env (default 7070 to match original service)
var port = Environment.GetEnvironmentVariable("PORT") ?? "7070";
//builder.WebHost.UseUrls($"http://0.0.0.0:{port}");

builder.WebHost.ConfigureKestrel(options =>
{   int portInt = int.Parse(Environment.GetEnvironmentVariable("PORT") ?? "7070");
    options.Listen(IPAddress.Any, 7070, listenOptions =>
    {
        listenOptions.Protocols = HttpProtocols.Http2;
    });
});





var app = builder.Build();

app.MapGrpcService<CartServiceImpl>();
app.MapGrpcHealthChecksService();

// Mark service as SERVING
var lifetime = app.Services.GetRequiredService<IHostApplicationLifetime>();


app.MapGet("/", () => "Cart Agent Service (Ollama-backed). Use a gRPC client.");

app.Logger.LogInformation("Cart Agent Service starting on port {Port}", port);
app.Logger.LogInformation("Ollama URL: {Url}", builder.Configuration["OLLAMA_URL"] ?? "http://ollama:11434");
app.Logger.LogInformation("Model: {Model}", builder.Configuration["OLLAMA_MODEL"] ?? "llama3.2:1b");

app.Run();
