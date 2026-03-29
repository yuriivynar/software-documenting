import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, DateTime,
    ForeignKey, Enum as SAEnum,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()



class CustomerType(enum.Enum):
    PERSONAL  = "personal"
    CORPORATE = "corporate"


class OrderStatus(enum.Enum):
    PENDING   = "pending"
    CONFIRMED = "confirmed"
    SHIPPED   = "shipped"
    DELIVERED = "delivered"


class PaymentMethod(enum.Enum):
    CREDIT_CARD   = "credit_card"
    PAYPAL        = "paypal"
    BANK_TRANSFER = "bank_transfer"
    APPLE_PAY     = "apple_pay"
    GOOGLE_PAY    = "google_pay"



class Category(Base):
    __tablename__ = "categories"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(100), unique=True, nullable=False)
    description = Column(String(500))

    products = relationship("Product", back_populates="category")



class Product(Base):
    __tablename__ = "products"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(200), nullable=False)
    price       = Column(Float,       nullable=False)
    description = Column(String(500))
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    category   = relationship("Category", back_populates="products")
    line_items = relationship("LineItem",  back_populates="product")



class Customer(Base):
    __tablename__ = "customers"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    customer_type = Column(SAEnum(CustomerType), nullable=False)
    email         = Column(String(255), unique=True, nullable=False)

    first_name   = Column(String(100))
    last_name    = Column(String(100))
    company_name = Column(String(200)) 
    tax_id       = Column(String(50))  

    addresses = relationship("ShippingAddress", back_populates="customer")
    orders    = relationship("Order",           back_populates="customer")
    bucket    = relationship("Bucket",          back_populates="customer",
                             uselist=False)

    __mapper_args__ = {"polymorphic_on": customer_type}


class PersonalCustomer(Customer):
    __mapper_args__ = {"polymorphic_identity": CustomerType.PERSONAL}


class CorporateCustomer(Customer):
    __mapper_args__ = {"polymorphic_identity": CustomerType.CORPORATE}



class ShippingAddress(Base):
    __tablename__ = "shipping_addresses"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    street      = Column(String(300), nullable=False)
    city        = Column(String(100), nullable=False)
    country     = Column(String(100), nullable=False)
    postal_code = Column(String(20),  nullable=False)

    customer = relationship("Customer",  back_populates="addresses")
    orders   = relationship("Order",     back_populates="shipping_address")



class Bucket(Base):
    __tablename__ = "buckets"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"),
                         unique=True, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)

    customer   = relationship("Customer", back_populates="bucket")
    line_items = relationship(
        "LineItem", back_populates="bucket",
        foreign_keys="LineItem.bucket_id",
        cascade="all, delete-orphan",
    )
    orders = relationship("Order", back_populates="bucket")



class Order(Base):
    __tablename__ = "orders"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    customer_id         = Column(Integer, ForeignKey("customers.id"),          nullable=False)
    shipping_address_id = Column(Integer, ForeignKey("shipping_addresses.id"), nullable=False)
    bucket_id           = Column(Integer, ForeignKey("buckets.id"),            nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow,            nullable=False)
    updated_at          = Column(DateTime, default=datetime.utcnow,
                                 onupdate=datetime.utcnow,                     nullable=True)
    status              = Column(SAEnum(OrderStatus), default=OrderStatus.PENDING)
    total_amount   = Column(Float,        nullable=True)
    notes          = Column(String(1000), nullable=True)
    payment_method = Column(SAEnum(PaymentMethod), nullable=True)

    customer         = relationship("Customer",        back_populates="orders")
    shipping_address = relationship("ShippingAddress", back_populates="orders")
    bucket           = relationship("Bucket",          back_populates="orders")
    line_items       = relationship(
        "LineItem", back_populates="order",
        foreign_keys="LineItem.order_id",
        cascade="all, delete-orphan",
    )


class LineItem(Base):

    __tablename__ = "line_items"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    order_id   = Column(Integer, ForeignKey("orders.id"),   nullable=True)
    bucket_id  = Column(Integer, ForeignKey("buckets.id"),  nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity   = Column(Integer, nullable=False)
    unit_price = Column(Float,   nullable=False)

    order   = relationship("Order",   back_populates="line_items",
                           foreign_keys=[order_id])
    bucket  = relationship("Bucket",  back_populates="line_items",
                           foreign_keys=[bucket_id])
    product = relationship("Product", back_populates="line_items")
