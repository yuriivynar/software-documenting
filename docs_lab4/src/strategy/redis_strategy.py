
import json
import logging
from typing import List, Dict, Any, Optional

from src.strategy.output_strategy import OutputStrategy

logger = logging.getLogger(__name__)

class RedisStrategy(OutputStrategy):

    def __init__(self, host: str = "localhost", port: int = 6379,
                 db: int = 0, password: Optional[str] = None,
                 key_prefix: str = "air_quality",
                 ttl: Optional[int] = None,
                 storage_type: str = "hash"):
        self._key_prefix = key_prefix
        self._ttl = ttl
        self._storage_type = storage_type
        self._count = 0
        self._client = None

        try:
            import redis as redis_lib

            self._client = redis_lib.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=5,
            )

            self._client.ping()
            logger.info(
                f"[RedisStrategy] Connected to Redis {host}:{port} db={db}, "
                f"storage_type='{storage_type}'"
            )

        except ImportError:
            logger.error(
                "[RedisStrategy] The 'redis' package is not installed. "
                "Run: pip install redis"
            )
        except Exception as exc:
            logger.warning(
                f"[RedisStrategy] Failed to connect to Redis: {exc}. "
                "Dry-run mode is enabled."
            )

    def _make_key(self, record_id: Any) -> str:
        return f"{self._key_prefix}:{record_id}"

    def _get_record_id(self, record: Dict[str, Any]) -> str:

        for field in ("unique_key", "id", ":id:", "objectid"):
            if field in record:
                return str(record[field])

        return str(self._count)

    def write(self, record: Dict[str, Any]) -> None:
        self._count += 1

        if not self._client:
            return

        try:
            if self._storage_type == "hash":
                self._write_as_hash(record)
            elif self._storage_type == "list":
                self._write_as_list(record)
            elif self._storage_type == "stream":
                self._write_as_stream(record)
            else:
                logger.warning(f"[RedisStrategy] Unknown storage_type: {self._storage_type}")

        except Exception as exc:
            logger.error(f"[RedisStrategy] Failed to write record #{self._count}: {exc}")

    def _write_as_hash(self, record: Dict[str, Any]) -> None:
        record_id = self._get_record_id(record)
        key = self._make_key(record_id)

        hash_data = {k: str(v) for k, v in record.items()}
        self._client.hset(key, mapping=hash_data)
        if self._ttl:
            self._client.expire(key, self._ttl)

    def _write_as_list(self, record: Dict[str, Any]) -> None:
        key = f"{self._key_prefix}:list"
        self._client.rpush(key, json.dumps(record, ensure_ascii=False))
        if self._ttl:
            self._client.expire(key, self._ttl)

    def _write_as_stream(self, record: Dict[str, Any]) -> None:
        key = f"{self._key_prefix}:stream"

        stream_data = {k: str(v) for k, v in record.items()}
        self._client.xadd(key, stream_data, maxlen=10000)

    def write_batch(self, records: List[Dict[str, Any]]) -> None:
        logger.info(
            f"[RedisStrategy] Writing batch of {len(records)} records "
            f"(storage_type='{self._storage_type}')"
        )
        if not self._client:
            for record in records:
                self.write(record)
            return

        pipe = self._client.pipeline(transaction=False)
        for record in records:
            self._count += 1
            try:
                if self._storage_type == "hash":
                    record_id = self._get_record_id(record)
                    key = self._make_key(record_id)
                    pipe.hset(key, mapping={k: str(v) for k, v in record.items()})
                    if self._ttl:
                        pipe.expire(key, self._ttl)
                elif self._storage_type == "list":
                    pipe.rpush(
                        f"{self._key_prefix}:list",
                        json.dumps(record, ensure_ascii=False)
                    )
                elif self._storage_type == "stream":
                    pipe.xadd(
                        f"{self._key_prefix}:stream",
                        {k: str(v) for k, v in record.items()},
                        maxlen=10000
                    )
            except Exception as exc:
                logger.error(f"[RedisStrategy] Failed to prepare record for pipeline: {exc}")

        pipe.execute()
        logger.info(f"[RedisStrategy] Pipeline executed for {len(records)} records.")

    def close(self) -> None:
        if self._client:
            self._client.close()
            logger.info(
                f"[RedisStrategy] Connection closed. Wrote {self._count} records."
            )
