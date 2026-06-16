import json
from pathlib import Path


def load_pipeline_config(config_path: str) -> dict:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Pipeline config not found: {config_path}")
    return json.loads(path.read_text(encoding="utf-8"))
