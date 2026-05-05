import logging
import os
from pathlib import Path
from typing import Generator, List, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from bll.interfaces import (
    ICategoryService,
    ICustomerService,
    IImportService,
    IOrderService,
    IProductService,
)
from bll.shop_service import CategoryService, CustomerService, ImportService, OrderService, ProductService
from dal.csv_reader import CsvFileReader
from dal.db_models import Base
from dal.db_repository import (
    BucketRepository,
    CategoryRepository,
    CustomerRepository,
    LineItemRepository,
    OrderRepository,
    ProductRepository,
    ShippingAddressRepository,
)
from generator.csv_generator import generate as csv_generate
from presentation.controllers.category_controller import router as category_mvc_router
from presentation.controllers.customer_controller import router as customer_mvc_router
from presentation.controllers.order_controller import router as order_mvc_router
from presentation.controllers.product_controller import router as product_mvc_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:@localhost:5432/docs_lab2")
ENGINE_KWARGS = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, **ENGINE_KWARGS)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class CategoryOut(BaseModel):
    id: int
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True


class ProductOut(BaseModel):
    id: int
    name: str
    price: float
    description: Optional[str]
    category_id: int

    class Config:
        from_attributes = True


class CustomerOut(BaseModel):
    id: int
    email: str
    customer_type: str
    first_name: Optional[str]
    last_name: Optional[str]
    company_name: Optional[str]
    tax_id: Optional[str]

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_custom(cls, obj):
        return cls(
            id=obj.id,
            email=obj.email,
            customer_type=obj.customer_type.value,
            first_name=getattr(obj, "first_name", None),
            last_name=getattr(obj, "last_name", None),
            company_name=getattr(obj, "company_name", None),
            tax_id=getattr(obj, "tax_id", None),
        )


class OrderOut(BaseModel):
    id: int
    customer_id: int
    shipping_address_id: int
    bucket_id: Optional[int]
    status: str
    created_at: str
    updated_at: Optional[str]
    total_amount: Optional[float]
    notes: Optional[str]
    payment_method: Optional[str]

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_custom(cls, obj):
        return cls(
            id=obj.id,
            customer_id=obj.customer_id,
            shipping_address_id=obj.shipping_address_id,
            bucket_id=obj.bucket_id,
            status=obj.status.value,
            created_at=obj.created_at.isoformat(),
            updated_at=obj.updated_at.isoformat() if obj.updated_at else None,
            total_amount=obj.total_amount,
            notes=obj.notes,
            payment_method=obj.payment_method.value if obj.payment_method else None,
        )


class ImportStats(BaseModel):
    categories: int
    products: int
    customers: int
    addresses: int
    buckets: int
    orders: int
    line_items: int
    total: int


class GenerateResult(BaseModel):
    output_path: str
    total_rows: int
    file_size_kb: float


app = FastAPI(
    title="Documenting Lab3 — Shop MVC",
    description=(
        "E-Shop web application built with the MVC pattern.\n\n"
        "- HTML MVC interface lives at `/`\n"
        "- JSON endpoints are available under `/api`\n"
        "- Swagger UI remains at `/docs`"
    ),
    version="3.0.0",
)

templates_dir = Path(__file__).parent / "presentation" / "templates"
app.state.templates = Jinja2Templates(directory=str(templates_dir))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_import_service(db: Session = Depends(get_db)) -> IImportService:
    return ImportService(
        reader=CsvFileReader(),
        cat_repo=CategoryRepository(db),
        prod_repo=ProductRepository(db),
        cust_repo=CustomerRepository(db),
        addr_repo=ShippingAddressRepository(db),
        order_repo=OrderRepository(db),
        li_repo=LineItemRepository(db),
        bucket_repo=BucketRepository(db),
        session=db,
    )


def get_category_service(db: Session = Depends(get_db)) -> ICategoryService:
    return CategoryService(CategoryRepository(db), db)


def get_product_service(db: Session = Depends(get_db)) -> IProductService:
    return ProductService(ProductRepository(db), CategoryRepository(db), db)


def get_customer_service(db: Session = Depends(get_db)) -> ICustomerService:
    return CustomerService(CustomerRepository(db), db)


def get_order_service(db: Session = Depends(get_db)) -> IOrderService:
    return OrderService(
        OrderRepository(db),
        CustomerRepository(db),
        ProductRepository(db),
        ShippingAddressRepository(db),
        LineItemRepository(db),
        db,
    )


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    request.state.db = SessionLocal()
    try:
        response = await call_next(request)
    finally:
        request.state.db.close()
    return response


app.state.product_service_factory = lambda req: ProductService(
    ProductRepository(req.state.db),
    CategoryRepository(req.state.db),
    req.state.db,
)
app.state.category_service_factory = lambda req: CategoryService(
    CategoryRepository(req.state.db),
    req.state.db,
)
app.state.customer_service_factory = lambda req: CustomerService(
    CustomerRepository(req.state.db),
    req.state.db,
)
app.state.order_service_factory = lambda req: OrderService(
    OrderRepository(req.state.db),
    CustomerRepository(req.state.db),
    ProductRepository(req.state.db),
    ShippingAddressRepository(req.state.db),
    LineItemRepository(req.state.db),
    req.state.db,
)

app.include_router(product_mvc_router)
app.include_router(category_mvc_router)
app.include_router(customer_mvc_router)
app.include_router(order_mvc_router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard(request: Request):
    db = request.state.db
    stats = {
        "products": len(ProductRepository(db).find_all()),
        "categories": len(CategoryRepository(db).find_all()),
        "customers": len(CustomerRepository(db).find_all()),
        "orders": len(OrderRepository(db).find_all()),
    }
    return app.state.templates.TemplateResponse("index.html", {"request": request, "stats": stats})


api_router = APIRouter(prefix="/api", tags=["API"])


@api_router.post("/generate", response_model=GenerateResult, tags=["Data Generation"])
def generate_csv(
    output: str = Query(default="data.csv", description="Output file path"),
    rows: int = Query(default=1100, ge=100, description="Minimum line_item rows"),
    delimiter: str = Query(default=",", description="CSV delimiter: ',' or ';'", pattern="^[,;]$"),
):
    total_rows = csv_generate(output, target_line_items=rows, delimiter=delimiter)
    size_kb = round(Path(output).stat().st_size / 1024, 1)
    return GenerateResult(output_path=str(Path(output).resolve()), total_rows=total_rows, file_size_kb=size_kb)


@api_router.post("/import", response_model=ImportStats, tags=["Import"])
def import_csv(
    file_path: str = Query(default="data.csv", description="Path to CSV file"),
    svc: IImportService = Depends(get_import_service),
):
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail=f"File '{file_path}' not found. Call /api/generate first.")
    stats = svc.import_from_file(file_path)
    return ImportStats(
        categories=stats.get("categories", 0),
        products=stats.get("products", 0),
        customers=stats.get("customers", 0),
        addresses=stats.get("addresses", 0),
        buckets=stats.get("buckets", 0),
        orders=stats.get("orders", 0),
        line_items=stats.get("line_items", 0),
        total=sum(stats.values()),
    )


@api_router.get("/categories", response_model=List[CategoryOut], tags=["Categories"])
def api_list_categories(svc: ICategoryService = Depends(get_category_service)):
    return svc.get_all()


@api_router.get("/categories/{id}", response_model=CategoryOut, tags=["Categories"])
def api_get_category(id: int, svc: ICategoryService = Depends(get_category_service)):
    category = svc.get_by_id(id)
    if category is None:
        raise HTTPException(status_code=404, detail=f"Category #{id} not found")
    return category


@api_router.get("/products", response_model=List[ProductOut], tags=["Products"])
def api_list_products(svc: IProductService = Depends(get_product_service)):
    return svc.get_all()


@api_router.get("/products/{id}", response_model=ProductOut, tags=["Products"])
def api_get_product(id: int, svc: IProductService = Depends(get_product_service)):
    product = svc.get_by_id(id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product #{id} not found")
    return product


@api_router.get("/customers", response_model=List[CustomerOut], tags=["Customers"])
def api_list_customers(svc: ICustomerService = Depends(get_customer_service)):
    return [CustomerOut.from_orm_custom(customer) for customer in svc.get_all()]


@api_router.get("/customers/{id}", response_model=CustomerOut, tags=["Customers"])
def api_get_customer(id: int, svc: ICustomerService = Depends(get_customer_service)):
    customer = svc.get_by_id(id)
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Customer #{id} not found")
    return CustomerOut.from_orm_custom(customer)


@api_router.get("/orders", response_model=List[OrderOut], tags=["Orders"])
def api_list_orders(svc: IOrderService = Depends(get_order_service)):
    return [OrderOut.from_orm_custom(order) for order in svc.get_all()]


@api_router.get("/orders/{id}", response_model=OrderOut, tags=["Orders"])
def api_get_order(id: int, svc: IOrderService = Depends(get_order_service)):
    order = svc.get_by_id(id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order #{id} not found")
    return OrderOut.from_orm_custom(order)


@api_router.get("/orders/customer/{customer_id}", response_model=List[OrderOut], tags=["Orders"])
def api_get_orders_by_customer(customer_id: int, svc: IOrderService = Depends(get_order_service)):
    return [OrderOut.from_orm_custom(order) for order in svc.get_by_customer(customer_id)]


app.include_router(api_router)
