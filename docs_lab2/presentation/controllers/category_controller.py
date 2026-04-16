from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from bll.interfaces import ICategoryService, IProductService

router = APIRouter(prefix="/categories")


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def _category_svc(request: Request) -> ICategoryService:
    return request.app.state.category_service_factory(request)


def _product_svc(request: Request) -> IProductService:
    return request.app.state.product_service_factory(request)


@router.get("", response_class=HTMLResponse, name="categories_index")
def index(request: Request):
    category_service = _category_svc(request)
    product_service = _product_svc(request)
    categories = category_service.get_all()
    cat_data = [
        {"category": category, "product_count": len(product_service.get_by_category(category.id))}
        for category in categories
    ]
    return _templates(request).TemplateResponse(
        "categories/index.html",
        {"request": request, "cat_data": cat_data},
    )


@router.get("/create", response_class=HTMLResponse, name="categories_create_form")
def create_form(request: Request):
    return _templates(request).TemplateResponse(
        "categories/form.html",
        {"request": request, "category": None, "error": None, "form_data": None},
    )


@router.post("/create", response_class=HTMLResponse, name="categories_create_submit")
def create_submit(request: Request, name: str = Form(...), description: str = Form("")):
    try:
        category = _category_svc(request).create(name, description)
        return RedirectResponse(url=f"/categories/{category.id}?created=1", status_code=303)
    except ValueError as exc:
        return _templates(request).TemplateResponse(
            "categories/form.html",
            {
                "request": request,
                "category": None,
                "error": str(exc),
                "form_data": {"name": name, "description": description},
            },
            status_code=422,
        )


@router.get("/{id}/edit", response_class=HTMLResponse, name="categories_edit_form")
def edit_form(request: Request, id: int):
    category = _category_svc(request).get_by_id(id)
    if category is None:
        return _templates(request).TemplateResponse(
            "404.html",
            {"request": request, "message": f"Category #{id} not found"},
            status_code=404,
        )
    return _templates(request).TemplateResponse(
        "categories/form.html",
        {"request": request, "category": category, "error": None, "form_data": None},
    )


@router.post("/{id}/edit", response_class=HTMLResponse, name="categories_edit_submit")
def edit_submit(request: Request, id: int, name: str = Form(...), description: str = Form("")):
    try:
        category = _category_svc(request).update(id, name, description)
        return RedirectResponse(url=f"/categories/{category.id}?updated=1", status_code=303)
    except ValueError as exc:
        return _templates(request).TemplateResponse(
            "categories/form.html",
            {
                "request": request,
                "category": _category_svc(request).get_by_id(id),
                "error": str(exc),
                "form_data": {"name": name, "description": description},
            },
            status_code=422,
        )


@router.get("/{id}/delete", response_class=HTMLResponse, name="categories_delete_confirm")
def delete_confirm(request: Request, id: int):
    category = _category_svc(request).get_by_id(id)
    if category is None:
        return _templates(request).TemplateResponse(
            "404.html",
            {"request": request, "message": f"Category #{id} not found"},
            status_code=404,
        )
    return _templates(request).TemplateResponse(
        "categories/delete.html",
        {"request": request, "category": category, "error": None},
    )


@router.post("/{id}/delete", response_class=HTMLResponse, name="categories_delete_submit")
def delete_submit(request: Request, id: int):
    try:
        deleted = _category_svc(request).delete(id)
        if not deleted:
            return _templates(request).TemplateResponse(
                "404.html",
                {"request": request, "message": f"Category #{id} not found"},
                status_code=404,
            )
        return RedirectResponse(url="/categories?deleted=1", status_code=303)
    except ValueError as exc:
        return _templates(request).TemplateResponse(
            "categories/delete.html",
            {"request": request, "category": _category_svc(request).get_by_id(id), "error": str(exc)},
            status_code=409,
        )


@router.get("/{id}", response_class=HTMLResponse, name="categories_detail")
def detail(request: Request, id: int):
    category = _category_svc(request).get_by_id(id)
    if category is None:
        return _templates(request).TemplateResponse(
            "404.html",
            {"request": request, "message": f"Category #{id} not found"},
            status_code=404,
        )
    products = _product_svc(request).get_by_category(id)
    return _templates(request).TemplateResponse(
        "categories/detail.html",
        {"request": request, "category": category, "products": products},
    )
