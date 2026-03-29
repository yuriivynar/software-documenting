from typing import List, Optional
from sqlalchemy.orm import Session

from dal.interfaces import (
    ICategoryRepository, IProductRepository, ICustomerRepository,
    IShippingAddressRepository, IOrderRepository,
    ILineItemRepository, IBucketRepository,
)
from dal.db_models import (
    Category, Product, Customer,
    ShippingAddress, Order, LineItem, Bucket,
)


class _BaseRepo:

    def __init__(self, session: Session):
        self._db = session

    def _save_all(self, objects: list) -> None:
        for obj in objects:
            self._db.merge(obj)
        self._db.flush()


class CategoryRepository(_BaseRepo, ICategoryRepository):

    def save_all(self, categories: List[Category]) -> None:
        self._save_all(categories)

    def find_all(self) -> List[Category]:
        return self._db.query(Category).all()

    def find_by_id(self, id: int) -> Optional[Category]:
        return self._db.get(Category, id)


class ProductRepository(_BaseRepo, IProductRepository):

    def save_all(self, products: List[Product]) -> None:
        self._save_all(products)

    def find_all(self) -> List[Product]:
        return self._db.query(Product).all()

    def find_by_id(self, id: int) -> Optional[Product]:
        return self._db.get(Product, id)


class CustomerRepository(_BaseRepo, ICustomerRepository):

    def save_all(self, customers: List[Customer]) -> None:
        self._save_all(customers)

    def find_all(self) -> List[Customer]:
        return self._db.query(Customer).all()

    def find_by_id(self, id: int) -> Optional[Customer]:
        return self._db.get(Customer, id)


class ShippingAddressRepository(_BaseRepo, IShippingAddressRepository):

    def save_all(self, addresses: List[ShippingAddress]) -> None:
        self._save_all(addresses)

    def find_by_customer_id(self, customer_id: int) -> List[ShippingAddress]:
        return (self._db.query(ShippingAddress)
                .filter_by(customer_id=customer_id).all())


class OrderRepository(_BaseRepo, IOrderRepository):

    def save_all(self, orders: List[Order]) -> None:
        self._save_all(orders)

    def find_all(self) -> List[Order]:
        return self._db.query(Order).all()

    def find_by_customer_id(self, customer_id: int) -> List[Order]:
        return (self._db.query(Order)
                .filter_by(customer_id=customer_id).all())


class LineItemRepository(_BaseRepo, ILineItemRepository):

    def save_all(self, line_items: List[LineItem]) -> None:
        self._save_all(line_items)

    def find_by_order_id(self, order_id: int) -> List[LineItem]:
        return (self._db.query(LineItem)
                .filter_by(order_id=order_id).all())

    def find_by_bucket_id(self, bucket_id: int) -> List[LineItem]:
        return (self._db.query(LineItem)
                .filter_by(bucket_id=bucket_id).all())


class BucketRepository(_BaseRepo, IBucketRepository):

    def save_all(self, buckets: List[Bucket]) -> None:
        self._save_all(buckets)

    def find_by_customer_id(self, customer_id: int) -> Optional[Bucket]:
        return (self._db.query(Bucket)
                .filter_by(customer_id=customer_id).first())

    def find_by_id(self, id: int) -> Optional[Bucket]:
        return self._db.get(Bucket, id)
