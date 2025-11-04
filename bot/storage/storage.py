from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SEEN_PATH = os.path.join(DATA_DIR, "seen.json")


@dataclass
class SeenStorage:
    path: str = SEEN_PATH
    _data: Dict[str, List[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}
        else:
            self._data = {}

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get_seen(self, cinema_key: str) -> List[str]:
        return list(self._data.get(cinema_key, []))

    def add_and_get_new(self, cinema_key: str, titles: List[str]) -> List[str]:
        seen = set(self._data.get(cinema_key, []))
        new_items = [t for t in titles if t not in seen]
        if new_items:
            updated = list(seen.union(new_items))
            self._data[cinema_key] = updated
            self.save()
        return new_items
