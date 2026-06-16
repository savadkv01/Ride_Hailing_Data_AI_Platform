import os
from pathlib import Path


_ENV_LOADED = False


def _candidate_env_paths(project_root: Path):
    return [
        project_root / ".env",
        project_root / ".env.local",
        project_root / "docker/compose/.env.local",
        project_root / "docker/compose/.env.enterprise-sim",
    ]


def resolve_env_file(project_root: Path | None = None):
    explicit = os.getenv("ENV_FILE")
    if explicit:
        explicit_path = Path(explicit)
        if not explicit_path.is_absolute() and project_root is not None:
            explicit_path = project_root / explicit_path
        return explicit_path

    if project_root is None:
        project_root = Path(__file__).resolve().parents[1]

    for candidate in _candidate_env_paths(project_root):
        if candidate.exists():
            return candidate
    return None


def load_env_file(env_file: Path, override: bool = False):
    if not env_file.exists():
        return 0

    loaded = 0
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if not key:
            continue
        if key in os.environ and not override:
            continue
        os.environ[key] = value
        loaded += 1

    return loaded


def auto_load_env(project_root: Path | None = None, override: bool = False):
    global _ENV_LOADED
    if _ENV_LOADED:
        return None

    env_file = resolve_env_file(project_root=project_root)
    if env_file is not None:
        load_env_file(env_file, override=override)
    _ENV_LOADED = True
    return env_file


def postgres_connection_kwargs():
    return {
        "host": os.getenv("PGHOST", os.getenv("POSTGRES_HOST", "localhost")),
        "port": int(os.getenv("PGPORT", os.getenv("POSTGRES_PORT", "5432"))),
        "dbname": os.getenv("PGDATABASE", os.getenv("POSTGRES_DB", "ride_warehouse")),
        "user": os.getenv("PGUSER", os.getenv("POSTGRES_USER", "ride_admin")),
        "password": os.getenv("PGPASSWORD", os.getenv("POSTGRES_PASSWORD", "ride_password")),
    }