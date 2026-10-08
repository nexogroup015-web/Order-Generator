from docx import Document
from docx.shared import Pt
from io import BytesIO

SEPARATOR = "─" * 50

CURRENCY_SYMBOLS = {
    "EUR": "€",
    "USD": "$",
    "GBP": "£",
    "BRL": "R$",
}


def _format_order(order):
    lines = []
    line_items = order.get("line_items", [])

    # Contagem total de itens (expande por quantidade)
    total_qty = sum(item.get("quantity", 1) for item in line_items)
    order_name = order.get("name", "")
    lines.append(f"{order_name}{'/' * total_qty}")

    # Itens do pedido
    for item in line_items:
        qty = item.get("quantity", 1)
        product_name = item.get("title", "")
        variant_title = item.get("variant_title") or ""
        properties = {p["name"]: p["value"] for p in item.get("properties", [])}

        # Detecta customização
        name_val = (
            properties.get("Name")
            or properties.get("Nome")
            or properties.get("name")
            or ""
        )
        number_val = (
            properties.get("Number")
            or properties.get("Número")
            or properties.get("Numero")
            or properties.get("number")
            or ""
        )
        has_customize = bool(name_val or number_val)

        # Separa tamanho e edição do variant_title
        size_parts = [p.strip() for p in variant_title.split("/")] if variant_title else []
        size = size_parts[0] if size_parts else ""
        edition = " / ".join(size_parts[1:]) if len(size_parts) > 1 else ""

        for _ in range(qty):
            lines.append(product_name)

            size_line = f"Tamanho: {size}"
            if edition:
                size_line += f" / {edition}"
            size_line += " / Customize" if has_customize else " / Not customize"
            lines.append(size_line)

            if has_customize:
                if name_val:
                    lines.append(f"Name: {name_val}")
                if number_val:
                    lines.append(f"Number: {number_val}")

    # Valores financeiros
    currency = order.get("currency", "EUR")
    symbol = CURRENCY_SYMBOLS.get(currency, currency + " ")
    subtotal = order.get("subtotal_price", "0.00")
    shipping_lines = order.get("shipping_lines", [])
    shipping = shipping_lines[0]["price"] if shipping_lines else "0.00"
    total = order.get("total_price", "0.00")
    lines.append(
        f"Subtotal: {symbol}{subtotal}   Envío: {symbol}{shipping}   TOTAL: {symbol}{total}"
    )

    # Dados do cliente
    addr = order.get("shipping_address") or {}
    cust = order.get("customer") or {}

    full_name = (
        addr.get("name")
        or f"{cust.get('first_name', '')} {cust.get('last_name', '')}".strip()
        or "—"
    )
    address = addr.get("address1", "")
    if addr.get("address2"):
        address += f", {addr['address2']}"
    postcode = addr.get("zip", "")
    state = addr.get("province", "")
    city = addr.get("city", "")
    country = addr.get("country", "")
    phone = addr.get("phone") or cust.get("phone", "")

    lines.append(f"Name: {full_name}")
    lines.append(f"Address: {address}")
    lines.append(f"Post code: {postcode}")
    lines.append(f"State: {state}")
    lines.append(f"City: {city}")
    lines.append(f"Country: {country}")
    lines.append(f"Phone Number: {phone}")
    lines.append(SEPARATOR)

    return lines


def generate_document(orders):
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    for order in orders:
        for line in _format_order(order):
            doc.add_paragraph(line)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
