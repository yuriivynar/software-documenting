import os
import logging
from pathlib import Path
from typing import Generator, List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from dal.db_models import Base
from dal.csv_reader import CsvFileReader
from dal.db_repository import (
    CategoryRepository, ProductRepository, CustomerRepository,
    ShippingAddressRepository, OrderRepository,
    LineItemRepository, BucketRepository,
)
from bll.shop_service import (
    ImportService, CategoryService, ProductService,
    CustomerService, OrderService,
)
from bll.interfaces import (
    IImportService, ICategoryService, IProductService,
    ICustomerService, IOrderService,
)
from generator.csv_generator import generate as csv_generate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:@localhost:5432/docs_lab2"
)
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)



def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_import_service(db: Session = Depends(get_db)) -> IImportService:
    return ImportService(
        reader      = CsvFileReader(),
        cat_repo    = CategoryRepository(db),
        prod_repo   = ProductRepository(db),
        cust_repo   = CustomerRepository(db),
        addr_repo   = ShippingAddressRepository(db),
        order_repo  = OrderRepository(db),
        li_repo     = LineItemRepository(db),
        bucket_repo = BucketRepository(db),
        session     = db,
    )


def get_category_service(db: Session = Depends(get_db)) -> ICategoryService:
    return CategoryService(CategoryRepository(db))

def get_product_service(db: Session = Depends(get_db)) -> IProductService:
    return ProductService(ProductRepository(db))

def get_customer_service(db: Session = Depends(get_db)) -> ICustomerService:
    return CustomerService(CustomerRepository(db))

def get_order_service(db: Session = Depends(get_db)) -> IOrderService:
    return OrderService(OrderRepository(db))



class CategoryOut(BaseModel):
    id:          int
    name:        str
    description: str | None

    class Config:
        from_attributes = True


class ProductOut(BaseModel):
    id:          int
    name:        str
    price:       float
    description: str | None
    category_id: int

    class Config:
        from_attributes = True


class CustomerOut(BaseModel):
    id:            int
    email:         str
    customer_type: str
    first_name:    str | None
    last_name:     str | None
    company_name:  str | None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_custom(cls, obj):
        return cls(
            id            = obj.id,
            email         = obj.email,
            customer_type = obj.customer_type.value,
            first_name    = getattr(obj, "first_name", None),
            last_name     = getattr(obj, "last_name", None),
            company_name  = getattr(obj, "company_name", None),
        )


class LineItemOut(BaseModel):
    id:         int
    product_id: int
    quantity:   int
    unit_price: float
    order_id:   int | None
    bucket_id:  int | None

    class Config:
        from_attributes = True


class BucketOut(BaseModel):

    id:          int
    customer_id: int
    created_at:  str
    items:       List[LineItemOut]

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_custom(cls, obj):
        return cls(
            id          = obj.id,
            customer_id = obj.customer_id,
            created_at  = obj.created_at.isoformat(),
            items       = [
                LineItemOut(
                    id         = li.id,
                    product_id = li.product_id,
                    quantity   = li.quantity,
                    unit_price = li.unit_price,
                    order_id   = li.order_id,
                    bucket_id  = li.bucket_id,
                )
                for li in obj.line_items
            ],
        )


class OrderOut(BaseModel):

    id:                  int
    customer_id:         int
    shipping_address_id: int
    bucket_id:           int | None
    status:              str
    created_at:          str
    updated_at:          str | None
    total_amount:        float | None
    notes:               str | None   
    payment_method:      str | None   

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_custom(cls, obj):
        return cls(
            id                  = obj.id,
            customer_id         = obj.customer_id,
            shipping_address_id = obj.shipping_address_id,
            bucket_id           = obj.bucket_id,
            status              = obj.status.value,
            created_at          = obj.created_at.isoformat(),
            updated_at          = obj.updated_at.isoformat() if obj.updated_at else None,
            total_amount        = obj.total_amount,
            notes               = obj.notes,
            payment_method      = obj.payment_method.value if obj.payment_method else None,
        )


class ImportStats(BaseModel):
    categories:  int
    products:    int
    customers:   int
    addresses:   int
    buckets:     int
    orders:      int
    line_items:  int
    total:       int


class GenerateResult(BaseModel):
    output_path:  str
    total_rows:   int
    file_size_kb: float



app = FastAPI(
    title       = "Documenting Lab2 API",
    description = (
        "Demo API for Laboratory Work #2.\n\n"
    ),
    version = "2.0.0",
)



@app.post("/generate", response_model=GenerateResult,
          summary="Generate test CSV file", tags=["Data Generation"])
def generate_csv(
    output: str = Query(default="data.csv",   description="Output file path"),
    rows:   int = Query(default=1100, ge=100, description="Minimum line_item rows"),
):
    total   = csv_generate(output, target_line_items=rows)
    size_kb = round(Path(output).stat().st_size / 1024, 1)
    return GenerateResult(
        output_path  = str(Path(output).resolve()),
        total_rows   = total,
        file_size_kb = size_kb,
    )



@app.post("/import", response_model=ImportStats,
          summary="Import CSV into PostgreSQL", tags=["Import"])
def import_csv(
    file_path: str = Query(default="data.csv", description="Path to CSV file"),
    svc: IImportService = Depends(get_import_service),
):
    if not Path(file_path).exists():
        raise HTTPException(
            status_code=404,
            detail=f"File '{file_path}' not found. Call /generate first.",
        )
    try:
        stats = svc.import_from_file(file_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return ImportStats(
        categories = stats.get("categories", 0),
        products   = stats.get("products",   0),
        customers  = stats.get("customers",  0),
        addresses  = stats.get("addresses",  0),
        buckets    = stats.get("buckets",    0),
        orders     = stats.get("orders",     0),
        line_items = stats.get("line_items", 0),
        total      = sum(stats.values()),
    )



@app.get("/categories", response_model=List[CategoryOut],
         summary="List all categories", tags=["Categories"])
def list_categories(svc: ICategoryService = Depends(get_category_service)):
    return svc.get_all()

@app.get("/categories/{id}", response_model=CategoryOut,
         summary="Get category by ID", tags=["Categories"])
def get_category(id: int, svc: ICategoryService = Depends(get_category_service)):
    obj = svc.get_by_id(id)
    if not obj:
        raise HTTPException(status_code=404, detail=f"Category #{id} not found")
    return obj



@app.get("/products", response_model=List[ProductOut],
         summary="List all products", tags=["Products"])
def list_products(svc: IProductService = Depends(get_product_service)):
    return svc.get_all()

@app.get("/products/{id}", response_model=ProductOut,
         summary="Get product by ID", tags=["Products"])
def get_product(id: int, svc: IProductService = Depends(get_product_service)):
    obj = svc.get_by_id(id)
    if not obj:
        raise HTTPException(status_code=404, detail=f"Product #{id} not found")
    return obj



@app.get("/customers", response_model=List[CustomerOut],
         summary="List all customers", tags=["Customers"])
def list_customers(svc: ICustomerService = Depends(get_customer_service)):
    return [CustomerOut.from_orm_custom(c) for c in svc.get_all()]

@app.get("/customers/{id}", response_model=CustomerOut,
         summary="Get customer by ID", tags=["Customers"])
def get_customer(id: int, svc: ICustomerService = Depends(get_customer_service)):
    obj = svc.get_by_id(id)
    if not obj:
        raise HTTPException(status_code=404, detail=f"Customer #{id} not found")
    return CustomerOut.from_orm_custom(obj)



@app.get("/orders", response_model=List[OrderOut],
         summary="List all orders", tags=["Orders"])
def list_orders(svc: IOrderService = Depends(get_order_service)):
    return [OrderOut.from_orm_custom(o) for o in svc.get_all()]

@app.get("/orders/customer/{customer_id}", response_model=List[OrderOut],
         summary="Get orders for a specific customer", tags=["Orders"])
def get_orders_by_customer(
    customer_id: int,
    svc: IOrderService = Depends(get_order_service),
):
    return [OrderOut.from_orm_custom(o) for o in svc.get_by_customer(customer_id)]



@app.get("/", include_in_schema=False)
def root():
    return JSONResponse({
        "message": "API is running!",
        "docs":    "http://localhost:8000/docs",
    })
