
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class OutputStrategy(ABC):

    @abstractmethod
    def write(self, record: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def write_batch(self, records: List[Dict[str, Any]]) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass
