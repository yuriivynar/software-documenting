from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from bll.interfaces import ICustomerService, IOrderService, IProductService
from dal.db_models import OrderStatus, PaymentMethod

router = APIRouter(prefix="/orders")


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def _order_svc(request: Request) -> IOrderService:
    return request.app.state.order_service_factory(request)


def _customer_svc(request: Request) -> ICustomerService:
    return request.app.state.customer_service_factory(request)


def _product_svc(request: Request) -> IProductService:
    return request.app.state.product_service_factory(request)


def _context(request: Request, order=None, error: Optional[str] = None, form_data=None):
    return {
        "request": request,
        "order": order,
        "error": error,
        "form_data": form_data,
        "customers": _customer_svc(request).get_all(),
        "products": _product_svc(request).get_all(),
        "statuses": [status.value for status in OrderStatus],
        "payment_methods": [method.value for method in PaymentMethod],
    }


async def _extract_order_form(request: Request):
    form = await request.form()
    product_ids = form.getlist("product_id[]")
    quantities = form.getlist("quantity[]")
    items = []
    for product_id, quantity in zip(product_ids, quantities):
        if not str(product_id).strip() and not str(quantity).strip():
            continue
        items.append({"product_id": product_id, "quantity": quantity})
    return {
        "customer_id": form.get("customer_id", ""),
        "status": form.get("status", ""),
        "payment_method": form.get("payment_method", ""),
        "notes": form.get("notes", ""),
        "street": form.get("street", ""),
        "city": form.get("city", ""),
        "country": form.get("country", ""),
        "postal_code": form.get("postal_code", ""),
        "items": items,
    }


def _coerce_order_payload(raw_data):
    return {
        "customer_id": int(raw_data["customer_id"]),
        "shipping_address": {
            "street": raw_data["street"],
            "city": raw_data["city"],
            "country": raw_data["country"],
            "postal_code": raw_data["postal_code"],
        },
        "status": raw_data["status"],
        "payment_method": raw_data["payment_method"],
        "notes": raw_data["notes"],
        "items": raw_data["items"],
    }


@router.get("", response_class=HTMLResponse, name="orders_index")
def index(request: Request):
    return _templates(request).TemplateResponse(
        "orders/index.html",
        {"request": request, "orders": _order_svc(request).get_all()},
    )


@router.get("/create", response_class=HTMLResponse, name="orders_create_form")
def create_form(request: Request):
    return _templates(request).TemplateResponse(
        "orders/form.html",
        _context(
            request,
            form_data={
                "customer_id": "",
                "status": OrderStatus.PENDING.value,
                "payment_method": "",
                "notes": "",
                "street": "",
                "city": "",
                "country": "",
                "postal_code": "",
                "items": [{"product_id": "", "quantity": 1}],
            },
        ),
    )


@router.post("/create", response_class=HTMLResponse, name="orders_create_submit")
async def create_submit(request: Request):
    raw_data = await _extract_order_form(request)
    try:
        order = _order_svc(request).create(**_coerce_order_payload(raw_data))
        return RedirectResponse(url=f"/orders/{order.id}?created=1", status_code=303)
    except (ValueError, TypeError) as exc:
        if not raw_data["items"]:
            raw_data["items"] = [{"product_id": "", "quantity": 1}]
        return _templates(request).TemplateResponse(
            "orders/form.html",
            _context(request, error=str(exc), form_data=raw_data),
            status_code=422,
        )


@router.get("/{id}/edit", response_class=HTMLResponse, name="orders_edit_form")
def edit_form(request: Request, id: int):
    order = _order_svc(request).get_by_id(id)
    if order is None:
        return _templates(request).TemplateResponse(
            "404.html",
            {"request": request, "message": f"Order #{id} not found"},
            status_code=404,
        )
    form_data = {
        "customer_id": order.customer_id,
        "status": order.status.value,
        "payment_method": order.payment_method.value if order.payment_method else "",
        "notes": order.notes or "",
        "street": order.shipping_address.street if order.shipping_address else "",
        "city": order.shipping_address.city if order.shipping_address else "",
        "country": order.shipping_address.country if order.shipping_address else "",
        "postal_code": order.shipping_address.postal_code if order.shipping_address else "",
        "items": [
            {"product_id": line_item.product_id, "quantity": line_item.quantity}
            for line_item in order.line_items
        ]
        or [{"product_id": "", "quantity": 1}],
    }
    return _templates(request).TemplateResponse(
        "orders/form.html",
        _context(request, order=order, form_data=form_data),
    )


@router.post("/{id}/edit", response_class=HTMLResponse, name="orders_edit_submit")
async def edit_submit(request: Request, id: int):
    raw_data = await _extract_order_form(request)
    try:
        order = _order_svc(request).update(id=id, **_coerce_order_payload(raw_data))
        return RedirectResponse(url=f"/orders/{order.id}?updated=1", status_code=303)
    except (ValueError, TypeError) as exc:
        if not raw_data["items"]:
            raw_data["items"] = [{"product_id": "", "quantity": 1}]
        return _templates(request).TemplateResponse(
            "orders/form.html",
            _context(request, order=_order_svc(request).get_by_id(id), error=str(exc), form_data=raw_data),
            status_code=422,
        )


@router.get("/{id}/delete", response_class=HTMLResponse, name="orders_delete_confirm")
def delete_confirm(request: Request, id: int):
    order = _order_svc(request).get_by_id(id)
    if order is None:
        return _templates(request).TemplateResponse(
            "404.html",
            {"request": request, "message": f"Order #{id} not found"},
            status_code=404,
        )
    return _templates(request).TemplateResponse(
        "orders/delete.html",
        {"request": request, "order": order, "error": None},
    )


@router.post("/{id}/delete", response_class=HTMLResponse, name="orders_delete_submit")
def delete_submit(request: Request, id: int):
    deleted = _order_svc(request).delete(id)
    if not deleted:
        return _templates(request).TemplateResponse(
            "404.html",
            {"request": request, "message": f"Order #{id} not found"},
            status_code=404,
        )
    return RedirectResponse(url="/orders?deleted=1", status_code=303)


@router.get("/{id}", response_class=HTMLResponse, name="orders_detail")
def detail(request: Request, id: int):
    order = _order_svc(request).get_by_id(id)
    if order is None:
        return _templates(request).TemplateResponse(
            "404.html",
            {"request": request, "message": f"Order #{id} not found"},
            status_code=404,
        )
    total = round(sum(line_item.quantity * line_item.unit_price for line_item in order.line_items), 2)
    return _templates(request).TemplateResponse(
        "orders/detail.html",
        {"request": request, "order": order, "total": total},
    )
