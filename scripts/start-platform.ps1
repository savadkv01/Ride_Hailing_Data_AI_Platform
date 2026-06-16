param(
    [ValidateSet('core', 'spark', 'monitoring', 'full')]
    [string]$Profile = 'monitoring',
    [string]$EnvFile = 'docker/compose/.env.local'
)

$base = @(
    '--env-file', $EnvFile,
    '-f', 'docker/compose/docker-compose.base.yml'
)

if ($Profile -eq 'core') {
    docker compose @base up -d
    exit $LASTEXITCODE
}

if ($Profile -eq 'spark') {
    docker compose @base -f docker/compose/docker-compose.spark.yml up -d
    exit $LASTEXITCODE
}

if ($Profile -eq 'monitoring') {
    docker compose @base -f docker/compose/docker-compose.spark.yml -f docker/compose/docker-compose.monitoring.yml up -d
    exit $LASTEXITCODE
}

if ($Profile -eq 'full') {
    docker compose @base -f docker/compose/docker-compose.spark.yml -f docker/compose/docker-compose.monitoring.yml -f docker/compose/docker-compose.airflow.yml up -d
    exit $LASTEXITCODE
}
