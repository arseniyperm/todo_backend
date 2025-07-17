import logging

from pythonjsonlogger import jsonlogger
import redis
from datetime import datetime, timedelta, timezone
import json
import os
from typing import Dict, Any, Optional
from sqlalchemy.orm.state import InstanceState
from collections import deque
import threading


class RedisCache:
    def __init__(self, host='localhost', port=6379, db=0):
        self._fallback_store = deque(maxlen=1000)
        self._lock = threading.Lock()
        self.redis = None
        try:
            self.redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                socket_connect_timeout=3,
                socket_timeout=5,
                retry_on_timeout=True
            )
            self.redis.ping()
        except Exception as e:
            logging.warning(f"Redis connection failed: {str(e)}. Using fallback storage.")

    def _serialize(self, data: Any) -> Any:
        if isinstance(data, (str, int, float, bool)) or data is None:
            return data
        elif isinstance(data, (datetime, timedelta)):
            return str(data)
        elif isinstance(data, dict):
            return {k: self._serialize(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple, set)):
            return [self._serialize(item) for item in data]
        elif isinstance(data, InstanceState):
            return None
        elif hasattr(data, '__dict__'):
            return self._serialize(data.__dict__)
        return str(data)

    def get(self, key: str) -> Optional[Any]:
        try:
            if self.redis:
                data = self.redis.get(key)
                return json.loads(data) if data else None
        except Exception as e:
            logging.error(f"Redis get error: {str(e)}")
        return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        try:
            serialized = self._serialize(value)
            if self.redis:
                self.redis.setex(key, ttl, json.dumps(serialized))
                return True
            with self._lock:
                self._fallback_store.append((key, serialized))
            return False
        except Exception as e:
            logging.error(f"Cache set error: {str(e)}")
            return False

    def delete(self, *keys) -> None:
        try:
            if self.redis:
                self.redis.delete(*keys)
        except Exception as e:
            logging.error(f"Redis delete error: {str(e)}")

    def flush_fallback(self):
        if not self.redis:
            return

        with self._lock:
            while self._fallback_store:
                key, value = self._fallback_store.popleft()
                try:
                    self.redis.set(key, json.dumps(value))
                except Exception:
                    self._fallback_store.appendleft((key, value))
                    break


class RequestLogger:
    def __init__(self):
        self.cache = RedisCache()
        self._setup_logger()

    def _setup_logger(self):
        self.logger = logging.getLogger('todo_service')
        self.logger.setLevel(logging.INFO)

        os.makedirs('logs', exist_ok=True)

        file_handler = logging.FileHandler('logs/todo_service.log')
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(levelname)s %(name)s %(message)s'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def log(self, action: str, **data):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            **{k: self.cache._serialize(v) for k, v in data.items()}
        }

        # Логирование в файл
        self.logger.info(log_entry)

        # Логирование в Redis
        try:
            if self.cache.redis:
                self.cache.redis.lpush('todo_logs', json.dumps(log_entry))
                self.cache.redis.ltrim('todo_logs', 0, 999)
            else:
                with self.cache._lock:
                    self.cache._fallback_store.append(('todo_logs', log_entry))
        except Exception as e:
            self.logger.error(f"Log storage failed: {str(e)}")


logger = RequestLogger()
cache = RedisCache()
