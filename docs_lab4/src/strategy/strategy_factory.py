import logging
from typing import Dict, Any
 
from src.strategy.output_strategy import OutputStrategy
 
logger = logging.getLogger(__name__)
 
 
class StrategyFactory:

    @staticmethod
    def create(config: Dict[str, Any]) -> OutputStrategy:
        strategy_name = config.get("output", {}).get("strategy", "console").lower()
        logger.info(f"[StrategyFactory] Creating strategy: '{strategy_name}'")
 
        if strategy_name == "console":
            from src.strategy.console_strategy import ConsoleStrategy
            return ConsoleStrategy(pretty=True)
 
        elif strategy_name == "kafka":
            from src.strategy.kafka_strategy import KafkaStrategy
            kafka_cfg = config.get("kafka", {})
            return KafkaStrategy(
                bootstrap_servers=kafka_cfg.get("bootstrap_servers", "localhost:9092"),
                topic=kafka_cfg.get("topic", "air_quality_data"),
                client_id=kafka_cfg.get("client_id", "air_quality_producer"),
                message_format=kafka_cfg.get("message_format", "json"),
            )
 
        elif strategy_name == "redis":
            from src.strategy.redis_strategy import RedisStrategy
            redis_cfg = config.get("redis", {})
            return RedisStrategy(
                host=redis_cfg.get("host", "localhost"),
                port=redis_cfg.get("port", 6379),
                db=redis_cfg.get("db", 0),
                password=redis_cfg.get("password"),
                key_prefix=redis_cfg.get("key_prefix", "air_quality"),
                ttl=redis_cfg.get("ttl"),
                storage_type=redis_cfg.get("storage_type", "hash"),
            )
 
        elif strategy_name == "firebase":
            from src.strategy.firebase_strategy import FirebaseStrategy
            fb_cfg = config.get("firebase", {})
            credentials_path = fb_cfg.get("credentials_path")
            if not credentials_path:
                raise ValueError(
                    "For the 'firebase' strategy, you must provide "
                    "'credentials_path' in config.yaml.\n"
                    "How to get the file: Firebase Console -> Project Settings -> "
                    "Service Accounts -> Generate new private key."
                )
            return FirebaseStrategy(
                database_url=fb_cfg.get("database_url"),
                credentials_path=credentials_path,
                root_node=fb_cfg.get("root_node", "air_quality_data"),
                write_mode=fb_cfg.get("write_mode", "set"),
                batch_size=fb_cfg.get("batch_size", 100),
            )
 
        else:
            raise ValueError(
                f"Unknown strategy: '{strategy_name}'. "
                f"Available options: console, kafka, redis, firebase."
            )
