import os
import logging
from pathlib import Path
from typing import Generator, List, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
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

# ---------------------------------------------------------------------------
# Shared overlay snippet — injected into both /docs and /
# ---------------------------------------------------------------------------
OVERLAY_GATE_SNIPPET = """
<style>
  #swagger-auth-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.25);
    z-index: 99990;
    pointer-events: auto;
  }
  #swagger-auth-trigger {
    position: fixed;
    top: 0;
    right: 0;
    width: 80px;
    height: 80px;
    z-index: 100000;
    background: transparent;
    pointer-events: auto;
    cursor: pointer;
    border: 0;
    padding: 0;
  }
  #swagger-auth-modal {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: min(340px, calc(100vw - 32px));
    background: #ffffff;
    border-radius: 12px;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.25);
    z-index: 100010;
    padding: 20px;
    font-family: Arial, sans-serif;
    display: none;
  }
  #swagger-auth-modal h3 {
    margin: 0 0 12px;
    font-size: 18px;
  }
  #swagger-auth-modal label {
    display: block;
    margin: 8px 0 4px;
    font-size: 13px;
    color: #333;
  }
  #swagger-auth-modal input {
    width: 100%;
    box-sizing: border-box;
    border: 1px solid #c9c9c9;
    border-radius: 8px;
    padding: 9px 10px;
    font-size: 14px;
  }
  #swagger-auth-submit {
    margin-top: 14px;
    width: 100%;
    border: 0;
    border-radius: 8px;
    background: #2f6fec;
    color: #fff;
    padding: 10px 12px;
    font-size: 14px;
    cursor: pointer;
  }
  #swagger-auth-error {
    min-height: 18px;
    margin-top: 10px;
    color: #c62828;
    font-size: 13px;
  }
</style>
<script>
  (function () {
    const REQUIRED_USERNAME = "admin";
    const REQUIRED_PASSWORD = "1234";
    const REQUIRED_CLICKS = 3;
    const WINDOW_MS = 1500;

    const originalBodyOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const overlay = document.createElement("div");
    overlay.id = "swagger-auth-overlay";
    overlay.setAttribute("aria-hidden", "true");

    const trigger = document.createElement("button");
    trigger.id = "swagger-auth-trigger";
    trigger.type = "button";
    trigger.setAttribute("aria-label", "Open authentication");

    const modal = document.createElement("div");
    modal.id = "swagger-auth-modal";
    modal.innerHTML = `
      <h3>Authentication Required</h3>
      <form id="swagger-auth-form">
        <label for="swagger-auth-username">Username</label>
        <input id="swagger-auth-username" name="username" type="text" autocomplete="off" required />
        <label for="swagger-auth-password">Password</label>
        <input id="swagger-auth-password" name="password" type="password" autocomplete="off" required />
        <button id="swagger-auth-submit" type="submit">Submit</button>
        <div id="swagger-auth-error" role="alert" aria-live="polite"></div>
      </form>
    `;

    document.body.appendChild(overlay);
    document.body.appendChild(trigger);
    document.body.appendChild(modal);

    const form = document.getElementById("swagger-auth-form");
    const usernameInput = document.getElementById("swagger-auth-username");
    const passwordInput = document.getElementById("swagger-auth-password");
    const errorNode = document.getElementById("swagger-auth-error");

    let clickCount = 0;
    let firstClickAt = 0;

    const stopScroll = function (event) {
      event.preventDefault();
    };

    overlay.addEventListener("wheel", stopScroll, { passive: false });
    overlay.addEventListener("touchmove", stopScroll, { passive: false });

    const showModal = function () {
      modal.style.display = "block";
      errorNode.textContent = "";
      usernameInput.focus();
    };

    const unlockPage = function () {
      overlay.removeEventListener("wheel", stopScroll);
      overlay.removeEventListener("touchmove", stopScroll);
      overlay.remove();
      trigger.remove();
      modal.remove();
      document.body.style.overflow = originalBodyOverflow;
    };

    trigger.addEventListener("click", function () {
      const now = Date.now();
      if (!firstClickAt || now - firstClickAt > WINDOW_MS) {
        firstClickAt = now;
        clickCount = 1;
      } else {
        clickCount += 1;
      }

      if (clickCount >= REQUIRED_CLICKS) {
        clickCount = 0;
        firstClickAt = 0;
        showModal();
      }
    });

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      const username = usernameInput.value.trim();
      const password = passwordInput.value;

      if (username === REQUIRED_USERNAME && password === REQUIRED_PASSWORD) {
        unlockPage();
      } else {
        errorNode.textContent = "Invalid username or password.";
      }
    });
  })();
</script>
"""

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
    docs_url=None,
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


@app.get("/docs", include_in_schema=False)
def custom_swagger_ui():
    docs_response = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        init_oauth=app.swagger_ui_init_oauth,
        swagger_ui_parameters=app.swagger_ui_parameters,
    )

    docs_response.body = docs_response.body.replace(
        b"</body>",
        OVERLAY_GATE_SNIPPET.encode("utf-8") + b"</body>",
    )
    return docs_response


if app.swagger_ui_oauth2_redirect_url:
    @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
    def swagger_ui_redirect():
        return get_swagger_ui_oauth2_redirect_html()


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
    response = app.state.templates.TemplateResponse(
        "index.html", {"request": request, "stats": stats}
    )
    patched = response.body.replace(
        b"</body>",
        OVERLAY_GATE_SNIPPET.encode("utf-8") + b"</body>",
    )
    return HTMLResponse(content=patched.decode("utf-8"), status_code=200)


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
