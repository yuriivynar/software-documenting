import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List



CATEGORIES = [
    ("Electronics",       "Smartphones, laptops, TVs and accessories"),
    ("Clothing",          "Men's and women's clothing for all seasons"),
    ("Footwear",          "Casual, sports and office shoes"),
    ("Books",             "Fiction, non-fiction and textbooks"),
    ("Sports & Outdoors", "Equipment and apparel for training"),
    ("Home & Garden",     "Furniture, decor and garden tools"),
    ("Beauty & Health",   "Cosmetics, perfumes and personal care"),
    ("Toys",              "Toys and board games for children"),
    ("Automotive",        "Spare parts and accessories"),
    ("Groceries",         "Coffee, tea, snacks and pantry staples"),
]

PRODUCT_TEMPLATES = [
    ("Smartphone {brand} {model}",  699.0,  0),
    ("Laptop {brand} {model}",     1899.0,  0),
    ("Headphones {brand}",          129.0,  0),
    ("Tablet {brand} {model}",      899.0,  0),
    ("{color} T-shirt {size}",       39.0,  1),
    ("{color} Jeans",                79.0,  1),
    ("{season} Jacket",             189.0,  1),
    ("{brand} Sneakers {size}",     159.0,  2),
    ("Leather Boots {color}",       219.0,  2),
    ('Novel "{title}"',              28.0,  3),
    ("Textbook on {subject}",        45.0,  3),
    ("{weight} kg Dumbbells",        69.0,  4),
    ("Yoga Mat",                     34.0,  4),
    ("Bicycle {model}",             789.0,  4),
    ("{color} Sofa",               1299.0,  5),
    ("Coffee Machine {brand}",      249.0,  9),
    ("{brand} Shampoo",              15.0,  6),
    ("{brand} Face Cream",           45.0,  6),
    ("Lego {model}",                 89.0,  7),
    ("{brand} Football",             39.0,  4),
]

BRANDS   = ["Samsung", "Apple", "Sony", "LG", "Nike", "Adidas",
            "Philips", "Xiaomi", "Lenovo", "HP", "Asus", "Puma"]
MODELS   = ["Pro", "Plus", "Ultra", "Air", "Max", "Lite",
            "X500", "Z3", "A7", "S21", "15i", "Neo"]
COLORS   = ["black", "white", "gray", "blue", "red", "green"]
SIZES    = ["XS", "S", "M", "L", "XL", "XXL"]
SEASONS  = ["winter", "autumn", "spring", "summer"]
SUBJECTS = ["algorithms", "databases", "machine learning", "web development"]
TITLES   = ["The Master and Margarita", "1984",
            "The Count of Monte Cristo", "The Three Musketeers"]
WEIGHTS  = ["2", "5", "8", "10", "15", "20"]

FIRST_NAMES = [
    "James", "Emma", "Oliver", "Sophia", "William", "Isabella",
    "Benjamin", "Mia", "Lucas", "Charlotte", "Henry", "Amelia",
    "Alexander", "Harper", "Michael", "Evelyn", "Daniel", "Abigail",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
    "Miller", "Davis", "Wilson", "Taylor", "Anderson", "Thomas",
    "Jackson", "White", "Harris", "Martin", "Thompson", "Moore",
]
COMPANY_TYPES = ["LLC", "Inc.", "Ltd.", "Corp."]
COMPANY_WORDS = ["Agro", "Tech", "Build", "Trade", "Service", "Plus", "Pro"]

STREETS = ["Main St", "Oak Ave", "Maple Dr", "Cedar Blvd",
           "Pine Rd", "Elm St", "Washington Blvd", "Park Ave"]
CITIES  = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
           "Philadelphia", "San Antonio", "San Diego", "Dallas", "Austin"]

STATUSES         = ["pending", "confirmed", "shipped", "delivered"]
PAYMENT_METHODS  = ["credit_card", "paypal", "bank_transfer", "apple_pay", "google_pay"]
ORDER_NOTES      = [
    "Please leave at the door",
    "Call before delivery",
    "Fragile items, handle with care",
    "Ring the bell twice",
    "Leave with neighbor if absent",
    "",
    "", "", "", "",
]



def _product_name(template: str) -> str:
    return template.format(
        brand=random.choice(BRANDS),   model=random.choice(MODELS),
        color=random.choice(COLORS),   size=random.choice(SIZES),
        season=random.choice(SEASONS), subject=random.choice(SUBJECTS),
        title=random.choice(TITLES),   weight=random.choice(WEIGHTS),
    )


def _random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def _to_email_part(text: str) -> str:
    return text.lower().replace(" ", ".").replace("'", "")[:20]


def _unique_email(base: str, used: set, uid: int) -> str:
    domains = ["gmail.com", "yahoo.com", "outlook.com", "proton.me"]
    base = _to_email_part(base)
    for domain in domains:
        email = f"{base}@{domain}"
        if email not in used:
            used.add(email)
            return email
    email = f"{base}{uid}@gmail.com"
    used.add(email)
    return email


def _row(record_type: str, **kwargs) -> dict:
    return {
        "record_type":         record_type,
        "id":                  kwargs.get("id", ""),
        "name":                kwargs.get("name", ""),
        "description":         kwargs.get("description", ""),
        "price":               kwargs.get("price", ""),
        "category_id":         kwargs.get("category_id", ""),
        "email":               kwargs.get("email", ""),
        "first_name":          kwargs.get("first_name", ""),
        "last_name":           kwargs.get("last_name", ""),
        "company_name":        kwargs.get("company_name", ""),
        "tax_id":              kwargs.get("tax_id", ""),
        "street":              kwargs.get("street", ""),
        "city":                kwargs.get("city", ""),
        "country":             kwargs.get("country", ""),
        "postal_code":         kwargs.get("postal_code", ""),
        "customer_id":         kwargs.get("customer_id", ""),
        "shipping_address_id": kwargs.get("shipping_address_id", ""),
        "bucket_id":           kwargs.get("bucket_id", ""),
        "status":              kwargs.get("status", ""),
        "created_at":          kwargs.get("created_at", ""),
        "updated_at":          kwargs.get("updated_at", ""),
        "total_amount":        kwargs.get("total_amount", ""),
        "notes":               kwargs.get("notes", ""),
        "payment_method":      kwargs.get("payment_method", ""),
        "order_id":            kwargs.get("order_id", ""),
        "product_id":          kwargs.get("product_id", ""),
        "quantity":            kwargs.get("quantity", ""),
        "unit_price":          kwargs.get("unit_price", ""),
    }



def generate(output_path: str, target_line_items: int = 1100,
             delimiter: str = ",") -> int:

    if delimiter not in (",", ";"):
        raise ValueError(f"Unsupported delimiter: {delimiter!r}. Use ',' or ';'.")
    random.seed(42)

    DATE_START = datetime(2023, 1, 1)
    DATE_END   = datetime(2025, 12, 31)
    rows: List[dict] = []

    cat_ids = list(range(1, len(CATEGORIES) + 1))
    for i, (name, desc) in enumerate(CATEGORIES, start=1):
        rows.append(_row("category", id=i, name=name, description=desc))

    product_prices: Dict[int, float] = {}
    product_ids: List[int] = []
    pid = 1
    for _ in range(120):
        tmpl, base_price, cat_offset = random.choice(PRODUCT_TEMPLATES)
        cat_id = cat_ids[cat_offset % len(cat_ids)]
        price  = round(base_price * random.uniform(0.7, 1.3), 2)
        rows.append(_row("product",
            id=pid, name=_product_name(tmpl),
            price=price, description=f"SKU: P{pid:05d}",
            category_id=cat_id,
        ))
        product_prices[pid] = price
        product_ids.append(pid)
        pid += 1

    customer_ids: List[int] = []
    used_emails: set = set()
    cid = 1

    for _ in range(150):
        fn, ln = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
        rows.append(_row("personal_customer",
            id=cid,
            email=_unique_email(f"{fn}.{ln}", used_emails, cid),
            first_name=fn, last_name=ln,
        ))
        customer_ids.append(cid); cid += 1

    for i in range(50):
        company = (f"{random.choice(COMPANY_WORDS)}"
                   f"{random.choice(COMPANY_WORDS)} "
                   f"{random.choice(COMPANY_TYPES)}")
        rows.append(_row("corporate_customer",
            id=cid,
            email=_unique_email(f"info{i}", used_emails, cid),
            company_name=company,
            tax_id=str(random.randint(10_000_000, 99_999_999)),
        ))
        customer_ids.append(cid); cid += 1

    address_ids: List[int] = []
    customer_addresses: Dict[int, List[int]] = {}
    aid = 1
    for c_id in customer_ids:
        count = random.choices([1, 2], weights=[60, 40])[0]
        customer_addresses[c_id] = []
        for _ in range(count):
            rows.append(_row("shipping_address",
                id=aid, customer_id=c_id,
                street=f"{random.randint(1, 999)} {random.choice(STREETS)}",
                city=random.choice(CITIES), country="USA",
                postal_code=str(random.randint(10000, 99999)),
            ))
            address_ids.append(aid)
            customer_addresses[c_id].append(aid)
            aid += 1

    bucket_ids: List[int] = []
    bucket_customer_map: Dict[int, int] = {}
    shuffled_customers = customer_ids[:]
    random.shuffle(shuffled_customers)
    for bid, c_id in enumerate(shuffled_customers[:180], start=1):
        created = _random_date(DATE_START, DATE_END)
        rows.append(_row("bucket",
            id=bid, customer_id=c_id,
            created_at=created.isoformat(),
        ))
        bucket_ids.append(bid)
        bucket_customer_map[bid] = c_id

    order_ids: List[int] = []
    buckets_used_by_orders: List[int] = []
    oid = 1
    for _ in range(300):
        c_id    = random.choice(customer_ids)
        a_list  = customer_addresses.get(c_id) or address_ids
        a_id    = random.choice(a_list)
        created = _random_date(DATE_START, DATE_END)
        # Decide if this order came from a bucket
        use_bucket = random.random() < 0.6 and bucket_ids
        b_id = random.choice(bucket_ids) if use_bucket else ""
        if b_id:
            buckets_used_by_orders.append(b_id)
        status = random.choice(STATUSES)
        if status != "pending":
            updated = created + timedelta(hours=random.randint(1, 72))
        else:
            updated = ""
        rows.append(_row("order",
            id=oid, customer_id=c_id,
            shipping_address_id=a_id,
            bucket_id=b_id,
            status=status,
            created_at=created.isoformat(),
            updated_at=updated.isoformat() if updated else "",
            payment_method=random.choice(PAYMENT_METHODS),
            notes=random.choice(ORDER_NOTES),
        ))
        order_ids.append(oid); oid += 1

    li_id = 1
    order_totals: Dict[int, float] = {o: 0.0 for o in order_ids}

    for b_id in bucket_ids:
        count   = random.randint(1, 4)
        chosen  = random.sample(product_ids, min(count, len(product_ids)))
        for p_id in chosen:
            qty = random.randint(1, 3)
            rows.append(_row("line_item",
                id=li_id,
                bucket_id=b_id,
                order_id="",
                product_id=p_id,
                quantity=qty,
                unit_price=product_prices[p_id],
            ))
            li_id += 1

    for o_id in order_ids:
        chosen = random.sample(product_ids, min(random.randint(2, 6), len(product_ids)))
        for p_id in chosen:
            qty   = random.randint(1, 5)
            price = product_prices[p_id]
            rows.append(_row("line_item",
                id=li_id,
                order_id=o_id,
                bucket_id="",
                product_id=p_id,
                quantity=qty,
                unit_price=price,
            ))
            order_totals[o_id] += qty * price
            li_id += 1

    while li_id - 1 < target_line_items:
        o_id  = random.choice(order_ids)
        p_id  = random.choice(product_ids)
        qty   = random.randint(1, 3)
        price = product_prices[p_id]
        rows.append(_row("line_item",
            id=li_id, order_id=o_id, bucket_id="",
            product_id=p_id, quantity=qty, unit_price=price,
        ))
        order_totals[o_id] += qty * price
        li_id += 1

    order_row_index: Dict[int, int] = {}
    for idx, row in enumerate(rows):
        if row["record_type"] == "order":
            order_row_index[int(row["id"])] = idx

    for o_id, total in order_totals.items():
        if o_id in order_row_index:
            rows[order_row_index[o_id]]["total_amount"] = round(total, 2)

    fieldnames = list(rows[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def main():
    parser = argparse.ArgumentParser(
        description="CSV test data generator for the lab project."
    )
    parser.add_argument("--output", "-o", default="data.csv",
                        help="Output file path (default: data.csv)")
    parser.add_argument("--rows", "-r", type=int, default=1100,
                        help="Minimum line_item rows (default: 1100)")
    parser.add_argument(
        "--delimiter", "-d", default=",", choices=[",", ";"],
        help="Column separator: ',' (default) or ';'",
    )
    args = parser.parse_args()

    delim_name = "comma (,)" if args.delimiter == "," else "semicolon (;)"
    print(f"Generating → {args.output}  [delimiter: {delim_name}] ...")
    total = generate(args.output, target_line_items=args.rows,
                     delimiter=args.delimiter)
    size  = Path(args.output).stat().st_size
    print(f"Done!  Rows: {total:,}  |  Size: {size:,} bytes")


if __name__ == "__main__":
    main()
