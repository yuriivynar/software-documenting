from abc import ABC, abstractmethod
from typing import List, Optional, Dict


class IDataFileReader(ABC):

    @abstractmethod
    def read(self, file_path: str) -> List[Dict[str, str]]: ...


class ICategoryRepository(ABC):

    @abstractmethod
    def save_all(self, categories: list) -> None: ...

    @abstractmethod
    def find_all(self) -> list: ...

    @abstractmethod
    def find_by_id(self, id: int) -> Optional[object]: ...


class IProductRepository(ABC):

    @abstractmethod
    def save_all(self, products: list) -> None: ...

    @abstractmethod
    def find_all(self) -> list: ...

    @abstractmethod
    def find_by_id(self, id: int) -> Optional[object]: ...


class ICustomerRepository(ABC):

    @abstractmethod
    def save_all(self, customers: list) -> None: ...

    @abstractmethod
    def find_all(self) -> list: ...

    @abstractmethod
    def find_by_id(self, id: int) -> Optional[object]: ...


class IShippingAddressRepository(ABC):

    @abstractmethod
    def save_all(self, addresses: list) -> None: ...

    @abstractmethod
    def find_by_customer_id(self, customer_id: int) -> list: ...


class IOrderRepository(ABC):

    @abstractmethod
    def save_all(self, orders: list) -> None: ...

    @abstractmethod
    def find_all(self) -> list: ...

    @abstractmethod
    def find_by_customer_id(self, customer_id: int) -> list: ...


class ILineItemRepository(ABC):

    @abstractmethod
    def save_all(self, line_items: list) -> None: ...

    @abstractmethod
    def find_by_order_id(self, order_id: int) -> list: ...


class IBucketRepository(ABC):

    @abstractmethod
    def save_all(self, buckets: list) -> None: ...

    @abstractmethod
    def find_by_customer_id(self, customer_id: int) -> Optional[object]: ...
