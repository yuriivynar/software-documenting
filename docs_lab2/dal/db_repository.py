from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from dal.db_models import Bucket, Category, Customer, LineItem, Order, Product, ShippingAddress
from dal.interfaces import (
    IBucketRepository,
    ICategoryRepository,
    ICustomerRepository,
    ILineItemRepository,
    IOrderRepository,
    IProductRepository,
    IShippingAddressRepository,
)


class _BaseRepo:
    def __init__(self, session: Session):
        self._db = session

    def _save_all(self, objects: list) -> None:
        for obj in objects:
            self._db.merge(obj)
        self._db.flush()

    def _save_one(self, obj):
        managed = self._db.merge(obj)
        self._db.flush()
        self._db.refresh(managed)
        return managed


class CategoryRepository(_BaseRepo, ICategoryRepository):
    def save_all(self, categories: List[Category]) -> None:
        self._save_all(categories)

    def save(self, category: Category) -> Category:
        return self._save_one(category)

    def delete(self, id: int) -> bool:
        category = self._db.get(Category, id)
        if category is None:
            return False
        self._db.delete(category)
        self._db.flush()
        return True

    def find_all(self) -> List[Category]:
        return self._db.query(Category).order_by(Category.name).all()

    def find_by_id(self, id: int) -> Optional[Category]:
        return self._db.get(Category, id)

    def find_by_name(self, name: str) -> Optional[Category]:
        return self._db.query(Category).filter(Category.name == name).first()


class ProductRepository(_BaseRepo, IProductRepository):
    def save_all(self, products: List[Product]) -> None:
        self._save_all(products)

    def save(self, product: Product) -> Product:
        return self._save_one(product)

    def delete(self, id: int) -> bool:
        product = self._db.get(Product, id)
        if product is None:
            return False
        self._db.delete(product)
        self._db.flush()
        return True

    def find_all(self) -> List[Product]:
        return self._db.query(Product).join(Category).order_by(Product.name).all()

    def find_by_id(self, id: int) -> Optional[Product]:
        return self._db.get(Product, id)

    def find_by_category(self, category_id: int) -> List[Product]:
        return self._db.query(Product).filter(Product.category_id == category_id).order_by(Product.name).all()

    def search(self, query: str) -> List[Product]:
        pattern = f"%{query}%"
        return (
            self._db.query(Product)
            .filter(or_(Product.name.ilike(pattern), Product.description.ilike(pattern)))
            .order_by(Product.name)
            .all()
        )


class CustomerRepository(_BaseRepo, ICustomerRepository):
    def save_all(self, customers: List[Customer]) -> None:
        self._save_all(customers)

    def save(self, customer: Customer) -> Customer:
        return self._save_one(customer)

    def delete(self, id: int) -> bool:
        customer = self._db.get(Customer, id)
        if customer is None:
            return False
        self._db.delete(customer)
        self._db.flush()
        return True

    def find_all(self) -> List[Customer]:
        return self._db.query(Customer).order_by(Customer.id).all()

    def find_by_id(self, id: int) -> Optional[Customer]:
        return self._db.get(Customer, id)

    def find_by_email(self, email: str) -> Optional[Customer]:
        return self._db.query(Customer).filter(Customer.email == email).first()


class ShippingAddressRepository(_BaseRepo, IShippingAddressRepository):
    def save_all(self, addresses: List[ShippingAddress]) -> None:
        self._save_all(addresses)

    def save(self, address: ShippingAddress) -> ShippingAddress:
        return self._save_one(address)

    def delete(self, id: int) -> bool:
        address = self._db.get(ShippingAddress, id)
        if address is None:
            return False
        self._db.delete(address)
        self._db.flush()
        return True

    def find_by_id(self, id: int) -> Optional[ShippingAddress]:
        return self._db.get(ShippingAddress, id)

    def find_by_customer_id(self, customer_id: int) -> List[ShippingAddress]:
        return self._db.query(ShippingAddress).filter_by(customer_id=customer_id).order_by(ShippingAddress.id.desc()).all()


class OrderRepository(_BaseRepo, IOrderRepository):
    def save_all(self, orders: List[Order]) -> None:
        self._save_all(orders)

    def save(self, order: Order) -> Order:
        return self._save_one(order)

    def delete(self, id: int) -> bool:
        order = self._db.get(Order, id)
        if order is None:
            return False
        self._db.delete(order)
        self._db.flush()
        return True

    def find_all(self) -> List[Order]:
        return self._db.query(Order).order_by(Order.created_at.desc(), Order.id.desc()).all()

    def find_by_id(self, id: int) -> Optional[Order]:
        return self._db.get(Order, id)

    def find_by_customer_id(self, customer_id: int) -> List[Order]:
        return (
            self._db.query(Order)
            .filter_by(customer_id=customer_id)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .all()
        )


class LineItemRepository(_BaseRepo, ILineItemRepository):
    def save_all(self, line_items: List[LineItem]) -> None:
        self._save_all(line_items)

    def delete_by_order_id(self, order_id: int) -> None:
        self._db.query(LineItem).filter(LineItem.order_id == order_id).delete(synchronize_session=False)
        self._db.flush()

    def find_by_order_id(self, order_id: int) -> List[LineItem]:
        return self._db.query(LineItem).filter_by(order_id=order_id).all()


class BucketRepository(_BaseRepo, IBucketRepository):
    def save_all(self, buckets: List[Bucket]) -> None:
        self._save_all(buckets)

    def find_by_customer_id(self, customer_id: int) -> Optional[Bucket]:
        return self._db.query(Bucket).filter_by(customer_id=customer_id).first()
