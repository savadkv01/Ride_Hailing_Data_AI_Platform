param(
    [string]$PostgresContainer = 'rh-postgres',
    [string]$PostgresUser = 'ride_admin',
    [string]$PostgresDatabase = 'ride_warehouse'
)

$scriptPathInContainer = '/tmp/cleanup_legacy_warehouse_schemas.sql'

$localScript = Join-Path $PSScriptRoot 'cleanup_legacy_warehouse_schemas.sql'
if (-not (Test-Path $localScript)) {
    throw "Cleanup SQL not found: $localScript"
}

docker cp $localScript "${PostgresContainer}:${scriptPathInContainer}"
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to copy cleanup SQL into Postgres container.'
}

docker exec -i $PostgresContainer psql -U $PostgresUser -d $PostgresDatabase -f $scriptPathInContainer
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to execute cleanup SQL.'
}

docker exec -i $PostgresContainer psql -U $PostgresUser -d $PostgresDatabase -c "select schema_name from information_schema.schemata where schema_name in ('staging','gold','analytics','analytics_staging','analytics_analytics') order by schema_name;"
