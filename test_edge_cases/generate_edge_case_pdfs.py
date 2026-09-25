"""Generate 200 isolated PDF fixtures for the GeM extractor edge-case suite."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import pymupdf


HERE = Path(__file__).resolve().parent
PDF_DIR = HERE / "pdfs"
MANIFEST = HERE / "case_manifest.json"


def base_case() -> dict:
    return {
        "contract_no": "GEMC-511687725752289",
        "generated_date": "15-Jan-2021",
        "organisation_name": "Indian Army",
        "buyer_email": "buyer@gov.in",
        "buyer_contact": "01123019405",
        "paying_email": "paying@gov.in",
        "seller_name": "Acme Medical Supplies Pvt Ltd",
        "seller_contact": "09760037477",
        "seller_email": "sales@acme.example.com",
        "seller_gstin": "09AKDPJ0153C1ZQ",
        "seller_address": "A-99, Saraswati Lok, Delhi Road, Meerut, UTTAR PRADESH-250002",
        "product_name": "Digital Patient Monitor",
        "brand": "Acme",
        "category": "Patient Monitor - Q1",
        "qty": "2",
        "unit_price": "12500",
        "total": "25000",
        "consignee_address": "District Hospital, Civil Lines, Meerut, UTTAR PRADESH-250001, India",
        "consignee_email": "store@gov.in",
        "consignee_contact": "01123019405",
        "label_case": "normal",
        "layout": "inline",
        "pages": 1,
        "products": None,
        "omit_sections": set(),
        "blank": False,
        "invalid_bytes": None,
    }


def labels(c: dict) -> dict:
    if c["label_case"] == "upper":
        return {k: v.upper() for k, v in {
            "contract": "Contract No", "date": "Generated Date", "org": "Organisation Details",
            "buyer": "Buyer Details", "paying": "Paying Authority Details", "seller": "Seller Details",
            "product": "Product Details", "consignee": "Consignee Detail", "company": "Company Name",
            "contact": "Contact No", "email": "Email ID", "gstin": "GSTIN", "address": "Address",
            "name": "Product Name", "brand": "Brand", "category": "Category Name & Quadrant",
            "qty": "Ordered Quantity", "unit": "Unit Price", "total": "Total Order Value",
        }.items()}
    if c["label_case"] == "mixed":
        return {
            "contract": "contract NO", "date": "generated date", "org": "Organisation Details",
            "buyer": "Buyer Details", "paying": "Paying Authority", "seller": "Seller Details",
            "product": "Product Details", "consignee": "Consignee Detail", "company": "Company name",
            "contact": "Contact No.", "email": "Email", "gstin": "GSTIN", "address": "Address",
            "name": "Product Name", "brand": "Brand", "category": "Category Name",
            "qty": "Ordered Quantity", "unit": "Unit Price", "total": "Total Order Value",
        }
    return {
        "contract": "Contract No", "date": "Generated Date", "org": "Organisation Details",
        "buyer": "Buyer Details", "paying": "Paying Authority Details", "seller": "Seller Details",
        "product": "Product Details", "consignee": "Consignee Detail", "company": "Company Name",
        "contact": "Contact No", "email": "Email ID", "gstin": "GSTIN", "address": "Address",
        "name": "Product Name", "brand": "Brand", "category": "Category Name & Quadrant",
        "qty": "Ordered Quantity", "unit": "Unit Price", "total": "Total Order Value",
    }


def render_page(c: dict, product: dict | None = None, include_header: bool = True) -> str:
    l = labels(c)
    p = product or {
        "product_name": c["product_name"], "brand": c["brand"], "category": c["category"],
        "qty": c["qty"], "unit_price": c["unit_price"], "total": c["total"],
    }
    lines = []
    if include_header:
        if "header" not in c["omit_sections"]:
            lines += [
            f"{l['contract']}: {c['contract_no']}",
            f"{l['date']}: {c['generated_date']}",
            ]
            if "organisation" not in c["omit_sections"]:
                lines += [l["org"], f"Organisation Name: {c['organisation_name']}"]
            if "buyer" not in c["omit_sections"]:
                lines += [l["buyer"], f"{l['email']}: {c['buyer_email']}", f"{l['contact']}: {c['buyer_contact']}"]
            if "paying" not in c["omit_sections"]:
                lines += [l["paying"], f"{l['email']}: {c['paying_email']}"]
            if "seller" not in c["omit_sections"]:
                lines += [l["seller"], f"{l['company']}: {c['seller_name']}",
                          f"{l['contact']}: {c['seller_contact']}", f"{l['email']}: {c['seller_email']}",
                          f"{l['gstin']}: {c['seller_gstin']}", f"{l['address']}: {c['seller_address']}"]
    if "product" not in c["omit_sections"]:
        lines += [
            l["product"], f"{l['name']}: {p['product_name']}", f"{l['brand']}: {p['brand']}",
            f"{l['category']}: {p['category']}",
            str(p["qty"]), "pieces", str(p["unit_price"]), "NA", str(p["total"]),
        ]
    if "consignee" not in c["omit_sections"]:
        lines += [
            l["consignee"], f"{l['address']}: {c['consignee_address']}",
            f"{l['email']}: {c['consignee_email']}", f"{l['contact']}: {c['consignee_contact']}",
        ]
    if c["layout"] == "label_on_next_line":
        transformed = []
        for line in lines:
            if ": " in line and not line.startswith("http"):
                key, value = line.split(": ", 1)
                transformed.extend([key, value])
            else:
                transformed.append(line)
        lines = transformed
    elif c["layout"] == "extra_whitespace":
        lines = [re.sub(r" ", "  ", line) if line else line for line in lines]
    elif c["layout"] == "pipes":
        lines = [line.replace(": ", " | ") if ": " in line else line for line in lines]
    return "\n".join(lines)


def make_case(number: int) -> tuple[dict, list[str]]:
    """Return a case definition and its page text. Definitions are deterministic."""
    c = base_case()
    group = (number - 1) // 10
    variant = (number - 1) % 10
    description = ""
    expected = {"status": "PASS", "record_count": 1}

    if group == 0:  # baseline layout variants
        description = [
            "standard inline labels", "upper-case labels", "mixed-case labels", "labels on next lines",
            "double spaces", "pipe separators", "GEM contract prefix", "one-page extra whitespace",
            "seller address with repeated punctuation", "consignee address with PIN and India",
        ][variant]
        if variant == 1: c["label_case"] = "upper"
        if variant == 2: c["label_case"] = "mixed"
        if variant == 3: c["layout"] = "label_on_next_line"
        if variant == 4: c["layout"] = "extra_whitespace"
        if variant == 5: c["layout"] = "pipes"
        if variant == 6: c["contract_no"] = "GEM-511687725752289"
        if variant == 7: c["pages"] = 2
        if variant == 8: c["seller_address"] = "A-99,, Saraswati Lok;;; Delhi Road,, Meerut"
        if variant == 9: c["consignee_address"] = "District Hospital, Civil Lines, Meerut, UTTAR PRADESH-250001, India"
    elif group == 1:  # page and section boundaries
        description = [
            "header and product split across two pages", "seller fields split across pages", "consignee split across pages",
            "three-page document", "product section starts on page two", "blank middle page", "repeated section heading",
            "long seller address", "long product name", "trailing blank page",
        ][variant]
        c["pages"] = 2 if variant != 3 else 3
        if variant == 0: c["layout"] = "label_on_next_line"
        if variant == 1: c["seller_address"] += ", Warehouse Block B, Industrial Estate"
        if variant == 2: c["consignee_address"] += ", Store Room 4, Main Campus"
        if variant == 4:
            c["layout"] = "label_on_next_line"
        if variant == 5: c["pages"] = 3
        if variant == 6: c["seller_name"] = "Acme Medical Supplies Pvt Ltd"
        if variant == 7: c["seller_address"] = "Plot 1, " + ", ".join(f"Address block {i}" for i in range(1, 12))
        if variant == 8: c["product_name"] = "Digital Patient Monitor " + ("with advanced clinical display " * 4)
    elif group == 2:  # contract number
        description = [
            "missing contract number", "too-short GEMC number", "alphabetic contract suffix", "contract number with spaces",
            "lower-case contract prefix", "contract label without value", "contract number only in filename",
            "two contract numbers", "contract number surrounded by punctuation", "non-GEM contract identifier",
        ][variant]
        expected = {"status": "REVIEW", "record_count": 1}
        if variant == 0: c["contract_no"] = ""
        if variant == 1: c["contract_no"] = "GEMC-123"
        if variant == 2: c["contract_no"] = "GEMC-51168772575228A"
        if variant == 3: c["contract_no"] = "GEMC 511687725752289"
        if variant == 4: c["contract_no"] = "gemc-511687725752289"
        if variant == 5: c["contract_no"] = ""
        if variant == 6: c["contract_no"] = ""
        if variant == 7: c["contract_no"] = "GEMC-511687725752289 / GEMC-511687725752290"
        if variant == 8: c["contract_no"] = "(GEMC-511687725752289)"
        if variant == 9: c["contract_no"] = "ORDER-511687725752289"
        if variant == 0:
            expected["field"] = {"contract_no": "NA"}
    elif group == 3:  # dates
        description = [
            "missing date", "invalid month", "day zero", "impossible day", "two-digit year", "slash date",
            "date only in delivery text", "date with timestamp", "generated date on next line", "date with extra punctuation",
        ][variant]
        if variant == 0: c["generated_date"] = ""
        if variant == 1: c["generated_date"] = "15-XXX-2021"
        if variant == 2: c["generated_date"] = "00-Jan-2021"
        if variant == 3: c["generated_date"] = "32-Jan-2021"
        if variant == 4: c["generated_date"] = "15-Jan-21"
        if variant == 5: c["generated_date"] = "15/01/2021"
        if variant == 6: c["generated_date"] = ""
        if variant == 7: c["generated_date"] = "15-Jan-2021 10:30"
        if variant == 8: c["layout"] = "label_on_next_line"
        if variant == 9: c["generated_date"] = "15-Jan-2021..."
        if variant in {0, 1, 2, 3, 6, 7, 9}:
            expected = {"status": "REVIEW", "record_count": 1, "field": {"generated_date": "NA"}}
    elif group == 4:  # seller name/contact
        description = [
            "missing seller name", "one-character seller name", "seller name with line wrap", "missing seller contact",
            "short seller contact", "landline seller contact", "seller contact with country code", "seller contact with extension",
            "seller name contains colon", "seller contact contains nearby label",
        ][variant]
        if variant == 0: c["seller_name"] = ""
        if variant == 1: c["seller_name"] = "A"
        if variant == 2: c["seller_name"] = "Acme Medical Supplies Pvt Ltd"
        if variant == 3: c["seller_contact"] = ""
        if variant == 4: c["seller_contact"] = "123"
        if variant == 5: c["seller_contact"] = "011-23019405"
        if variant == 6: c["seller_contact"] = "+91 9760037477"
        if variant == 7: c["seller_contact"] = "09760037477 ext 4"
        if variant == 8: c["seller_name"] = "Acme: Medical Supplies"
        if variant == 9: c["seller_contact"] = "09760037477 Contact No"
        if variant in {0, 1, 3, 4}:
            expected = {"status": "REVIEW", "record_count": 1}
    elif group == 5:  # seller email
        description = [
            "missing seller email", "invalid seller email", "email without domain", "email without TLD", "email with uppercase",
            "plus-address seller email", "seller email with surrounding text", "two seller emails", "seller email with underscore",
            "seller email is government address",
        ][variant]
        if variant == 0: c["seller_email"] = ""
        if variant == 1: c["seller_email"] = "sales@@acme.example.com"
        if variant == 2: c["seller_email"] = "sales@acme"
        if variant == 3: c["seller_email"] = "sales@acme.c"
        if variant == 4: c["seller_email"] = "SALES@ACME.EXAMPLE.COM"
        if variant == 5: c["seller_email"] = "sales+gem@acme.example.com"
        if variant == 6: c["seller_email"] = "Seller: sales@acme.example.com"
        if variant == 7: c["seller_email"] = "first@acme.example.com second@acme.example.com"
        if variant == 8: c["seller_email"] = "sales_team@acme.example.com"
        if variant == 9: c["seller_email"] = "seller@gov.in"
        if variant in {0, 1, 2, 3}:
            expected = {"status": "REVIEW", "record_count": 1}
    elif group == 6:  # GSTIN
        description = [
            "missing GSTIN", "too-short GSTIN", "GSTIN with invalid state code", "GSTIN with invalid checksum shape",
            "lower-case GSTIN", "GSTIN with spaces", "GSTIN embedded in sentence", "buyer GSTIN before seller GSTIN",
            "seller GSTIN with punctuation", "seller GSTIN using NA marker",
        ][variant]
        if variant == 0: c["seller_gstin"] = ""
        if variant == 1: c["seller_gstin"] = "09AKDPJ0153C1Z"
        if variant == 2: c["seller_gstin"] = "00AKDPJ0153C1ZQ"
        if variant == 3: c["seller_gstin"] = "09AKDPJ0153C1ZZ"
        if variant == 4: c["seller_gstin"] = "09akdpj0153c1zq"
        if variant == 5: c["seller_gstin"] = "09 AKDPJ 0153 C1ZQ"
        if variant == 6: c["seller_gstin"] = "GSTIN is 09AKDPJ0153C1ZQ"
        if variant == 7: c["seller_gstin"] = "09AAAAA0000A1Z5"
        if variant == 8: c["seller_gstin"] = "09AKDPJ0153C1ZQ."
        if variant == 9: c["seller_gstin"] = "NA"
        if variant in {0, 1, 2, 3, 5, 9}:
            expected = {"status": "REVIEW", "record_count": 1}
    elif group == 7:  # consignee address
        description = [
            "missing consignee address", "short consignee address", "address with delivery dates", "address with leaked product",
            "repeated address segment", "address with Hindi marker", "address ending in comma", "address containing PIN only",
            "address longer than sanitizer patterns", "address with state marker",
        ][variant]
        if variant == 0: c["consignee_address"] = ""
        if variant == 1: c["consignee_address"] = "A"
        if variant == 2: c["consignee_address"] += " 23-Dec-2025 07-Jan-2026"
        if variant == 3: c["consignee_address"] += " Acme Digital Patient Monitor - Max user 100 kg"
        if variant == 4: c["consignee_address"] = "Block A, Block A, Block A, Meerut, India"
        if variant == 5: c["consignee_address"] = "Pata: District Hospital, Meerut, India"
        if variant == 6: c["consignee_address"] += ","
        if variant == 7: c["consignee_address"] = "110001"
        if variant == 8: c["consignee_address"] = ", ".join(f"Building {i}" for i in range(1, 30))
        if variant == 9: c["consignee_address"] = "District Hospital, STATE - UTTAR PRADESH-250001, India"
        if variant in {0, 1, 7}:
            expected = {"status": "REVIEW", "record_count": 1}
    elif group == 8:  # consignee email/contact
        description = [
            "missing consignee email", "invalid consignee email", "missing consignee contact", "short consignee contact",
            "landline consignee contact", "consignee contact with country code", "two consignee emails", "email label on next line",
            "consignee contact with punctuation", "consignee uses NIC email",
        ][variant]
        if variant == 0: c["consignee_email"] = ""
        if variant == 1: c["consignee_email"] = "store@"
        if variant == 2: c["consignee_contact"] = ""
        if variant == 3: c["consignee_contact"] = "12"
        if variant == 4: c["consignee_contact"] = "011-23019405"
        if variant == 5: c["consignee_contact"] = "+91 9760037477"
        if variant == 6: c["consignee_email"] = "first@gov.in second@gov.in"
        if variant == 7: c["layout"] = "label_on_next_line"
        if variant == 8: c["consignee_contact"] = "01123019405;"
        if variant == 9: c["consignee_email"] = "store@nic.in"
        if variant in {0, 1, 2, 3}:
            expected = {"status": "REVIEW", "record_count": 1}
    elif group == 9:  # quantity
        description = [
            "zero quantity", "negative quantity", "missing quantity", "decimal quantity", "quantity with comma",
            "quantity word only", "very large quantity", "quantity with unit in same line", "quantity as NA", "quantity as zero-padded",
        ][variant]
        if variant == 0: c["qty"] = "0"
        if variant == 1: c["qty"] = "-1"
        if variant == 2: c["qty"] = ""
        if variant == 3: c["qty"] = "2.5"
        if variant == 4: c["qty"] = "1,000"
        if variant == 5: c["qty"] = "two"
        if variant == 6: c["qty"] = "999999999"
        if variant == 7: c["qty"] = "2 pieces"
        if variant == 8: c["qty"] = "NA"
        if variant == 9: c["qty"] = "002"
        if variant in {0, 1, 2, 3, 5, 7, 8}:
            expected = {"status": "REVIEW", "record_count": 1}
    elif group == 10:  # price and math
        description = [
            "zero unit price", "negative unit price", "missing unit price", "decimal unit price", "price with comma",
            "missing total", "zero total", "negative total", "math mismatch", "rounding tolerance",
        ][variant]
        if variant == 0: c["unit_price"] = "0"
        if variant == 1: c["unit_price"] = "-12500"
        if variant == 2: c["unit_price"] = ""
        if variant == 3: c["unit_price"] = "12500.50"; c["total"] = "25001"
        if variant == 4: c["unit_price"] = "12,500"
        if variant == 5: c["total"] = ""
        if variant == 6: c["total"] = "0"
        if variant == 7: c["total"] = "-1"
        if variant == 8: c["total"] = "99999"
        if variant == 9: c["total"] = "25002"
        if variant in {0, 1, 2, 5, 6, 7, 8}:
            expected = {"status": "REVIEW", "record_count": 1}
    elif group == 11:  # product/name/category/brand
        description = [
            "missing product name", "brand marked unbranded", "brand includes dimensions", "brand too long", "missing category",
            "category includes model suffix", "product name with brand suffix", "product name with commas", "product name Hindi suffix",
            "empty product block",
        ][variant]
        if variant == 0: c["product_name"] = ""
        if variant == 1: c["brand"] = "Unbranded"
        if variant == 2: c["brand"] = "Acme 10 x 20 mm"
        if variant == 3: c["brand"] = "B" * 60
        if variant == 4: c["category"] = ""
        if variant == 5: c["category"] = "Patient Monitor - Q1 Model X HSN Code 9018"
        if variant == 6: c["product_name"] = "Digital Patient Monitor Brand: Acme"
        if variant == 7: c["product_name"] = "Monitor, digital, portable"
        if variant == 8: c["product_name"] = "Digital Patient Monitor परीक्षण"
        if variant == 9: c["product_name"] = ""
        if variant in {0, 9}:
            expected = {"status": "PASS", "record_count": 1, "field": {"product_name": "NA"}}
    elif group == 12:  # whitespace and unicode
        description = [
            "non-breaking spaces", "tabs between labels", "control characters", "leading separators", "trailing separators",
            "Devanagari in product", "Devanagari in address", "zero-width-like punctuation", "multiple blank lines", "UTF-8 punctuation",
        ][variant]
        if variant == 0: c["seller_name"] = "Acme\u00a0Medical\u00a0Supplies"
        if variant == 1: c["layout"] = "label_on_next_line"
        if variant == 2: c["seller_name"] = "Acme\x01 Medical Supplies"
        if variant == 3: c["seller_address"] = "--- A-99, Meerut"
        if variant == 4: c["seller_address"] = "A-99, Meerut ---"
        if variant == 5: c["product_name"] = "Digital Monitor परीक्षण"
        if variant == 6: c["consignee_address"] = "पता: District Hospital, Meerut, India"
        if variant == 7: c["product_name"] = "Digital\u200b Monitor"
        if variant == 8: c["layout"] = "extra_whitespace"
        if variant == 9: c["product_name"] = "Digital Monitor – portable"
    elif group == 13:  # bilingual / alternate labels
        description = [
            "Hindi section labels beside English", "Hindi address label", "Hindi product label", "Hindi email label", "Hindi contact label",
            "English then Hindi header", "Hindi then English header", "mixed bilingual spacing", "Devanagari organisation", "bilingual category",
        ][variant]
        # Keep English labels present so the fixture remains a valid PDF text-layer test;
        # the Hindi text exercises transliteration and noisy Unicode around known labels.
        c["organisation_name"] = "भारतीय सेना / Indian Army" if variant in {0, 8} else c["organisation_name"]
        c["product_name"] = "डिजिटल मॉनिटर / Digital Patient Monitor" if variant in {2, 9} else c["product_name"]
        c["consignee_address"] = "पता / Address: District Hospital, Meerut, India" if variant == 1 else c["consignee_address"]
        c["seller_email"] = "sales@acme.example.com" if variant == 3 else c["seller_email"]
        c["layout"] = "label_on_next_line" if variant in {5, 6, 7} else c["layout"]
    elif group == 14:  # multi-product
        description = [
            "two products", "three products", "same product twice", "different quantities", "different brands",
            "one incomplete product", "products across pages", "product numbers with two digits", "mixed product punctuation", "four products",
        ][variant]
        count = {0: 2, 1: 3, 2: 2, 3: 2, 4: 2, 5: 2, 6: 2, 7: 2, 8: 2, 9: 4}[variant]
        products = []
        for i in range(count):
            products.append({
                "product_name": f"Product {i + 1} Medical Device",
                "brand": "Acme" if variant != 4 or i == 0 else "Beta",
                "category": f"Medical Device - Q{i + 1}",
                "qty": str(i + 1), "unit_price": str(1000 * (i + 1)), "total": str(1000 * (i + 1) ** 2),
            })
        c["products"] = products
        expected = {"status": "PASS", "record_count": count}
        if variant == 5:
            products[1]["product_name"] = ""
            expected = {"status": "PASS", "record_count": 2}
        if variant == 6: c["pages"] = 2
        if variant == 7: products[1]["product_name"] = "Product 12 Medical Device"
        if variant == 8: products[0]["product_name"] = "Product, 1: Medical Device"
    elif group == 15:  # duplicated and ambiguous fields
        description = [
            "duplicate seller email", "duplicate seller GSTIN", "duplicate consignee email", "buyer email before seller email",
            "two addresses in seller section", "two date candidates", "two product rows with same name", "labels inside description",
            "section heading repeated", "field value contains label text",
        ][variant]
        if variant == 0: c["seller_email"] = "sales@acme.example.com sales2@acme.example.com"
        if variant == 1: c["seller_gstin"] = "09AKDPJ0153C1ZQ 09AKDPJ0153C1ZQ"
        if variant == 2: c["consignee_email"] = "store@gov.in backup@gov.in"
        if variant == 3: c["buyer_email"] = "buyer@gov.in seller-note@acme.example.com"
        if variant == 4: c["seller_address"] = "Address: A-99, Meerut Address: Warehouse 2, Meerut"
        if variant == 5: c["generated_date"] = "01-Jan-2020 15-Jan-2021"
        if variant == 6:
            c["products"] = [{"product_name": "Same Device", "brand": "Acme", "category": "Device - Q1", "qty": "1", "unit_price": "10", "total": "10"}, {"product_name": "Same Device", "brand": "Acme", "category": "Device - Q1", "qty": "2", "unit_price": "10", "total": "20"}]
            expected = {"status": "PASS", "record_count": 2}
        if variant == 7: c["product_name"] = "Product Description Brand: Acme Category Name: Device"
        if variant == 8: c["pages"] = 2
        if variant == 9: c["seller_name"] = "Seller Details Company Name Acme"
    elif group == 16:  # long and unusual content
        description = [
            "very long organisation name", "very long seller name", "very long email local part", "very long filename-safe data",
            "numeric-only product", "emoji in product", "quotes in address", "ampersands in company", "slashes in category", "non-ASCII currency text",
        ][variant]
        if variant == 0: c["organisation_name"] = "Organisation " + ("North Regional Procurement Division " * 5)
        if variant == 1: c["seller_name"] = "Acme " + ("Medical Supplies " * 10)
        if variant == 2: c["seller_email"] = "a" * 70 + "@acme.example.com"
        if variant == 3: c["product_name"] = "Device " + ("x " * 30)
        if variant == 4: c["product_name"] = "1234567890"
        if variant == 5: c["product_name"] = "Monitor 😀"
        if variant == 6: c["consignee_address"] = 'District Hospital, "Civil Lines", Meerut, India'
        if variant == 7: c["seller_name"] = "Acme & Sons (India) Pvt. Ltd."
        if variant == 8: c["category"] = "Medical/Diagnostic/Equipment - Q1"
        if variant == 9: c["unit_price"] = "₹12,500"; c["total"] = "₹25,000"
    elif group == 17:  # filename and fallback behavior
        description = [
            "contract recovered from filename", "filename with spaces", "filename with parentheses", "filename with Unicode",
            "filename with very long name", "filename contains wrong contract but body valid", "uppercase PDF extension equivalent",
            "duplicate-looking filename", "filename with path separators sanitized", "filename without contract and body missing contract",
        ][variant]
        if variant == 0: c["contract_no"] = ""
        if variant == 5: c["contract_no"] = "GEMC-511687725752289"
        if variant == 9: c["contract_no"] = ""
        if variant == 0:
            expected = {"status": "PASS", "record_count": 1, "field": {"contract_no": "GEMC-511687725752289"}}
            c["filename_override"] = "GEMC-511687725752289_case_171.pdf"
    elif group == 18:  # missing whole sections
        description = [
            "missing organisation section", "missing buyer section", "missing paying authority", "missing seller section",
            "missing product section", "missing consignee section", "empty product values", "only header fields", "only product fields", "blank PDF page",
        ][variant]
        expected = {"status": "REVIEW", "record_count": 1}
        omit = {
            0: "organisation", 1: "buyer", 2: "paying", 3: "seller", 4: "product", 5: "consignee",
        }.get(variant)
        if omit:
            c["omit_sections"].add(omit)
        if variant == 6:
            c["product_name"] = ""; c["brand"] = ""; c["category"] = ""; c["qty"] = ""; c["unit_price"] = ""; c["total"] = ""
        if variant == 7: c["seller_name"] = ""; c["seller_contact"] = ""; c["seller_email"] = ""; c["seller_gstin"] = ""
        if variant == 8: c["contract_no"] = ""; c["generated_date"] = ""
        if variant == 9: c["blank"] = True
    else:  # invalid PDF and boundary files
        description = [
            "empty PDF", "malformed PDF bytes", "truncated PDF bytes", "PDF with image-only page", "PDF with zero-width text",
            "PDF with a blank first page", "PDF with blank trailing page", "PDF with many blank pages", "PDF with form-feed text", "PDF with NUL-like content",
        ][variant]
        expected = {"status": "REVIEW", "record_count": 1}
        if variant == 0: c["blank"] = True
        if variant == 1: c["invalid_bytes"] = b"not a pdf"
        if variant == 2: c["invalid_bytes"] = b"%PDF-1.7\n%truncated"
        if variant in {3, 5, 6, 7}: c["blank"] = True
        if variant == 4: c["product_name"] = "\x00\x01\x02 Digital Monitor"
        if variant == 5: c["pages"] = 2
        if variant == 6: c["pages"] = 2
        if variant == 7: c["pages"] = 8
        if variant == 8: c["layout"] = "extra_whitespace"
        if variant == 9: c["seller_name"] = "Acme\x00 Supplies"
        if variant in {4, 8, 9}:
            expected = {"status": "PASS", "record_count": 1}

    pages = []
    if c.get("blank"):
        pages = [""] * c.get("pages", 1)
    elif c.get("invalid_bytes") is not None:
        pages = []
    elif c.get("products"):
        header = render_page(c, c["products"][0], include_header=True)
        product_tail = ""
        if "Consignee Detail" in header:
            header, product_tail = header.split("Consignee Detail", 1)
            product_tail = "Consignee Detail" + product_tail
        header = header.replace("Product Details\n", "Product Details\n1\n", 1)
        pages.append(header)
        for index, product in enumerate(c["products"][1:], start=2):
            product_page = render_page(c, product, include_header=False)
            product_page = product_page.split("Consignee Detail", 1)[0]
            product_page = product_page.replace("Product Details\n", "", 1)
            pages.append(f"{index}\n" + product_page)
        pages.append(product_tail)
    else:
        full = render_page(c)
        if c.get("pages", 1) <= 1:
            pages = [full]
        else:
            lines = full.splitlines()
            split = max(1, len(lines) // c["pages"])
            pages = ["\n".join(lines[i:i + split]) for i in range(0, len(lines), split)]
            while len(pages) < c["pages"]:
                pages.append("")
            if len(pages) > c["pages"]:
                pages = pages[:c["pages"] - 1] + ["\n".join(pages[c["pages"] - 1:])]

    case = {
        "id": f"case_{number:03d}",
        "filename": c.get("filename_override", f"case_{number:03d}.pdf"),
        "category": [
            "baseline", "layout", "contract", "date", "seller", "seller_email", "gstin", "address",
            "consignee", "quantity", "math", "product", "text_normalization", "bilingual", "multi_product",
            "ambiguity", "long_values", "filename_fallback", "missing_sections", "malformed_pdf",
        ][group],
        "description": description,
        "expected": expected,
        "source": c,
        "pages": pages,
    }
    return case, pages


def write_pdf(path: Path, pages: list[str], invalid_bytes: bytes | None = None) -> None:
    if invalid_bytes is not None:
        path.write_bytes(invalid_bytes)
        return
    doc = pymupdf.open()
    for page_text in pages:
        page = doc.new_page(width=612, height=792)
        if page_text:
            page.insert_text((36, 42), page_text, fontsize=8, lineheight=1.35)
    doc.save(path)
    doc.close()


def main() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    for old in PDF_DIR.glob("*.pdf"):
        old.unlink()

    manifest = []
    for number in range(1, 201):
        case, pages = make_case(number)
        invalid = case["source"].get("invalid_bytes")
        write_pdf(PDF_DIR / case["filename"], pages, invalid)
        case.pop("source", None)
        case.pop("pages", None)
        manifest.append(case)

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated {len(manifest)} fixtures in {PDF_DIR}")


if __name__ == "__main__":
    main()
