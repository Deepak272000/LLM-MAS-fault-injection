# -- Build stage ---------------------------------------------------------------
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /app

COPY src/cartservice.csproj ./
RUN dotnet restore

COPY src/ ./
COPY protos/ ../protos/
RUN dotnet publish -c Release -o /out --no-restore

# -- Runtime stage -------------------------------------------------------------
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS runtime
WORKDIR /app

# Non-root user for security
RUN addgroup --system --gid 1001 appgroup && \
    adduser  --system --uid 1001 --ingroup appgroup appuser

COPY --from=build /out ./
RUN chown -R appuser:appgroup /app

USER appuser

ENV ASPNETCORE_ENVIRONMENT=Production
ENV PORT=7070

EXPOSE 7070

ENTRYPOINT ["dotnet", "cartservice.dll"]
