from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from bll.interfaces import ICategoryService, IProductService

router = APIRouter(prefix="/products")


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def _product_svc(request: Request) -> IProductService:
    return request.app.state.product_service_factory(request)


def _category_svc(request: Request) -> ICategoryService:
    return request.app.state.category_service_factory(request)


@router.get("", response_class=HTMLResponse, name="products_index")
def index(request: Request, q: Optional[str] = None, category_id: Optional[int] = None):
    product_service = _product_svc(request)
    category_service = _category_svc(request)

    if q:
        products = product_service.search(q)
    elif category_id:
        products = product_service.get_by_category(category_id)
    else:
        products = product_service.get_all()

    return _templates(request).TemplateResponse(
        "products/index.html",
        {
            "request": request,
            "products": products,
            "categories": category_service.get_all(),
            "query": q or "",
            "selected_cat": category_id,
            "total": len(products),
        },
    )


@router.get("/create", response_class=HTMLResponse, name="products_create_form")
def create_form(request: Request):
    return _templates(request).TemplateResponse(
        "products/form.html",
        {
            "request": request,
            "product": None,
            "categories": _category_svc(request).get_all(),
            "error": None,
            "form_data": None,
        },
    )


@router.post("/create", response_class=HTMLResponse, name="products_create_submit")
def create_submit(
    request: Request,
    name: str = Form(...),
    price: float = Form(...),
    description: str = Form(""),
    category_id: int = Form(...),
):
    try:
        product = _product_svc(request).create(name, price, description, category_id)
        return RedirectResponse(url=f"/products/{product.id}?created=1", status_code=303)
    except ValueError as exc:
        return _templates(request).TemplateResponse(
            "products/form.html",
            {
                "request": request,
                "product": None,
                "categories": _category_svc(request).get_all(),
                "error": str(exc),
                "form_data": {
                    "name": name,
                    "price": price,
                    "description": description,
                    "category_id": category_id,
                },
            },
            status_code=422,
        )


@router.get("/{id}/edit", response_class=HTMLResponse, name="products_edit_form")
def edit_form(request: Request, id: int):
    product = _product_svc(request).get_by_id(id)
    if product is None:
        return _templates(request).TemplateResponse(
            "404.html",
            {"request": request, "message": f"Product #{id} not found"},
            status_code=404,
        )
    return _templates(request).TemplateResponse(
        "products/form.html",
        {
            "request": request,
            "product": product,
            "categories": _category_svc(request).get_all(),
            "error": None,
            "form_data": None,
        },
    )


@router.post("/{id}/edit", response_class=HTMLResponse, name="products_edit_submit")
def edit_submit(
    request: Request,
    id: int,
    name: str = Form(...),
    price: float = Form(...),
    description: str = Form(""),
    category_id: int = Form(...),
):
    try:
        product = _product_svc(request).update(id, name, price, description, category_id)
        return RedirectResponse(url=f"/products/{product.id}?updated=1", status_code=303)
    except ValueError as exc:
        return _templates(request).TemplateResponse(
            "products/form.html",
            {
                "request": request,
                "product": _product_svc(request).get_by_id(id),
                "categories": _category_svc(request).get_all(),
                "error": str(exc),
                "form_data": {
                    "name": name,
                    "price": price,
                    "description": description,
                    "category_id": category_id,
                },
            },
            status_code=422,
        )


@router.get("/{id}/delete", response_class=HTMLResponse, name="products_delete_confirm")
def delete_confirm(request: Request, id: int):
    product = _product_svc(request).get_by_id(id)
    if product is None:
        return _templates(request).TemplateResponse(
            "404.html",
            {"request": request, "message": f"Product #{id} not found"},
            status_code=404,
        )
    return _templates(request).TemplateResponse(
        "products/delete.html",
        {"request": request, "product": product, "error": None},
    )


@router.post("/{id}/delete", response_class=HTMLResponse, name="products_delete_submit")
def delete_submit(request: Request, id: int):
    try:
        deleted = _product_svc(request).delete(id)
        if not deleted:
            return _templates(request).TemplateResponse(
                "404.html",
                {"request": request, "message": f"Product #{id} not found"},
                status_code=404,
            )
        return RedirectResponse(url="/products?deleted=1", status_code=303)
    except ValueError as exc:
        return _templates(request).TemplateResponse(
            "products/delete.html",
            {"request": request, "product": _product_svc(request).get_by_id(id), "error": str(exc)},
            status_code=409,
        )


@router.get("/{id}", response_class=HTMLResponse, name="products_detail")
def detail(request: Request, id: int):
    product = _product_svc(request).get_by_id(id)
    if product is None:
        return _templates(request).TemplateResponse(
            "404.html",
            {"request": request, "message": f"Product #{id} not found"},
            status_code=404,
        )
    return _templates(request).TemplateResponse(
        "products/detail.html",
        {"request": request, "product": product},
    )
