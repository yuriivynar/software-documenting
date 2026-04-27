
import json
import logging
from typing import List, Dict, Any

from src.strategy.output_strategy import OutputStrategy

logger = logging.getLogger(__name__)

class KafkaStrategy(OutputStrategy):

    def __init__(self, bootstrap_servers: str, topic: str,
                 client_id: str = "air_quality_producer",
                 message_format: str = "json"):
        self._topic = topic
        self._message_format = message_format
        self._count = 0
        self._producer = None

        try:

            from kafka import KafkaProducer

            self._producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                client_id=client_id,

                value_serializer=lambda v: json.dumps(
                    v, ensure_ascii=False
                ).encode("utf-8"),

                retries=3,

                acks="all",
            )
            logger.info(
                f"[KafkaStrategy] Producer connected to {bootstrap_servers}, "
                f"topic='{topic}'"
            )

        except ImportError:
            logger.error(
                "[KafkaStrategy] The 'kafka-python' package is not installed. "
                "Run: pip install kafka-python"
            )
        except Exception as exc:
            logger.warning(
                f"[KafkaStrategy] Failed to connect to Kafka: {exc}. "
                "Dry-run mode is enabled."
            )

    def _serialize(self, record: Dict[str, Any]) -> str:
        if self._message_format == "csv":
            return ",".join(str(v) for v in record.values())
        return json.dumps(record, ensure_ascii=False)

    def write(self, record: Dict[str, Any]) -> None:
        self._count += 1
        if self._producer:
            future = self._producer.send(self._topic, value=record)
            try:
                future.get(timeout=10)
            except Exception as exc:
                logger.error(f"[KafkaStrategy] Failed to send record #{self._count}: {exc}")
        else:
            return

    def write_batch(self, records: List[Dict[str, Any]]) -> None:
        logger.info(
            f"[KafkaStrategy] Sending batch of {len(records)} records "
            f"to topic='{self._topic}'"
        )
        for record in records:
            self.write(record)

        if self._producer:
            self._producer.flush()

    def close(self) -> None:
        if self._producer:
            self._producer.flush()
            self._producer.close()
            logger.info(
                f"[KafkaStrategy] Connection closed. Sent {self._count} records."
            )
