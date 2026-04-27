
import json
from typing import List, Dict, Any

from src.strategy.output_strategy import OutputStrategy

class ConsoleStrategy(OutputStrategy):

    def __init__(self, pretty: bool = True, separator: str = "-" * 60):
        self._pretty = pretty
        self._separator = separator
        self._count = 0

    def write(self, record: Dict[str, Any]) -> None:
        self._count += 1
        indent = 2 if self._pretty else None
        print(f"[#{self._count}] {json.dumps(record, ensure_ascii=False, indent=indent)}")
        if self._pretty:
            print(self._separator)

    def write_batch(self, records: List[Dict[str, Any]]) -> None:
        print(f"\n{'='*60}")
        print(f"  Batch output: {len(records)} records  [strategy: CONSOLE]")
        print(f"{'='*60}\n")
        for record in records:
            self.write(record)

    def close(self) -> None:
        print(f"\n[ConsoleStrategy] Done. Printed {self._count} records.")
