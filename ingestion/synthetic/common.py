from __future__ import annotations

from datetime import datetime, timezone
import random
import uuid

CITIES = ["NYC", "CHICAGO", "DUBAI","ABU DHABI"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rand_city() -> str:
    return random.choice(CITIES)


def rid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"
