from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from bll.interfaces import ICustomerService, IOrderService

router = APIRouter(prefix="/customers")


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def _customer_svc(request: Request) -> ICustomerService:
    return request.app.state.customer_service_factory(request)


def _order_svc(request: Request) -> IOrderService:
    return request.app.state.order_service_factory(request)


def _form_data(
    customer_type: str,
    email: str,
    first_name: str,
    last_name: str,
    company_name: str,
    tax_id: str,
):
    return {
        "customer_type": customer_type,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "company_name": company_name,
        "tax_id": tax_id,
    }


@router.get("", response_class=HTMLResponse, name="customers_index")
def index(request: Request):
    return _templates(request).TemplateResponse(
        "customers/index.html",
        {"request": request, "customers": _customer_svc(request).get_all()},
    )


@router.get("/create", response_class=HTMLResponse, name="customers_create_form")
def create_form(request: Request):
    return _templates(request).TemplateResponse(
        "customers/form.html",
        {
            "request": request,
            "customer": None,
            "error": None,
            "form_data": _form_data("personal", "", "", "", "", ""),
        },
    )


@router.post("/create", response_class=HTMLResponse, name="customers_create_submit")
def create_submit(
    request: Request,
    customer_type: str = Form(...),
    email: str = Form(...),
    first_name: str = Form(""),
    last_name: str = Form(""),
    company_name: str = Form(""),
    tax_id: str = Form(""),
):
    try:
        customer = _customer_svc(request).create(
            customer_type=customer_type,
            email=email,
            first_name=first_name,
            last_name=last_name,
            company_name=company_name,
            tax_id=tax_id,
        )
        return RedirectResponse(url=f"/customers/{customer.id}?created=1", status_code=303)
    except ValueError as exc:
        return _templates(request).TemplateResponse(
            "customers/form.html",
            {
                "request": request,
                "customer": None,
                "error": str(exc),
                "form_data": _form_data(
                    customer_type, email, first_name, last_name, company_name, tax_id
                ),
            },
            status_code=422,
        )


@router.get("/{id}/edit", response_class=HTMLResponse, name="customers_edit_form")
def edit_form(request: Request, id: int):
    customer = _customer_svc(request).get_by_id(id)
    if customer is None:
        return _templates(request).TemplateResponse(
            "404.html",
            {"request": request, "message": f"Customer #{id} not found"},
            status_code=404,
        )
    return _templates(request).TemplateResponse(
        "customers/form.html",
        {
            "request": request,
            "customer": customer,
            "error": None,
            "form_data": _form_data(
                customer.customer_type.value,
                customer.email,
                getattr(customer, "first_name", "") or "",
                getattr(customer, "last_name", "") or "",
                getattr(customer, "company_name", "") or "",
                getattr(customer, "tax_id", "") or "",
            ),
        },
    )


@router.post("/{id}/edit", response_class=HTMLResponse, name="customers_edit_submit")
def edit_submit(
    request: Request,
    id: int,
    customer_type: str = Form(...),
    email: str = Form(...),
    first_name: str = Form(""),
    last_name: str = Form(""),
    company_name: str = Form(""),
    tax_id: str = Form(""),
):
    try:
        customer = _customer_svc(request).update(
            id=id,
            customer_type=customer_type,
            email=email,
            first_name=first_name,
            last_name=last_name,
            company_name=company_name,
            tax_id=tax_id,
        )
        return RedirectResponse(url=f"/customers/{customer.id}?updated=1", status_code=303)
    except ValueError as exc:
        return _templates(request).TemplateResponse(
            "customers/form.html",
            {
                "request": request,
                "customer": _customer_svc(request).get_by_id(id),
                "error": str(exc),
                "form_data": _form_data(
                    customer_type, email, first_name, last_name, company_name, tax_id
                ),
            },
            status_code=422,
        )


@router.get("/{id}/delete", response_class=HTMLResponse, name="customers_delete_confirm")
def delete_confirm(request: Request, id: int):
    customer = _customer_svc(request).get_by_id(id)
    if customer is None:
        return _templates(request).TemplateResponse(
            "404.html",
            {"request": request, "message": f"Customer #{id} not found"},
            status_code=404,
        )
    return _templates(request).TemplateResponse(
        "customers/delete.html",
        {"request": request, "customer": customer, "error": None},
    )


@router.post("/{id}/delete", response_class=HTMLResponse, name="customers_delete_submit")
def delete_submit(request: Request, id: int):
    try:
        deleted = _customer_svc(request).delete(id)
        if not deleted:
            return _templates(request).TemplateResponse(
                "404.html",
                {"request": request, "message": f"Customer #{id} not found"},
                status_code=404,
            )
        return RedirectResponse(url="/customers?deleted=1", status_code=303)
    except ValueError as exc:
        return _templates(request).TemplateResponse(
            "customers/delete.html",
            {"request": request, "customer": _customer_svc(request).get_by_id(id), "error": str(exc)},
            status_code=409,
        )


@router.get("/{id}", response_class=HTMLResponse, name="customers_detail")
def detail(request: Request, id: int):
    customer = _customer_svc(request).get_by_id(id)
    if customer is None:
        return _templates(request).TemplateResponse(
            "404.html",
            {"request": request, "message": f"Customer #{id} not found"},
            status_code=404,
        )
    orders = _order_svc(request).get_by_customer(id)
    return _templates(request).TemplateResponse(
        "customers/detail.html",
        {"request": request, "customer": customer, "orders": orders},
    )
