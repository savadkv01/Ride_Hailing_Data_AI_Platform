param(
    [string]$EnvFile = 'docker/compose/.env.local'
)

docker compose --env-file $EnvFile -f docker/compose/docker-compose.base.yml -f docker/compose/docker-compose.spark.yml -f docker/compose/docker-compose.monitoring.yml -f docker/compose/docker-compose.airflow.yml down
