import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from sqlalchemy.orm import Session

from bll.interfaces import (
    ICategoryService,
    ICustomerService,
    IImportService,
    IOrderService,
    IProductService,
)
from dal.db_models import (
    Bucket,
    Category,
    CorporateCustomer,
    CustomerType,
    LineItem,
    Order,
    OrderStatus,
    PaymentMethod,
    PersonalCustomer,
    Product,
    ShippingAddress,
)
from dal.interfaces import (
    IBucketRepository,
    ICategoryRepository,
    ICustomerRepository,
    IDataFileReader,
    ILineItemRepository,
    IOrderRepository,
    IProductRepository,
    IShippingAddressRepository,
)

logger = logging.getLogger(__name__)


class ImportService(IImportService):
    def __init__(
        self,
        reader: IDataFileReader,
        cat_repo: ICategoryRepository,
        prod_repo: IProductRepository,
        cust_repo: ICustomerRepository,
        addr_repo: IShippingAddressRepository,
        order_repo: IOrderRepository,
        li_repo: ILineItemRepository,
        bucket_repo: IBucketRepository,
        session: Session,
    ):
        self._reader = reader
        self._cats = cat_repo
        self._prods = prod_repo
        self._custs = cust_repo
        self._addrs = addr_repo
        self._orders = order_repo
        self._lis = li_repo
        self._buckets = bucket_repo
        self._session = session

    def import_from_file(self, file_path: str, delimiter: str = "auto") -> Dict[str, int]:
        logger.info("Import started: %s [delimiter=%s]", file_path, delimiter)
        all_rows = self._reader.read(file_path, delimiter=delimiter)

        groups: Dict[str, List[dict]] = {}
        for row in all_rows:
            record_type = row["record_type"].strip().lower()
            groups.setdefault(record_type, []).append(row)

        stats: Dict[str, int] = {}
        try:
            stats["categories"] = self._save_categories(groups.get("category", []))
            stats["products"] = self._save_products(groups.get("product", []))
            stats["customers"] = self._save_customers(
                groups.get("personal_customer", []),
                groups.get("corporate_customer", []),
            )
            stats["addresses"] = self._save_addresses(groups.get("shipping_address", []))
            stats["buckets"] = self._save_buckets(groups.get("bucket", []))
            stats["orders"] = self._save_orders(groups.get("order", []))
            stats["line_items"] = self._save_line_items(groups.get("line_item", []))
            self._sync_postgres_sequences()
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return stats

    def _sync_postgres_sequences(self) -> None:

        bind = self._session.get_bind()
        if bind is None or bind.dialect.name != "postgresql":
            return

        sequence_targets = (
            ("categories", "id"),
            ("products", "id"),
            ("customers", "id"),
            ("shipping_addresses", "id"),
            ("buckets", "id"),
            ("orders", "id"),
            ("line_items", "id"),
        )

        for table_name, column_name in sequence_targets:
            _sync_postgres_table_sequence(self._session, table_name, column_name)

    def _save_categories(self, rows: List[dict]) -> int:
        objects = [
            Category(id=int(r["id"]), name=r["name"].strip(), description=r.get("description", ""))
            for r in rows
        ]
        self._cats.save_all(objects)
        return len(objects)

    def _save_products(self, rows: List[dict]) -> int:
        objects = [
            Product(
                id=int(r["id"]),
                name=r["name"].strip(),
                price=float(r["price"]),
                description=r.get("description", ""),
                category_id=int(r["category_id"]),
            )
            for r in rows
        ]
        self._prods.save_all(objects)
        return len(objects)

    def _save_customers(self, personal_rows: List[dict], corporate_rows: List[dict]) -> int:
        objects = []
        for row in personal_rows:
            objects.append(
                PersonalCustomer(
                    id=int(row["id"]),
                    email=row["email"].strip(),
                    first_name=row["first_name"].strip(),
                    last_name=row["last_name"].strip(),
                    customer_type=CustomerType.PERSONAL,
                )
            )
        for row in corporate_rows:
            objects.append(
                CorporateCustomer(
                    id=int(row["id"]),
                    email=row["email"].strip(),
                    company_name=row["company_name"].strip(),
                    tax_id=row["tax_id"].strip(),
                    customer_type=CustomerType.CORPORATE,
                )
            )
        self._custs.save_all(objects)
        return len(objects)

    def _save_addresses(self, rows: List[dict]) -> int:
        objects = [
            ShippingAddress(
                id=int(r["id"]),
                customer_id=int(r["customer_id"]),
                street=r["street"].strip(),
                city=r["city"].strip(),
                country=r["country"].strip(),
                postal_code=r["postal_code"].strip(),
            )
            for r in rows
        ]
        self._addrs.save_all(objects)
        return len(objects)

    def _save_buckets(self, rows: List[dict]) -> int:
        seen_customer_ids = set()
        objects = []
        for row in rows:
            customer_id = int(row["customer_id"])
            if customer_id in seen_customer_ids:
                continue
            seen_customer_ids.add(customer_id)
            raw_created_at = row.get("created_at", "")
            created_at = datetime.fromisoformat(raw_created_at) if raw_created_at else datetime.utcnow()
            objects.append(Bucket(id=int(row["id"]), customer_id=customer_id, created_at=created_at))
        self._buckets.save_all(objects)
        return len(objects)

    def _save_orders(self, rows: List[dict]) -> int:
        objects = []
        for row in rows:
            status = _parse_order_status(row.get("status", "pending"))
            payment_method = _parse_payment_method(row.get("payment_method", ""))
            raw_bucket_id = row.get("bucket_id", "").strip()
            raw_total_amount = row.get("total_amount", "").strip()
            raw_updated_at = row.get("updated_at", "").strip()
            objects.append(
                Order(
                    id=int(row["id"]),
                    customer_id=int(row["customer_id"]),
                    shipping_address_id=int(row["shipping_address_id"]),
                    bucket_id=int(raw_bucket_id) if raw_bucket_id else None,
                    status=status,
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(raw_updated_at) if raw_updated_at else None,
                    total_amount=float(raw_total_amount) if raw_total_amount else None,
                    notes=row.get("notes", "").strip() or None,
                    payment_method=payment_method,
                )
            )
        self._orders.save_all(objects)
        return len(objects)

    def _save_line_items(self, rows: List[dict]) -> int:
        objects = []
        for row in rows:
            raw_order_id = row.get("order_id", "").strip()
            raw_bucket_id = row.get("bucket_id", "").strip()
            objects.append(
                LineItem(
                    id=int(row["id"]),
                    order_id=int(raw_order_id) if raw_order_id else None,
                    bucket_id=int(raw_bucket_id) if raw_bucket_id else None,
                    product_id=int(row["product_id"]),
                    quantity=int(row["quantity"]),
                    unit_price=float(row["unit_price"]),
                )
            )
        self._lis.save_all(objects)
        return len(objects)


class CategoryService(ICategoryService):
    def __init__(self, repo: ICategoryRepository, session: Session):
        self._repo = repo
        self._session = session

    def get_all(self) -> list:
        return self._repo.find_all()

    def get_by_id(self, id: int) -> Optional[object]:
        return self._repo.find_by_id(id)

    def create(self, name: str, description: str) -> object:
        normalized_name = _require_non_empty(name, "Category name")
        self._ensure_unique_category_name(normalized_name)
        category = Category(name=normalized_name, description=(description or "").strip())
        return self._commit_return(lambda: self._repo.save(category))

    def update(self, id: int, name: str, description: str) -> object:
        existing = self._repo.find_by_id(id)
        if existing is None:
            raise ValueError(f"Category with id={id} not found.")
        normalized_name = _require_non_empty(name, "Category name")
        self._ensure_unique_category_name(normalized_name, exclude_id=id)
        existing.name = normalized_name
        existing.description = (description or "").strip()
        return self._commit_return(lambda: self._repo.save(existing))

    def delete(self, id: int) -> bool:
        existing = self._repo.find_by_id(id)
        if existing is None:
            return False
        if existing.products:
            raise ValueError(
                f"Cannot delete category '{existing.name}' because it still contains products."
            )
        return self._commit_return(lambda: self._repo.delete(id))

    def _ensure_unique_category_name(self, name: str, exclude_id: Optional[int] = None) -> None:
        for category in self._repo.find_all():
            if category.name.lower() == name.lower() and category.id != exclude_id:
                raise ValueError(f"Category name '{name}' already exists.")

    def _commit_return(self, operation):
        try:
            result = operation()
            self._session.commit()
            return result
        except IntegrityError as exc:
            self._session.rollback()
            if _is_primary_key_sequence_error(exc):
                _sync_postgres_table_sequence(self._session, "categories", "id")
                result = operation()
                self._session.commit()
                return result
            raise ValueError(_format_integrity_error(exc, "category")) from exc
        except Exception:
            self._session.rollback()
            raise


class ProductService(IProductService):
    def __init__(self, repo: IProductRepository, cat_repo: ICategoryRepository, session: Session):
        self._repo = repo
        self._cats = cat_repo
        self._session = session

    def get_all(self) -> list:
        return self._repo.find_all()

    def get_by_id(self, id: int) -> Optional[object]:
        return self._repo.find_by_id(id)

    def get_by_category(self, category_id: int) -> list:
        return self._repo.find_by_category(category_id)

    def search(self, query: str) -> list:
        if not query or not query.strip():
            return self._repo.find_all()
        return self._repo.search(query.strip())

    def create(self, name: str, price: float, description: str, category_id: int) -> object:
        normalized_name = _require_non_empty(name, "Product name")
        normalized_price = _require_positive_number(price, "Price")
        self._ensure_category_exists(category_id)
        product = Product(
            name=normalized_name,
            price=normalized_price,
            description=(description or "").strip(),
            category_id=category_id,
        )
        return self._commit_return(lambda: self._repo.save(product))

    def update(self, id: int, name: str, price: float, description: str, category_id: int) -> object:
        existing = self._repo.find_by_id(id)
        if existing is None:
            raise ValueError(f"Product with id={id} not found.")
        existing.name = _require_non_empty(name, "Product name")
        existing.price = _require_positive_number(price, "Price")
        existing.description = (description or "").strip()
        existing.category_id = category_id
        self._ensure_category_exists(category_id)
        return self._commit_return(lambda: self._repo.save(existing))

    def delete(self, id: int) -> bool:
        existing = self._repo.find_by_id(id)
        if existing is None:
            return False
        if existing.line_items:
            raise ValueError(
                f"Cannot delete product '{existing.name}' because it is referenced by orders or carts."
            )
        return self._commit_return(lambda: self._repo.delete(id))

    def _ensure_category_exists(self, category_id: int) -> None:
        if self._cats.find_by_id(category_id) is None:
            raise ValueError(f"Category with id={category_id} does not exist.")

    def _commit_return(self, operation):
        try:
            result = operation()
            self._session.commit()
            return result
        except IntegrityError as exc:
            self._session.rollback()
            if _is_primary_key_sequence_error(exc):
                _sync_postgres_table_sequence(self._session, "products", "id")
                result = operation()
                self._session.commit()
                return result
            raise ValueError(_format_integrity_error(exc, "product")) from exc
        except Exception:
            self._session.rollback()
            raise


class CustomerService(ICustomerService):
    def __init__(self, repo: ICustomerRepository, session: Session):
        self._repo = repo
        self._session = session

    def get_all(self) -> list:
        return self._repo.find_all()

    def get_by_id(self, id: int) -> Optional[object]:
        return self._repo.find_by_id(id)

    def create(
        self,
        customer_type: str,
        email: str,
        first_name: str = "",
        last_name: str = "",
        company_name: str = "",
        tax_id: str = "",
    ) -> object:
        normalized_type = _parse_customer_type(customer_type)
        normalized_email = _require_non_empty(email, "Email").lower()
        self._ensure_unique_email(normalized_email)
        customer = _build_customer_entity(
            normalized_type,
            email=normalized_email,
            first_name=first_name,
            last_name=last_name,
            company_name=company_name,
            tax_id=tax_id,
        )
        return self._commit_return(lambda: self._repo.save(customer))

    def update(
        self,
        id: int,
        customer_type: str,
        email: str,
        first_name: str = "",
        last_name: str = "",
        company_name: str = "",
        tax_id: str = "",
    ) -> object:
        existing = self._repo.find_by_id(id)
        if existing is None:
            raise ValueError(f"Customer with id={id} not found.")
        normalized_type = _parse_customer_type(customer_type)
        normalized_email = _require_non_empty(email, "Email").lower()
        self._ensure_unique_email(normalized_email, exclude_id=id)
        customer = _build_customer_entity(
            normalized_type,
            id=id,
            email=normalized_email,
            first_name=first_name,
            last_name=last_name,
            company_name=company_name,
            tax_id=tax_id,
        )
        return self._commit_return(lambda: self._repo.save(customer))

    def delete(self, id: int) -> bool:
        existing = self._repo.find_by_id(id)
        if existing is None:
            return False
        if existing.orders or existing.addresses or existing.bucket:
            raise ValueError(
                f"Cannot delete customer '{existing.email}' because related orders, addresses, or cart data exist."
            )
        return self._commit_return(lambda: self._repo.delete(id))

    def _ensure_unique_email(self, email: str, exclude_id: Optional[int] = None) -> None:
        for customer in self._repo.find_all():
            if customer.email.lower() == email.lower() and customer.id != exclude_id:
                raise ValueError(f"Email '{email}' is already used by another customer.")

    def _commit_return(self, operation):
        try:
            result = operation()
            self._session.commit()
            return result
        except IntegrityError as exc:
            self._session.rollback()
            if _is_primary_key_sequence_error(exc):
                _sync_postgres_table_sequence(self._session, "customers", "id")
                result = operation()
                self._session.commit()
                return result
            raise ValueError(_format_integrity_error(exc, "customer")) from exc
        except Exception:
            self._session.rollback()
            raise


class OrderService(IOrderService):
    def __init__(
        self,
        repo: IOrderRepository,
        customer_repo: ICustomerRepository,
        product_repo: IProductRepository,
        address_repo: IShippingAddressRepository,
        line_item_repo: ILineItemRepository,
        session: Session,
    ):
        self._repo = repo
        self._customers = customer_repo
        self._products = product_repo
        self._addresses = address_repo
        self._line_items = line_item_repo
        self._session = session

    def get_all(self) -> list:
        return self._repo.find_all()

    def get_by_customer(self, customer_id: int) -> list:
        return self._repo.find_by_customer_id(customer_id)

    def get_by_id(self, id: int) -> Optional[object]:
        return self._repo.find_by_id(id)

    def create(
        self,
        customer_id: int,
        shipping_address: Dict[str, str],
        status: str,
        payment_method: str,
        notes: str,
        items: List[Dict[str, int]],
    ) -> object:
        validated_items, total_amount = self._validate_order_payload(customer_id, shipping_address, items)
        address = self._build_shipping_address(customer_id, shipping_address)
        order = Order(
            customer_id=customer_id,
            shipping_address_id=None,
            bucket_id=None,
            status=_parse_order_status(status),
            payment_method=_parse_payment_method(payment_method),
            notes=(notes or "").strip() or None,
            total_amount=total_amount,
        )
        return self._save_order_graph(order, address, validated_items)

    def update(
        self,
        id: int,
        customer_id: int,
        shipping_address: Dict[str, str],
        status: str,
        payment_method: str,
        notes: str,
        items: List[Dict[str, int]],
    ) -> object:
        existing = self._repo.find_by_id(id)
        if existing is None:
            raise ValueError(f"Order with id={id} not found.")
        validated_items, total_amount = self._validate_order_payload(customer_id, shipping_address, items)
        address = self._build_shipping_address(customer_id, shipping_address)
        existing.customer_id = customer_id
        existing.bucket_id = None
        existing.status = _parse_order_status(status)
        existing.payment_method = _parse_payment_method(payment_method)
        existing.notes = (notes or "").strip() or None
        existing.total_amount = total_amount
        return self._save_order_graph(existing, address, validated_items, replace_existing_items=True)

    def delete(self, id: int) -> bool:
        existing = self._repo.find_by_id(id)
        if existing is None:
            return False
        try:
            self._line_items.delete_by_order_id(id)
            deleted = self._repo.delete(id)
            self._session.commit()
            return deleted
        except Exception:
            self._session.rollback()
            raise

    def _validate_order_payload(
        self,
        customer_id: int,
        shipping_address: Dict[str, str],
        items: List[Dict[str, int]],
    ) -> tuple[list[LineItem], float]:
        if self._customers.find_by_id(customer_id) is None:
            raise ValueError(f"Customer with id={customer_id} does not exist.")
        for field_name in ("street", "city", "country", "postal_code"):
            if not (shipping_address.get(field_name) or "").strip():
                raise ValueError(f"Shipping address field '{field_name}' is required.")
        if not items:
            raise ValueError("Order must contain at least one line item.")

        validated_items: list[LineItem] = []
        total_amount = 0.0
        for item in items:
            product_id = int(item["product_id"])
            quantity = int(item["quantity"])
            if quantity <= 0:
                raise ValueError("Each line item quantity must be greater than zero.")
            product = self._products.find_by_id(product_id)
            if product is None:
                raise ValueError(f"Product with id={product_id} does not exist.")
            unit_price = round(float(product.price), 2)
            validated_items.append(
                LineItem(product_id=product_id, quantity=quantity, unit_price=unit_price)
            )
            total_amount += unit_price * quantity
        return validated_items, round(total_amount, 2)

    def _build_shipping_address(self, customer_id: int, shipping_address: Dict[str, str]) -> ShippingAddress:
        return ShippingAddress(
            customer_id=customer_id,
            street=shipping_address["street"].strip(),
            city=shipping_address["city"].strip(),
            country=shipping_address["country"].strip(),
            postal_code=shipping_address["postal_code"].strip(),
        )

    def _save_order_graph(
        self,
        order: Order,
        address: ShippingAddress,
        items: List[LineItem],
        replace_existing_items: bool = False,
    ) -> Order:
        try:
            return self._save_order_graph_once(order, address, items, replace_existing_items)
        except IntegrityError as exc:
            self._session.rollback()
            if _is_primary_key_sequence_error(exc):
                self._sync_order_graph_sequences()
                try:
                    return self._save_order_graph_once(order, address, items, replace_existing_items)
                except IntegrityError as retry_exc:
                    self._session.rollback()
                    raise ValueError(_format_integrity_error(retry_exc, "order")) from retry_exc
            raise ValueError(_format_integrity_error(exc, "order")) from exc
        except Exception:
            self._session.rollback()
            raise

    def _save_order_graph_once(
        self,
        order: Order,
        address: ShippingAddress,
        items: List[LineItem],
        replace_existing_items: bool = False,
    ) -> Order:
        saved_address = self._addresses.save(address)
        order.shipping_address_id = saved_address.id
        saved_order = self._repo.save(order)
        if replace_existing_items:
            self._line_items.delete_by_order_id(saved_order.id)
        for item in items:
            item.order_id = saved_order.id
        self._line_items.save_all(items)
        self._session.commit()
        refreshed = self._repo.find_by_id(saved_order.id)
        return refreshed if refreshed is not None else saved_order

    def _sync_order_graph_sequences(self) -> None:
        for table_name in ("shipping_addresses", "orders", "line_items"):
            _sync_postgres_table_sequence(self._session, table_name, "id")


def _require_non_empty(value: str, label: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ValueError(f"{label} cannot be empty.")
    return normalized


def _require_positive_number(value: float, label: str) -> float:
    if float(value) <= 0:
        raise ValueError(f"{label} must be a positive number.")
    return round(float(value), 2)


def _parse_customer_type(raw_value: str) -> CustomerType:
    value = (raw_value or "").strip().lower()
    if value == CustomerType.PERSONAL.value:
        return CustomerType.PERSONAL
    if value == CustomerType.CORPORATE.value:
        return CustomerType.CORPORATE
    raise ValueError("Customer type must be either 'personal' or 'corporate'.")


def _build_customer_entity(
    customer_type: CustomerType,
    email: str,
    first_name: str = "",
    last_name: str = "",
    company_name: str = "",
    tax_id: str = "",
    id: Optional[int] = None,
):
    payload = {"id": id, "email": email, "customer_type": customer_type}
    if customer_type == CustomerType.PERSONAL:
        payload["first_name"] = _require_non_empty(first_name, "First name")
        payload["last_name"] = _require_non_empty(last_name, "Last name")
        payload["company_name"] = None
        payload["tax_id"] = None
        return PersonalCustomer(**payload)

    payload["company_name"] = _require_non_empty(company_name, "Company name")
    payload["tax_id"] = _require_non_empty(tax_id, "Tax ID")
    payload["first_name"] = None
    payload["last_name"] = None
    return CorporateCustomer(**payload)


def _parse_order_status(raw_value: str) -> OrderStatus:
    value = (raw_value or "").strip().lower() or OrderStatus.PENDING.value
    for status in OrderStatus:
        if status.value == value:
            return status
    raise ValueError("Invalid order status.")


def _parse_payment_method(raw_value: str) -> Optional[PaymentMethod]:
    value = (raw_value or "").strip().lower()
    if not value:
        return None
    for method in PaymentMethod:
        if method.value == value:
            return method
    raise ValueError("Invalid payment method.")


def _format_integrity_error(exc: IntegrityError, entity_name: str) -> str:
    message = str(exc.orig).lower()
    if "duplicate key value violates unique constraint" in message and "_pkey" in message:
        return (
            f"Cannot create or update {entity_name}: database primary-key sequence is out of sync. "
            "This usually happens after importing rows with explicit ids. Re-run CSV import with the "
            "new sequence sync code or reset the PostgreSQL sequence."
        )
    if "duplicate key value violates unique constraint" in message:
        return f"Cannot create or update {entity_name}: a unique value already exists."
    if "foreign key" in message:
        return f"Cannot save {entity_name}: referenced related data does not exist."
    return str(exc.orig)


def _is_primary_key_sequence_error(exc: IntegrityError) -> bool:
    message = str(exc.orig).lower()
    return "duplicate key value violates unique constraint" in message and "_pkey" in message


def _sync_postgres_table_sequence(session: Session, table_name: str, column_name: str) -> None:
    bind = session.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return

    session.execute(
        text(
            """
            SELECT setval(
                pg_get_serial_sequence(:table_name, :column_name),
                COALESCE((SELECT MAX(id) FROM {table_name}), 1),
                COALESCE((SELECT MAX(id) FROM {table_name}), 0) > 0
            )
            """.format(table_name=table_name)
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    session.flush()
