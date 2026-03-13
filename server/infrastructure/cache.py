import json
from pathlib import Path

CACHE_FLUSH_BATCH = 100

# cache 目录保持不变：沿用原 backend/cache
CACHE_DIR = Path(__file__).resolve().parents[2] / "backend" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class PersistentCache:
    def __init__(self, name):
        self.path = CACHE_DIR / f"{name}.json"
        self.store = self._load()
        self.pending = 0

    def _load(self):
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value
        self.pending += 1
        if self.pending >= CACHE_FLUSH_BATCH:
            self.flush()

    def flush(self):
        if self.pending <= 0:
            return
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self.store, f, ensure_ascii=False)
        self.pending = 0
