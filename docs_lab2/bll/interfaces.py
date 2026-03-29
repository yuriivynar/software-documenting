from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class IImportService(ABC):


    @abstractmethod
    def import_from_file(self, file_path: str) -> Dict[str, int]: ...



class ICategoryService(ABC):

    @abstractmethod
    def get_all(self) -> List: ...

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[object]: ...


class IProductService(ABC):

    @abstractmethod
    def get_all(self) -> List: ...

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[object]: ...


class ICustomerService(ABC):

    @abstractmethod
    def get_all(self) -> List: ...

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[object]: ...


class IOrderService(ABC):

    @abstractmethod
    def get_all(self) -> List: ...

    @abstractmethod
    def get_by_customer(self, customer_id: int) -> List: ...
