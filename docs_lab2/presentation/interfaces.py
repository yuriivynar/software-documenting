from abc import ABC, abstractmethod
from typing import Any, Dict, List


class IImportController(ABC):

    @abstractmethod
    def run_import(self, file_path: str) -> Dict[str, Any]: ...


class IGeneratorController(ABC):

    @abstractmethod
    def generate(self, output_path: str, row_count: int) -> Dict[str, Any]: ...


class ICategoryController(ABC):

    @abstractmethod
    def list_all(self) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def get_one(self, id: int) -> Dict[str, Any]: ...


class IProductController(ABC):

    @abstractmethod
    def list_all(self) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def get_one(self, id: int) -> Dict[str, Any]: ...


class ICustomerController(ABC):

    @abstractmethod
    def list_all(self) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def get_one(self, id: int) -> Dict[str, Any]: ...


class IOrderController(ABC):

    @abstractmethod
    def list_all(self) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def list_by_customer(self, customer_id: int) -> List[Dict[str, Any]]: ...
