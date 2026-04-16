from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class IImportService(ABC):
    @abstractmethod
    def import_from_file(self, file_path: str, delimiter: str = "auto") -> Dict[str, int]: ...


class ICategoryService(ABC):
    @abstractmethod
    def get_all(self) -> List: ...

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[object]: ...

    @abstractmethod
    def create(self, name: str, description: str) -> object: ...

    @abstractmethod
    def update(self, id: int, name: str, description: str) -> object: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...


class IProductService(ABC):
    @abstractmethod
    def get_all(self) -> List: ...

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[object]: ...

    @abstractmethod
    def get_by_category(self, category_id: int) -> List: ...

    @abstractmethod
    def search(self, query: str) -> List: ...

    @abstractmethod
    def create(self, name: str, price: float, description: str, category_id: int) -> object: ...

    @abstractmethod
    def update(self, id: int, name: str, price: float, description: str, category_id: int) -> object: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...


class ICustomerService(ABC):
    @abstractmethod
    def get_all(self) -> List: ...

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[object]: ...

    @abstractmethod
    def create(
        self,
        customer_type: str,
        email: str,
        first_name: str = "",
        last_name: str = "",
        company_name: str = "",
        tax_id: str = "",
    ) -> object: ...

    @abstractmethod
    def update(
        self,
        id: int,
        customer_type: str,
        email: str,
        first_name: str = "",
        last_name: str = "",
        company_name: str = "",
        tax_id: str = "",
    ) -> object: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...


class IOrderService(ABC):
    @abstractmethod
    def get_all(self) -> List: ...

    @abstractmethod
    def get_by_customer(self, customer_id: int) -> List: ...

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[object]: ...

    @abstractmethod
    def create(
        self,
        customer_id: int,
        shipping_address: Dict[str, str],
        status: str,
        payment_method: str,
        notes: str,
        items: List[Dict[str, int]],
    ) -> object: ...

    @abstractmethod
    def update(
        self,
        id: int,
        customer_id: int,
        shipping_address: Dict[str, str],
        status: str,
        payment_method: str,
        notes: str,
        items: List[Dict[str, int]],
    ) -> object: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...
