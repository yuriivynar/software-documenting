
from typing import List, Dict, Any

from src.strategy.output_strategy import OutputStrategy

class OutputContext:

    def __init__(self, strategy: OutputStrategy):
        self._strategy = strategy

    def set_strategy(self, strategy: OutputStrategy) -> None:
        self._strategy = strategy

    def write(self, record: Dict[str, Any]) -> None:
        self._strategy.write(record)

    def write_batch(self, records: List[Dict[str, Any]]) -> None:
        self._strategy.write_batch(records)

    def close(self) -> None:
        self._strategy.close()

    def get_strategy_name(self) -> str:
        return type(self._strategy).__name__
