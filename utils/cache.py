# -*- coding: utf-8 -*-
# @Time : 2025/2/18 下午12:08
# @Author : renjiajia
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class CacheManager:
    def __init__(self, ttl: int = 30):
        self.cache_file = Path("data/cache.db")
        self.ttl = ttl
        self._ensure_cache_file()

    def _ensure_cache_file(self):
        if not self.cache_file.exists():
            self.cache_file.parent.mkdir(exist_ok=True)
            with open(self.cache_file, "wb") as f:
                pickle.dump({}, f)

    def get(self, key: str) -> Any:
        """获取缓存项"""
        with open(self.cache_file, "rb") as f:
            cache = pickle.load(f)

        entry = cache.get(key)
        if entry and datetime.now() < entry["expiry"]:
            return entry["value"]
        return None

    def set(self, key: str, value: Any) -> None:
        """设置缓存项"""
        with open(self.cache_file, "rb") as f:
            cache = pickle.load(f)

        cache[key] = {
            "value": value,
            "expiry": datetime.now() + timedelta(days=self.ttl)
        }

        with open(self.cache_file, "wb") as f:
            pickle.dump(cache, f)

    def delete(self, key: str) -> None:
        """删除缓存项"""
        with open(self.cache_file, "rb") as f:
            cache = pickle.load(f)

        if key in cache:
            del cache[key]

        with open(self.cache_file, "wb") as f:
            pickle.dump(cache, f)

    def exists(self, key: str) -> bool:
        """检查缓存项是否存在"""
        with open(self.cache_file, "rb") as f:
            cache = pickle.load(f)

        entry = cache.get(key)
        if entry and datetime.now() < entry["expiry"]:
            return True
        return False

# 测试
if __name__ == "__main__":
    cache = CacheManager()
    cache.set("user", "renjiajia")
    print(cache.get("user"))
    cache.delete("user")
    print(cache.get("user"))  # None



