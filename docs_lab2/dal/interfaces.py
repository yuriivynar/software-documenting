from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class IDataFileReader(ABC):
    @abstractmethod
    def read(self, file_path: str, delimiter: str = "auto") -> List[Dict[str, str]]: ...


class ICategoryRepository(ABC):
    @abstractmethod
    def save_all(self, categories: list) -> None: ...

    @abstractmethod
    def save(self, category: object) -> object: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def find_all(self) -> list: ...

    @abstractmethod
    def find_by_id(self, id: int) -> Optional[object]: ...

    @abstractmethod
    def find_by_name(self, name: str) -> Optional[object]: ...


class IProductRepository(ABC):
    @abstractmethod
    def save_all(self, products: list) -> None: ...

    @abstractmethod
    def save(self, product: object) -> object: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def find_all(self) -> list: ...

    @abstractmethod
    def find_by_id(self, id: int) -> Optional[object]: ...

    @abstractmethod
    def find_by_category(self, category_id: int) -> list: ...

    @abstractmethod
    def search(self, query: str) -> list: ...


class ICustomerRepository(ABC):
    @abstractmethod
    def save_all(self, customers: list) -> None: ...

    @abstractmethod
    def save(self, customer: object) -> object: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def find_all(self) -> list: ...

    @abstractmethod
    def find_by_id(self, id: int) -> Optional[object]: ...

    @abstractmethod
    def find_by_email(self, email: str) -> Optional[object]: ...


class IShippingAddressRepository(ABC):
    @abstractmethod
    def save_all(self, addresses: list) -> None: ...

    @abstractmethod
    def save(self, address: object) -> object: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def find_by_id(self, id: int) -> Optional[object]: ...

    @abstractmethod
    def find_by_customer_id(self, customer_id: int) -> list: ...


class IOrderRepository(ABC):
    @abstractmethod
    def save_all(self, orders: list) -> None: ...

    @abstractmethod
    def save(self, order: object) -> object: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def find_all(self) -> list: ...

    @abstractmethod
    def find_by_id(self, id: int) -> Optional[object]: ...

    @abstractmethod
    def find_by_customer_id(self, customer_id: int) -> list: ...


class ILineItemRepository(ABC):
    @abstractmethod
    def save_all(self, line_items: list) -> None: ...

    @abstractmethod
    def delete_by_order_id(self, order_id: int) -> None: ...

    @abstractmethod
    def find_by_order_id(self, order_id: int) -> list: ...


class IBucketRepository(ABC):
    @abstractmethod
    def save_all(self, buckets: list) -> None: ...

    @abstractmethod
    def find_by_customer_id(self, customer_id: int) -> Optional[object]: ...
