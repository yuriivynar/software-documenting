
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.config_loader import load_config
from src.strategy.strategy_factory import StrategyFactory
from src.context.output_context import OutputContext
from src.reader.dataset_reader import DatasetReader

def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)


    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config.yaml")
    config = load_config(config_path)
    strategy_name = config.get("output", {}).get("strategy", "console")
    logger.info(f"Active output strategy: '{strategy_name.upper()}'")

    dataset_cfg = config.get("dataset", {})
    reader = DatasetReader(
        local_path=dataset_cfg.get("local_path", "data/air_quality.csv"),
        api_url=dataset_cfg.get("url"),
        limit=dataset_cfg.get("limit", 500),
    )

    try:
        records = reader.read()
    except ConnectionError as exc:
        logger.error(f"Connection error: {exc}")
        records = reader.read() if os.path.exists(
            dataset_cfg.get("local_path", "data/air_quality.csv")
        ) else []

    if not records:
        logger.error("Data is missing. Terminating execution.")
        return

    summary = reader.get_summary(records)
    print(f"Records loaded: {summary['total_records']}")
    print(f"Number of fields:     {summary['total_fields']}")
    print(f"Fields: {', '.join(summary['fields'])}\n")

    strategy = StrategyFactory.create(config)
    context = OutputContext(strategy)

    print(f"Active strategy: {context.get_strategy_name()}")
    print("-" * 65)

    try:

        context.write_batch(records)

    except KeyboardInterrupt:
        logger.warning("Execution interrupted by user (Ctrl+C).")
    except Exception as exc:
        logger.error(f"Output error: {exc}", exc_info=True)
    finally:

        context.close()

    print("\n" + "=" * 65)
    print("  Execution completed successfully.")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    main()
