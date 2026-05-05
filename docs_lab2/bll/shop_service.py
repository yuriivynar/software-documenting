import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from dal.interfaces import (
    IDataFileReader, ICategoryRepository, IProductRepository,
    ICustomerRepository, IShippingAddressRepository, IOrderRepository,
    ILineItemRepository, IBucketRepository,
)
from bll.interfaces import (
    IImportService, ICategoryService, IProductService,
    ICustomerService, IOrderService,
)
from dal.db_models import (
    Category, Product, PersonalCustomer, CorporateCustomer,
    ShippingAddress, Order, LineItem, Bucket,
    CustomerType, OrderStatus, PaymentMethod,
)

logger = logging.getLogger(__name__)


class ImportService(IImportService):

    def __init__(
        self,
        reader:       IDataFileReader,
        cat_repo:     ICategoryRepository,
        prod_repo:    IProductRepository,
        cust_repo:    ICustomerRepository,
        addr_repo:    IShippingAddressRepository,
        order_repo:   IOrderRepository,
        li_repo:      ILineItemRepository,
        bucket_repo:  IBucketRepository,
        session:      Session,
    ):
        self._reader     = reader
        self._cats       = cat_repo
        self._prods      = prod_repo
        self._custs      = cust_repo
        self._addrs      = addr_repo
        self._orders     = order_repo
        self._lis        = li_repo
        self._buckets    = bucket_repo
        self._session    = session

    def import_from_file(self, file_path: str) -> Dict[str, int]:
        logger.info("Starting import from: %s", file_path)

        all_rows = self._reader.read(file_path)
        logger.info("Rows read: %d", len(all_rows))

        groups: Dict[str, List[dict]] = {}
        for row in all_rows:
            rt = row["record_type"].strip().lower()
            groups.setdefault(rt, []).append(row)

        stats: Dict[str, int] = {}

        try:
            stats["categories"] = self._save_categories(groups.get("category", []))
            stats["products"]   = self._save_products(groups.get("product", []))
            stats["customers"]  = self._save_customers(
                groups.get("personal_customer", []),
                groups.get("corporate_customer", []),
            )
            stats["addresses"]  = self._save_addresses(groups.get("shipping_address", []))
            stats["buckets"]    = self._save_buckets(groups.get("bucket", []))
            stats["orders"]     = self._save_orders(groups.get("order", []))
            stats["line_items"] = self._save_line_items(groups.get("line_item", []))

            self._session.commit()
            logger.info("Import completed successfully: %s", stats)

        except Exception as exc:
            self._session.rollback()
            logger.error("Import failed, transaction rolled back: %s", exc)
            raise

        return stats


    def _save_categories(self, rows: List[dict]) -> int:
        objects = [
            Category(
                id          = int(row["id"]),
                name        = row["name"].strip(),
                description = row.get("description", ""),
            )
            for row in rows
        ]
        self._cats.save_all(objects)
        return len(objects)

    def _save_products(self, rows: List[dict]) -> int:
        objects = [
            Product(
                id          = int(row["id"]),
                name        = row["name"].strip(),
                price       = float(row["price"]),
                description = row.get("description", ""),
                category_id = int(row["category_id"]),
            )
            for row in rows
        ]
        self._prods.save_all(objects)
        return len(objects)

    def _save_customers(
        self, personal_rows: List[dict], corporate_rows: List[dict]
    ) -> int:
        objects = []
        for row in personal_rows:
            objects.append(PersonalCustomer(
                id            = int(row["id"]),
                email         = row["email"].strip(),
                first_name    = row["first_name"].strip(),
                last_name     = row["last_name"].strip(),
                customer_type = CustomerType.PERSONAL,
            ))
        for row in corporate_rows:
            objects.append(CorporateCustomer(
                id            = int(row["id"]),
                email         = row["email"].strip(),
                company_name  = row["company_name"].strip(),
                tax_id        = row["tax_id"].strip(),
                customer_type = CustomerType.CORPORATE,
            ))
        self._custs.save_all(objects)
        return len(objects)

    def _save_addresses(self, rows: List[dict]) -> int:
        objects = [
            ShippingAddress(
                id          = int(row["id"]),
                customer_id = int(row["customer_id"]),
                street      = row["street"].strip(),
                city        = row["city"].strip(),
                country     = row["country"].strip(),
                postal_code = row["postal_code"].strip(),
            )
            for row in rows
        ]
        self._addrs.save_all(objects)
        return len(objects)

    def _save_buckets(self, rows: List[dict]) -> int:
        seen = set()
        objects = []
        for row in rows:
            cid = int(row["customer_id"])
            if cid in seen:
                continue
            seen.add(cid)
            raw_date = row.get("created_at", "")
            created  = datetime.fromisoformat(raw_date) if raw_date else datetime.utcnow()
            objects.append(Bucket(
                id          = int(row["id"]),
                customer_id = cid,
                created_at  = created,
            ))
        self._buckets.save_all(objects)
        return len(objects)

    def _save_orders(self, rows: List[dict]) -> int:
        objects = []
        for row in rows:
            try:
                status = OrderStatus[row["status"].strip().upper()]
            except KeyError:
                status = OrderStatus.PENDING

            pm_raw = row.get("payment_method", "").strip().upper()
            try:
                payment = PaymentMethod[pm_raw] if pm_raw else None
            except KeyError:
                payment = None

            raw_bid = row.get("bucket_id", "").strip()
            bucket_id = int(raw_bid) if raw_bid else None

            raw_total = row.get("total_amount", "").strip()
            total_amount = float(raw_total) if raw_total else None

            raw_updated = row.get("updated_at", "").strip()
            updated_at = datetime.fromisoformat(raw_updated) if raw_updated else None

            objects.append(Order(
                id                  = int(row["id"]),
                customer_id         = int(row["customer_id"]),
                shipping_address_id = int(row["shipping_address_id"]),
                bucket_id           = bucket_id,
                status              = status,
                created_at          = datetime.fromisoformat(row["created_at"]),
                updated_at          = updated_at,
                total_amount        = total_amount,
                notes               = row.get("notes", "").strip() or None,
                payment_method      = payment,
            ))
        self._orders.save_all(objects)
        return len(objects)

    def _save_line_items(self, rows: List[dict]) -> int:
        objects = []
        for row in rows:
            raw_oid = row.get("order_id", "").strip()
            raw_bid = row.get("bucket_id", "").strip()
            objects.append(LineItem(
                id         = int(row["id"]),
                order_id   = int(raw_oid) if raw_oid else None,
                bucket_id  = int(raw_bid) if raw_bid else None,
                product_id = int(row["product_id"]),
                quantity   = int(row["quantity"]),
                unit_price = float(row["unit_price"]),
            ))
        self._lis.save_all(objects)
        return len(objects)


class CategoryService(ICategoryService):
    def __init__(self, repo: ICategoryRepository):
        self._repo = repo

    def get_all(self) -> list:
        return self._repo.find_all()

    def get_by_id(self, id: int) -> Optional[object]:
        return self._repo.find_by_id(id)


class ProductService(IProductService):
    def __init__(self, repo: IProductRepository):
        self._repo = repo

    def get_all(self) -> list:
        return self._repo.find_all()

    def get_by_id(self, id: int) -> Optional[object]:
        return self._repo.find_by_id(id)


class CustomerService(ICustomerService):
    def __init__(self, repo: ICustomerRepository):
        self._repo = repo

    def get_all(self) -> list:
        return self._repo.find_all()

    def get_by_id(self, id: int) -> Optional[object]:
        return self._repo.find_by_id(id)


class OrderService(IOrderService):
    def __init__(self, repo: IOrderRepository):
        self._repo = repo

    def get_all(self) -> list:
        return self._repo.find_all()

    def get_by_customer(self, customer_id: int) -> list:
        return self._repo.find_by_customer_id(customer_id)
