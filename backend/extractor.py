"""
extractor.py — GeM Contract High-Speed Non-LLM Parser & Validation Engine
=========================================================================
Extracts structured data from Government e-Marketplace (GeM) contract PDFs
using PyMuPDF for high-speed local text extraction and deterministic regex/tabular rules.

Features:
  1. Handles Pure English, Bilingual English|Hindi, and Hindi|English layouts.
  2. Multi-line continuous field scanning (e.g. multi-line Category Name & Quadrant, Product Name, Company Name, Address).
  3. Extracts all required contract fields with complete values without truncation.
  4. 4-Tier Automated Verification Matrix (Syntax, Math, Section Isolation, Consistency).
  5. Deterministic PASS / REVIEW status scoring with detailed error breakdown.
"""

import re
import os
# pyrefly: ignore [missing-import]
import pymupdf  # PyMuPDF
from typing import Dict, Any, List, Optional, Tuple
# pyrefly: ignore [missing-import]
from unidecode import unidecode


# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS & REGEX DEFINITIONS
# ──────────────────────────────────────────────────────────────────────────────

NA = "NA"
STATUS_PASS = "PASS"
STATUS_REVIEW = "REVIEW"

RE_DEVANAGARI = re.compile(r'[\u0900-\u097F]')
RE_GSTIN_VALID = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$', re.IGNORECASE)
RE_EMAIL_VALID = re.compile(r'^[\w.\-+]+@[\w.\-]+\.[a-zA-Z]{2,}$')


# ──────────────────────────────────────────────────────────────────────────────
# TEXT CLEANING & TRANSLITERATION
# ──────────────────────────────────────────────────────────────────────────────

def transliterate_hindi(text: str) -> str:
    """Convert Devanagari characters to clean English / Latin equivalents."""
    if not text or text == NA:
        return text
    # Strip unprintable / control characters first
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    if RE_DEVANAGARI.search(text):
        return unidecode(text)
    return text


def clean_text(text: Optional[str]) -> str:
    """Normalize whitespace, strip control chars, and clean extraneous punctuation."""
    if not text:
        return NA
    cleaned = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', str(text))
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    cleaned = re.sub(r'^[:|\-–\s]+|[:|\-–\s]+$', '', cleaned).strip()
    if not cleaned or cleaned.upper() in {"-", "--", "N/A", "NONE", "NULL", "NA"}:
        return NA
    return transliterate_hindi(cleaned)


def clean_phone(text: Optional[str]) -> str:
    """Normalize phone / contact numbers."""
    if not text or text == NA:
        return NA
    text_str = str(text).strip()
    m = re.search(r'(?:(?:\+91|0)?[1-9]\d{9}|0\d{2,4}[-\s]?\d{6,8})', text_str)
    if m:
        digits = re.sub(r'[^\d]', '', m.group(0))
        return digits[-10:] if len(digits) == 10 or digits.startswith(('7', '8', '9')) else digits
    digits = re.sub(r'[^\d]', '', text_str)
    if len(digits) >= 10:
        return digits[-10:] if len(digits) == 10 else digits
    if digits and len(digits) >= 7:
        return digits
    return NA


def clean_email(text: Optional[str]) -> str:
    """Extract and validate clean email address."""
    if not text or text == NA:
        return NA
    match = re.search(r'[\w.\-+]+@[\w.\-]+\.[a-zA-Z]{2,}', str(text))
    if match:
        return match.group(0).lower().strip()
    return NA


def clean_gstin(text: Optional[str]) -> str:
    """Extract and clean GSTIN."""
    if not text or text == NA:
        return NA
    match = re.search(r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b', str(text), re.IGNORECASE)
    if match:
        return match.group(0).upper().strip()
    cleaned = clean_text(text)
    if cleaned != NA and RE_GSTIN_VALID.match(cleaned):
        return cleaned.upper()
    return NA


def clean_address(text: Optional[str]) -> str:
    """Normalize whitespace, strip address/pata/ptaa label prefixes, colons, and clean address text."""
    if not text or text == NA:
        return NA
    val = str(text).strip()
    val = transliterate_hindi(val)
    prefix_regex = re.compile(
        r'^(?:address|pataa|ptaa|pata|पता)\b\s*(?:[/|\\–\-])?\s*(?:address|pataa|ptaa|pata|पता)?\s*[:.\-–=;]*\s*',
        re.IGNORECASE
    )
    for _ in range(5):
        prev = val
        val = prefix_regex.sub('', val).strip()
        val = re.sub(r'^(?:address|pataa|ptaa|pata|पता)\b[:.\s\-–;=]*', '', val, flags=re.IGNORECASE).strip()
        val = re.sub(r'^[:|\-–;,\s]+', '', val).strip()
        if val == prev:
            break

    val = re.sub(r'\s+', ' ', val).strip()
    val = re.sub(r'^[:|\-–;,\s]+|[:|\-–;\s]+$', '', val).strip()

    if not val or val.upper() in {"-", "--", "N/A", "NONE", "NULL", "NA"}:
        return NA
    return val


def extract_full_address(section: str) -> str:
    """
    Extracts complete multi-line address until 'India', pin-code, or next structural section.
    """
    if not section:
        return NA

    # Pattern 1: Address up to ', India' or ', Bharat' or 6-digit PIN with India
    m_india = re.search(
        r'(?:Address|पता)\s*[:.\s]*\n?\s*([\s\S]+?,\s*(?:India|भारत|\d{6},\s*India))',
        section, re.IGNORECASE
    )
    if m_india:
        addr = clean_address(m_india.group(1))
        if 5 <= len(addr) <= 300:
            return addr

    # Pattern 2: Address up to State-PIN: e.g. UTTAR PRADESH-250002, -
    m_pin = re.search(
        r'(?:Address|पता)\s*[:.\s]*\n?\s*([\s\S]+?,\s*[A-Z\s]+-\d{6}(?:,\s*[-–\w]+)?)',
        section, re.IGNORECASE
    )
    if m_pin:
        addr = clean_address(m_pin.group(1))
        if 5 <= len(addr) <= 300:
            return addr

    # Pattern 3: Multiline address stopping before next known section/table header
    m_stop = re.search(
        r'(?:Address|पता)\s*[:.\s]*\n?\s*([^\n\r]+(?:\n\s*[^\n\r]+){1,5})',
        section, re.IGNORECASE
    )
    if m_stop:
        lines = m_stop.group(1).split('\n')
        addr_lines = []
        for l in lines:
            l_str = l.strip()
            if not l_str:
                continue
            if any(k in l_str.lower() for k in [
                'consignee', 'product', 'item', 'brand', 'msme', 'gstin',
                'lot no', 'quantity', 'delivery', 'specification', 'paying authority'
            ]):
                break
            addr_lines.append(l_str)
        if addr_lines:
            addr = clean_address(' '.join(addr_lines))
            if 5 <= len(addr) <= 300:
                return addr

    return NA


def to_number(val: Any) -> Any:
    """Convert string to integer or float safely."""
    if val is None or val == NA:
        return NA
    if isinstance(val, (int, float)):
        return val
    val_str = str(val).replace(',', '').replace('INR', '').replace('₹', '').replace('Rs.', '').strip()
    try:
        if '.' in val_str:
            f = float(val_str)
            return int(f) if f.is_integer() else f
        return int(val_str)
    except (ValueError, TypeError):
        return NA


# ──────────────────────────────────────────────────────────────────────────────
# SECTION EXTRACTION UTILITIES (Bilingual Support)
# ──────────────────────────────────────────────────────────────────────────────

def extract_section(text: str, start_keywords: List[str], end_keywords: List[str]) -> str:
    """Extracts text between start_keyword and earliest end_keyword."""
    start_pos = -1
    for kw in start_keywords:
        pat = re.compile(re.escape(kw), re.IGNORECASE)
        m = pat.search(text)
        if m and (start_pos == -1 or m.start() < start_pos):
            start_pos = m.end()

    if start_pos == -1:
        return ""

    end_pos = len(text)
    for kw in end_keywords:
        pat = re.compile(re.escape(kw), re.IGNORECASE)
        m = pat.search(text, start_pos)
        if m and m.start() < end_pos:
            end_pos = m.start()

    return text[start_pos:end_pos].strip()


def match_multiline_kv(label_regex: str, text: str, max_lines: int = 5) -> str:
    """
    Extracts multi-line field value robustly handling single-line and multi-line keys,
    scanning continuous lines until the next field label, table row, or section boundary.
    """
    pat = re.compile(
        rf'(?:{label_regex})(?:[^\n\r:]*?)[:.]\s*([^\n\r]*)',
        re.IGNORECASE
    )
    m = pat.search(text)
    if not m:
        pat2 = re.compile(
            rf'(?:{label_regex})\s*\n\s*([^\n\r]*)',
            re.IGNORECASE
        )
        m = pat2.search(text)
        if not m:
            return NA

    first_line = m.group(1).strip()
    start_idx = m.end()
    remaining = text[start_idx:].lstrip('\r\n')
    sub_lines = remaining.split('\n')

    val_lines = []
    if first_line:
        val_lines.append(first_line)

    stop_kws = [
        'brand type', 'brand', 'model', 'hsn code', 'hsn', 'selling as', 'catalogue status',
        'category name', 'category', 'total order value', 'total contract value',
        'ordered quantity', 'unit price', 'item description', 'lot no',
        'delivery start', 'delivery to', 'delivery instructions',
        'consignee detail', 'consignee', 'product specification',
        'terms and conditions', 'epbg detail', 'financial approval',
        'paying authority', 'seller details', 'buyer details', 'organisation details',
        'email id', 'contact no', 'gstin'
    ]

    for line in sub_lines[:max_lines]:
        l_str = line.strip()
        if not l_str:
            if val_lines:
                break
            continue

        l_lower = l_str.lower()
        if any(kw in l_lower for kw in stop_kws):
            break

        if re.search(r'[:|]\s*(?:Brand|Model|HSN|Category|Selling|Product|Catalogue|Lot|Quantity|Price|Unit|Email|Contact|GSTIN|Address)\b', l_str, re.IGNORECASE):
            break

        if re.match(r'^(?:pieces|Nos\.?|units?|box|meters?|set|each|packets?|Test|\d+)$', l_str, re.IGNORECASE):
            break
        if re.match(r'^\d+\s+(?:pieces|Nos|units|box|meters|set|each|packets|Test)\b', l_str, re.IGNORECASE):
            break

        val_lines.append(l_str)

    if val_lines:
        res = clean_text(' '.join(val_lines))
        if res != NA and len(res) >= 1 and not res.lower().startswith(('details', 'description', 'specification')):
            return res

    return NA


# ──────────────────────────────────────────────────────────────────────────────
# CORE SECTION PARSERS
# ──────────────────────────────────────────────────────────────────────────────

RE_DATE_STRICT = re.compile(
    r'^\d{1,2}[-\/](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{1,2})[-\/]\d{2,4}$',
    re.IGNORECASE
)


def extract_clean_date(raw_text: str) -> str:
    """Extract and strictly validate contract generated date."""
    # 1. Inline match: Generated Date : 18-Mar-2024
    m_inline = re.search(
        r'(?:Generated\s*Date|Contract\s*Date|Date\s*of\s*Contract|अनुबंध\s*तिथि|अनुबंध\s*[\%!]?त[\%!]?थ)\s*[:.\s]*\s*(\d{1,2}[-\/]\w{3}[-\/]\d{2,4}|\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4})',
        raw_text, re.IGNORECASE
    )
    if m_inline and RE_DATE_STRICT.match(m_inline.group(1).strip()):
        return m_inline.group(1).strip()

    # 2. Next line match: Generated Date:\n 18-Mar-2024
    m_next = re.search(
        r'(?:Generated\s*Date|Contract\s*Date|Date\s*of\s*Contract|अनुबंध\s*तिथि|अनुबंध\s*[\%!]?त[\%!]?थ)\s*[:.\s]*\n\s*(\d{1,2}[-\/]\w{3}[-\/]\d{2,4}|\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4})',
        raw_text, re.IGNORECASE
    )
    if m_next and RE_DATE_STRICT.match(m_next.group(1).strip()):
        return m_next.group(1).strip()

    # 3. Previous line match: 15-Jan-2021\n Generated Date:
    m_prev = re.search(
        r'(\d{1,2}[-\/]\w{3}[-\/]\d{2,4}|\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4})\s*\n\s*(?:Generated\s*Date|अनुबंध\s*तिथि)',
        raw_text, re.IGNORECASE
    )
    if m_prev and RE_DATE_STRICT.match(m_prev.group(1).strip()):
        return m_prev.group(1).strip()

    # 4. Fallback search for Month-name date format
    all_dates = re.findall(
        r'\b(\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{4})\b',
        raw_text, re.IGNORECASE
    )
    if all_dates:
        return all_dates[0]

    # 5. Fallback search for DD/MM/YYYY date format
    all_dates_slash = re.findall(r'\b(\d{1,2}/\d{1,2}/\d{4})\b', raw_text)
    if all_dates_slash:
        return all_dates_slash[0]

    return NA


def parse_header(raw_text: str, filename: str = "") -> Tuple[str, str]:
    """Extract Contract No and Generated Date."""
    contract_no = NA

    gemc_m = re.search(r'\b(GEMC-[0-9]{12,18})\b', raw_text)
    if gemc_m:
        contract_no = gemc_m.group(1)
    else:
        contract_no = match_multiline_kv(r'(?:Contract\s*No|अनुबंध\s*क्रमांक|अनुबंध\s*मांक)', raw_text, max_lines=1)
        if contract_no == NA and filename:
            m_fn = re.search(r'\b(GEMC-[0-9]{12,18})\b', filename)
            if m_fn:
                contract_no = m_fn.group(1)

    gen_date = extract_clean_date(raw_text)

    return contract_no, gen_date


def parse_buyer_section(raw_text: str) -> Dict[str, str]:
    """Parse Buyer Details section."""
    section = extract_section(
        raw_text,
        ["Buyer Details", "खरीदार विवरण", "Buying Organisation"],
        ["Financial Approval", "वित्तीय स्वीकृति", "Paying Authority", "भुगतान प्राधिकरण", "Seller Details", "विक्रेता विवरण"]
    )
    if not section:
        section = raw_text

    email = clean_email(match_multiline_kv(r'(?:Email\s*(?:ID)?|ईमेल\s*आईडी)', section, max_lines=1))
    contact = clean_phone(match_multiline_kv(r'(?:Contact\s*(?:No\.?)?|संपर्क\s*नंबर|संपक[EHLG]\s*नंबर)', section, max_lines=1))
    gstin = clean_gstin(match_multiline_kv(r'(?:GSTIN|जीएसटीआईएन|जीएसट[cai\]\^]आईएन)', section, max_lines=1))

    return {
        "email": email,
        "contact_no": contact,
        "gstin": gstin
    }


def parse_paying_authority_section(raw_text: str) -> Dict[str, str]:
    """Parse Paying Authority Details section."""
    section = extract_section(
        raw_text,
        ["Paying Authority Details", "भुगतान प्राधिकरण विवरण", "Paying Authority"],
        ["Seller Details", "विक्रेता विवरण", "Product Details", "उत्पाद विवरण", "Consignee Detail", "परेषिती विवरण", "Total Order Value"]
    )
    if not section:
        return {"email": NA, "role": NA}

    email = clean_email(match_multiline_kv(r'(?:Email\s*(?:ID)?|ईमेल\s*आईडी)', section, max_lines=1))
    role = match_multiline_kv(r'(?:Role|पद|Designation)', section, max_lines=2)

    return {
        "email": email,
        "role": role
    }


def parse_seller_section(raw_text: str) -> Dict[str, str]:
    """Parse Seller Details section."""
    section = extract_section(
        raw_text,
        ["Seller Details", "विक्रेता विवरण", "%व ेता %ववरण", "$व ेता $ववरण", "!व ेता !ववरण", "Authorized Seller"],
        ["Product Details", "उत्पाद विवरण", "Delivery Instructions", "वितरण निर्देश", "Consignee Detail", "परेषिती विवरण", "Total Order Value", "Paying Authority Details"]
    )
    if not section:
        section = raw_text

    company_name = match_multiline_kv(r'(?:Company\s*Name|कंपनी\s*का\s*नाम)', section, max_lines=3)
    contact_no = clean_phone(match_multiline_kv(r'(?:Contact\s*(?:No\.?)?|संपर्क\s*नंबर|संपक[EHLG]\s*नंबर)', section, max_lines=1))
    if contact_no == NA:
        m_phone = re.search(r'(?:0[1-9]\d{9,10}|[6-9]\d{9})', section)
        if m_phone:
            contact_no = clean_phone(m_phone.group(0))

    email = clean_email(match_multiline_kv(r'(?:Email\s*(?:ID)?|ईमेल\s*आईडी)', section, max_lines=1))
    if email == NA:
        emails = re.findall(r'[\w.\-+]+@[\w.\-]+\.[a-zA-Z]{2,}', section)
        for e in emails:
            if not e.endswith('@gov.in') and not e.endswith('@nic.in'):
                email = clean_email(e)
                break
        if email == NA and emails:
            email = clean_email(emails[0])

    gstin = clean_gstin(match_multiline_kv(r'(?:GSTIN|जीएसटीआईएन|जीएसट[cai\]\^]आईएन)', section, max_lines=1))
    if gstin == NA:
        gstins = re.findall(r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b', section)
        if gstins:
            gstin = gstins[0]
        else:
            all_gstins = re.findall(r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b', raw_text)
            if all_gstins:
                gstin = all_gstins[0]

    address = extract_full_address(section)

    return {
        "company_name": company_name,
        "contact_no": contact_no,
        "email": email,
        "gstin": gstin,
        "address": address
    }


def parse_product_details(raw_text: str, doc: Optional[Any] = None) -> Dict[str, Any]:
    """Parse Product line item, complete multi-line category name & quadrant, brand, quantity, unit price, and total order value."""
    section = extract_section(
        raw_text,
        ["Product Details", "उत्पाद विवरण", "उxपाद", "उwपाद", "उtपाद", "उpपाद", "उyपाद", "उ|पाद", "उzपाद", "Item Description"],
        ["Consignee Detail", "परेषिती", "परे%षती", "परे\"षती", "परे षती", "Product Specification", "Terms and Conditions", "ePBG Detail"]
    )
    if not section:
        section = raw_text

    # 1. Multi-line Product Name
    product_name = match_multiline_kv(r'(?:Product\s*Name|उत्पाद\s*का\s*नाम|उ[xwtpyz|~o]पाद\s*का\s*नाम)', section, max_lines=4)

    # 2. Multi-line Brand (Strict: only if listed after Brand label)
    brand = match_multiline_kv(r'(?:Brand|ब्रांड|[‚€†\x7f\x81\x83]ांड)', section, max_lines=2)
    if brand != NA:
        b_clean = brand.strip().lower()
        if b_clean in {"na", "none", "-", "unbranded", "not specified", "not specified by seller", "n/a"}:
            brand = NA
        elif brand.startswith("NA "):
            brand = NA

    # 3. Multi-line Category & Quadrant
    cat_label_regex = (
        r'(?:Category\s*Name\s*(?:&|and)\s*Quadrant|Category\s*Name|'
        r'[\u0900-\u097F\w\s†‡ˆ‰vro…\x86\x88|]*?[ेo\u0947][\u0923\u0966-\u097F\w]*?\s*का\s*नाम(?:\s*और\s*चतुथा[\u0900-\u097F\wˆ‡‰Œ\s\x87\x89]*श)?)'
    )
    category_quadrant = match_multiline_kv(cat_label_regex, section, max_lines=4)

    # 4. Check PyMuPDF table structure if doc is provided
    table_data = {}
    if doc:
        try:
            for page in doc:
                tabs = page.find_tables()
                for tab in tabs.tables:
                    extracted = tab.extract()
                    for r_idx, row in enumerate(extracted):
                        row_clean = [c.strip() for c in row if c and c.strip()]
                        if any('item description' in c.lower() for c in row_clean) and any('category' in c.lower() for c in row_clean):
                            col_map = {}
                            for idx, cell in enumerate(row):
                                if cell:
                                    cl = cell.lower().replace('\n', ' ')
                                    if 'item description' in cl:
                                        col_map['item_description'] = idx
                                    elif 'category' in cl:
                                        col_map['category'] = idx
                                    elif 'model' in cl:
                                        col_map['model'] = idx
                                    elif 'ordered' in cl or 'quantity' in cl:
                                        col_map['qty'] = idx
                                    elif 'unit' in cl and 'price' not in cl:
                                        col_map['unit'] = idx
                                    elif 'price' in cl or 'duties' in cl:
                                        col_map['price'] = idx

                            for data_row in extracted[r_idx+1:]:
                                if data_row and any(data_row):
                                    first_val = next((c for c in data_row if c), '')
                                    if first_val.strip() in {'1', '01'} or (col_map.get('qty') and data_row[col_map['qty']]):
                                        for k, c_idx in col_map.items():
                                            if c_idx < len(data_row) and data_row[c_idx]:
                                                cell_txt = ' '.join(str(data_row[c_idx]).split())
                                                table_data[k] = clean_text(cell_txt)
                                        break
                            if table_data:
                                break
                    if table_data:
                        break
                if table_data:
                    break
        except Exception:
            pass

    if table_data:
        if (category_quadrant == NA or category_quadrant.lower() in {"model", "hsn code", "ordered quantity"}) and table_data.get('category'):
            category_quadrant = table_data['category']
        if product_name == NA and table_data.get('item_description'):
            product_name = table_data['item_description']

    # 5. Table column layout check (older GeM contracts where Category Name / Model / HSN are in separate column lines under Selling As)
    if category_quadrant == NA or category_quadrant.lower() in {"model", "hsn code", "ordered quantity"}:
        m_col = re.search(
            r'Selling\s*As\s*:[^\n]*\n([\s\S]+?)(?=\n\s*(?:HSN\s*not\s*specified|\b\d+\s*\n\s*(?:pieces|Nos|units|Test|box)|\n\s*Total\s*Order\s*Value))',
            section, re.IGNORECASE
        )
        if m_col:
            block = m_col.group(1).strip()
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            cat_lines = []
            for l in lines:
                if re.search(r'^(?:HSN|Model|pieces|Test|\d+$)', l, re.IGNORECASE):
                    break
                cat_lines.append(l)
            if cat_lines:
                joined = ' '.join(cat_lines)
                m_q = re.search(r'(.*?\(Q[1-4]\))', joined, re.IGNORECASE)
                if m_q:
                    category_quadrant = clean_text(m_q.group(1))
                else:
                    cat_only = []
                    for cl in cat_lines:
                        if re.search(r'^(?:IMI-|ESAW|truenat|CMS\d+|KLEAN|Pedestal|CHOKSI|Masppo)', cl, re.IGNORECASE):
                            break
                        cat_only.append(cl)
                    if cat_only:
                        category_quadrant = clean_text(' '.join(cat_only))
                    else:
                        category_quadrant = clean_text(joined)

    # 6. Fallback from text stream if table was not parsed
    if product_name == NA or category_quadrant == NA or category_quadrant.lower() in {"model", "hsn code"}:
        m_tbl = re.search(
            r'\n\s*1\s*\n\s*([^\n]+(?:\n[^\n]+){1,10}?)\n\s*(\d+)\s*\n\s*(pieces|Nos|units|Test|box|meters|set|each|packets)\s*\n\s*(?:[-–\d\w,.]+\s*\n\s*)?([\d,]+\.?\d*)',
            section, re.IGNORECASE
        )
        if m_tbl:
            tbl_lines = [l.strip() for l in m_tbl.group(1).split('\n') if l.strip()]
            hsn_idx = -1
            for i, l in enumerate(tbl_lines):
                if re.search(r'HSN\b', l, re.IGNORECASE):
                    hsn_idx = i
                    break

            if hsn_idx != -1:
                content_lines = tbl_lines[:hsn_idx]
            else:
                content_lines = tbl_lines

            if len(content_lines) >= 4:
                if product_name == NA:
                    product_name = clean_text(' '.join(content_lines[:2]))
                if category_quadrant == NA or category_quadrant.lower() in {"model", "hsn code"}:
                    category_quadrant = clean_text(' '.join(content_lines[2:4]))
            elif len(content_lines) >= 2:
                if product_name == NA:
                    product_name = clean_text(content_lines[0])
                if category_quadrant == NA or category_quadrant.lower() in {"model", "hsn code"}:
                    category_quadrant = clean_text(content_lines[1])

    # 7. Fallback to Product Specification General Item table or heading
    if category_quadrant == NA or category_quadrant.lower() in {"model", "hsn code"}:
        m_spec = re.search(r'(?:General\s+Item|Item)\s*\n\s*([^\n]+(?:\n[^\n]+){1,2})', raw_text, re.IGNORECASE)
        if m_spec:
            spec_text = m_spec.group(1).strip()
            lines = [l.strip() for l in spec_text.split('\n') if l.strip()]
            clean_spec = []
            for l in lines:
                if any(k in l.lower() for k in ['physical', 'characteristics', 'warranty', 'certification', 'yes', 'no', 'specification', 'sub-spec']):
                    break
                clean_spec.append(l)
            if clean_spec:
                res = clean_text(' '.join(clean_spec))
                if res != NA and len(res) > 3:
                    category_quadrant = res

    # 8. Fallback to Product Specification Title
    if product_name == NA or category_quadrant == NA or category_quadrant.lower() in {"model", "hsn code"}:
        m_ps = re.search(r'Product\s*Specification\s*for\s*([^\n]+(?:\n[^\n]+)?)', raw_text, re.IGNORECASE)
        if m_ps:
            ps_title = clean_text(m_ps.group(1))
            if product_name == NA:
                product_name = ps_title
            if category_quadrant == NA or category_quadrant.lower() in {"model", "hsn code"}:
                category_quadrant = ps_title

    qty = NA
    unit_price = NA
    total_val = NA

    if table_data.get('qty'):
        qty = to_number(table_data['qty'])
    if table_data.get('price'):
        total_val = to_number(table_data['price'])

    # 9. Total Order Value first
    tot_str = match_multiline_kv(r'(?:Total\s*Order\s*Value|कुल\s*ऑर्डर\s*मूल्य|कुल\s*ऑड[EHLG]र\s*मू[\|य\s]+|Total\s*Contract\s*Value)', raw_text, max_lines=1)
    if tot_str != NA:
        total_val = to_number(tot_str)

    if total_val == NA:
        m_tot = re.search(r'Total\s*Order\s*Value[^\n]*\n\s*([\d,]+\.?\d*)', raw_text, re.IGNORECASE)
        if m_tot:
            total_val = to_number(m_tot.group(1))

    # 10. Table row: 5-column or 4-column (Quantity, Unit, Unit Price, Tax, Total Price)
    m_row1 = re.search(
        r'\n\s*(\d+)\s*\n\s*(?:pieces|Nos\.?|units?|box|meters?|set|each|packets?|Test|[A-Za-z]+)\s*\n\s*([\d,]+\.?\d*)\s*\n\s*(?:NA|[\d,]+\.?\d*)\s*\n\s*([\d,]+\.?\d*)',
        section, re.IGNORECASE
    )
    if m_row1:
        qty = to_number(m_row1.group(1))
        unit_price = to_number(m_row1.group(2))
        if total_val == NA:
            total_val = to_number(m_row1.group(3))

    # 11. Table row with Lead Time column: (Quantity, Unit, LeadTime, Total Price)
    if qty == NA:
        m_row2 = re.search(
            r'\n\s*(\d+)\s*\n\s*(?:pieces|Nos\.?|units?|box|meters?|set|each|packets?|Test|[A-Za-z]+)\s*\n\s*[-–\d]+\s*\n\s*([\d,]+\.?\d*)',
            section, re.IGNORECASE
        )
        if m_row2:
            qty = to_number(m_row2.group(1))
            row_total = to_number(m_row2.group(2))
            if total_val == NA:
                total_val = row_total
            if qty != NA and qty > 0 and total_val != NA:
                unit_price = round(total_val / qty, 2)

    if qty != NA and unit_price == NA and total_val != NA:
        if qty > 0:
            unit_price = round(total_val / qty, 2)
            if qty > 0 and total_val != NA:
                unit_price = round(total_val / qty, 2)

    # 12. Table row horizontal: "1 pieces 6,000 NA 6,000"
    if qty == NA:
        m_row3 = re.search(
            r'\n\s*(\d+)\s+(?:pieces|Nos\.?|units?|box|meters?|set|each|packets?|Test|[A-Za-z]+)\s+([\d,]+\.?\d*)\s+(?:NA|[\d,]+\.?\d*)\s+([\d,]+\.?\d*)',
            section, re.IGNORECASE
        )
        if m_row3:
            qty = to_number(m_row3.group(1))
            unit_price = to_number(m_row3.group(2))
            if total_val == NA:
                total_val = to_number(m_row3.group(3))

    # 13. Table row 3-element: "1\n pieces\n 39,998"
    if qty == NA:
        m_row4 = re.search(
            r'\n\s*(\d+)\s*\n\s*(?:pieces|Nos\.?|units?|box|meters?|set|each|packets?|Test|[A-Za-z]+)\s*\n\s*([\d,]+\.?\d*)',
            section, re.IGNORECASE
        )
        if m_row4:
            qty = to_number(m_row4.group(1))
            val_found = to_number(m_row4.group(2))
            if total_val != NA and qty > 0:
                unit_price = round(total_val / qty, 2)
            else:
                unit_price = val_found
                total_val = val_found * qty

    # 14. Fallback from Consignee table quantity
    if qty == NA:
        m_cq = re.search(r'(?:Lot\s*No\.?|लॉट\s*नंबर)[\s\S]*?(?:Quantity|मात्रा|मा>ा|मा\?ा)[\s\S]*?\n\s*[-–\w]*\s*\n\s*(\d+)\s*\n\s*(\d{1,2}[-\w/]+)', raw_text, re.IGNORECASE)
        if m_cq:
            qty = to_number(m_cq.group(1))

    # 15. Math reconciliation between Total Order Value, Quantity, and Unit Price
    if total_val != NA and qty != NA and (unit_price == NA or unit_price == 0) and qty > 0:
        unit_price = round(total_val / qty, 2)
    elif unit_price != NA and qty != NA and (total_val == NA or total_val == 0):
        total_val = round(unit_price * qty, 2)
    elif total_val != NA and unit_price != NA and (qty == NA or qty == 0) and unit_price > 0:
        qty = int(round(total_val / unit_price))

    return {
        "product_name": product_name,
        "brand": brand,
        "category_name_quadrant": category_quadrant,
        "ordered_quantity": qty,
        "unit_price": unit_price,
        "total_order_value": total_val
    }


def parse_consignee_section(raw_text: str) -> List[Dict[str, str]]:
    """Parse Consignee Detail section."""
    section = extract_section(
        raw_text,
        ["Consignee Detail", "परेषिती विवरण", "परे%षती %ववरण", "परे\"षती \"ववरण", "परे षती  ववरण", "Consignee Details", "Consignee"],
        ["Product Specification", "ePBG Detail", "Terms and Conditions", "General Terms", "Product Details", "Organisation Details"]
    )
    if not section:
        section = raw_text

    # Address (Full Multiline Address)
    address = extract_full_address(section)
    if address == NA:
        address = extract_full_address(raw_text)

    # Email
    email = clean_email(match_multiline_kv(r'(?:Email\s*(?:ID)?|ईमेल\s*आईडी)', section, max_lines=1))
    if email == NA:
        emails = re.findall(r'[\w.\-+]+@[\w.\-]+\.[a-zA-Z]{2,}', section)
        if emails:
            email = clean_email(emails[0])
        else:
            gov_emails = re.findall(r'[\w.\-+]+@(?:[a-zA-Z0-9.\-]+\.)?(?:gov\.in|nic\.in|kvs\.gov\.in|iaf\.nic\.in)', raw_text)
            if gov_emails:
                email = clean_email(gov_emails[0])

    contact = clean_phone(match_multiline_kv(r'(?:Contact\s*(?:No\.?)?|संपर्क\s*(?:नंबर)?|संपक[EHLGJK]\s*(?:नंबर)?)', section, max_lines=1))
    if contact == NA:
        m_c = re.search(r'(?:Contact|संपर्क|संपक[A-Za-z0-9_])\s*[:|]\s*([^\n]+)', section, re.IGNORECASE)
        if m_c:
            contact = clean_phone(m_c.group(1))

    return [{
        "consignee_address": address,
        "consignee_email": email,
        "consignee_contact_no": contact
    }]


# ──────────────────────────────────────────────────────────────────────────────
# 4-TIER RULE & MATH VALIDATION MATRIX
# ──────────────────────────────────────────────────────────────────────────────

def validate_record(rec: Dict[str, Any]) -> Tuple[str, int, List[str], Dict[str, Any]]:
    """
    Validates extracted fields against deterministic syntactic, format,
    and mathematical rules.

    Returns:
        (status, score, errors_list, details_dict)
    """
    errors = []
    checks = {}

    # 1. Contract No (Mandatory 100%)
    contract_no = rec.get("contract_no", NA)
    if contract_no == NA:
        errors.append("Missing Contract No")
        checks["contract_no"] = False
    elif "GEMC-" in str(contract_no):
        checks["contract_no"] = True
    else:
        errors.append("Invalid Contract No format (must contain GEMC-)")
        checks["contract_no"] = False

    # 2. Generated Date (Mandatory 100%)
    gen_date = rec.get("generated_date", NA)
    if gen_date == NA:
        errors.append("Missing Generated Date")
        checks["generated_date"] = False
    else:
        checks["generated_date"] = True

    # 3. Seller Company Name (Mandatory 100%)
    company_name = rec.get("seller_company_name", NA)
    if company_name == NA or len(str(company_name)) < 2:
        errors.append("Missing Seller Company Name")
        checks["seller_company_name"] = False
    else:
        checks["seller_company_name"] = True

    # 4. Seller Contact No (Mandatory 100%)
    seller_contact = rec.get("seller_contact_no", NA)
    if seller_contact == NA or len(str(seller_contact)) < 7:
        errors.append("Invalid or missing Seller Contact No")
        checks["seller_contact_no"] = False
    else:
        checks["seller_contact_no"] = True

    # 5. Seller Email (Mandatory 100%)
    seller_email = rec.get("seller_email", NA)
    if seller_email == NA or not RE_EMAIL_VALID.match(str(seller_email)):
        errors.append("Invalid or missing Seller Email")
        checks["seller_email"] = False
    else:
        checks["seller_email"] = True

    # 6. Seller GSTIN (Mandatory 100%)
    seller_gstin = rec.get("seller_gstin", NA)
    if seller_gstin == NA or not RE_GSTIN_VALID.match(str(seller_gstin)):
        errors.append(f"Invalid Seller GSTIN format: {seller_gstin}")
        checks["seller_gstin"] = False
    else:
        checks["seller_gstin"] = True

    # 7. Consignee Address (Mandatory 100%)
    consignee_addr = rec.get("consignee_address", NA)
    if consignee_addr == NA or len(str(consignee_addr)) < 5:
        errors.append("Missing Consignee Address")
        checks["consignee_address"] = False
    else:
        checks["consignee_address"] = True

    # 8. Consignee Email (Mandatory 100%)
    consignee_email = rec.get("consignee_email", NA)
    if consignee_email == NA or not RE_EMAIL_VALID.match(str(consignee_email)):
        errors.append("Invalid or missing Consignee Email")
        checks["consignee_email"] = False
    else:
        checks["consignee_email"] = True

    # 9. Ordered Quantity (Mandatory 100%)
    qty = rec.get("ordered_quantity", NA)
    if qty == NA or not (isinstance(qty, (int, float)) and qty > 0):
        errors.append("Invalid or missing Ordered Quantity")
        checks["ordered_quantity"] = False
    else:
        checks["ordered_quantity"] = True

    # 10. Unit Price (Mandatory 100%)
    unit_price = rec.get("unit_price", NA)
    if unit_price == NA or not (isinstance(unit_price, (int, float)) and unit_price > 0):
        errors.append("Invalid or missing Unit Price")
        checks["unit_price"] = False
    else:
        checks["unit_price"] = True

    # 11. Total Order Value & Mathematical Consistency (Mandatory 100%)
    total_val = rec.get("total_order_value", NA)
    if total_val == NA or not (isinstance(total_val, (int, float)) and total_val > 0):
        errors.append("Invalid or missing Total Order Value")
        checks["total_order_value"] = False
    else:
        if checks.get("ordered_quantity") and checks.get("unit_price"):
            expected_total = qty * unit_price
            if abs(expected_total - total_val) > 2.0:
                errors.append(f"Math check mismatch: {qty} * {unit_price} = {expected_total} != {total_val}")
                checks["math_consistency"] = False
            else:
                checks["math_consistency"] = True
        else:
            checks["total_order_value"] = True

    total_rules = len(checks)
    passed_rules = sum(1 for v in checks.values() if v is True)
    score = int((passed_rules / total_rules * 100)) if total_rules > 0 else 0
    status = STATUS_PASS if len(errors) == 0 else STATUS_REVIEW

    return status, score, errors, checks


# ──────────────────────────────────────────────────────────────────────────────
# MASTER DOCUMENT PROCESSOR
# ──────────────────────────────────────────────────────────────────────────────

def process_single_pdf(filepath: str) -> Dict[str, Any]:
    """
    Extracts, cleans, normalizes, and validates all required fields from a GeM contract PDF.
    Zero external network/LLM calls. High-speed local execution.
    """
    filename = os.path.basename(filepath)

    doc = None
    try:
        doc = pymupdf.open(filepath)
        raw_text = ""
        for page in doc:
            raw_text += page.get_text("text") + "\n"
    except Exception as e:
        if doc:
            doc.close()
        return {
            "file_name": filename,
            "contract_no": NA,
            "generated_date": NA,
            "consignee_address": NA,
            "consignee_email": NA,
            "buyer_email": NA,
            "paying_authority_email": NA,
            "seller_company_name": NA,
            "seller_contact_no": NA,
            "seller_email": NA,
            "seller_gstin": NA,
            "seller_address": NA,
            "product_name": NA,
            "brand": NA,
            "category_name_quadrant": NA,
            "ordered_quantity": NA,
            "unit_price": NA,
            "total_order_value": NA,
            "validation_status": STATUS_REVIEW,
            "validation_score": 0,
            "validation_errors": [f"Failed to open PDF: {str(e)}"],
            "validation_checks": {}
        }

    # Extract all sections
    contract_no, gen_date = parse_header(raw_text, filename)
    buyer = parse_buyer_section(raw_text)
    paying_auth = parse_paying_authority_section(raw_text)
    seller = parse_seller_section(raw_text)
    product = parse_product_details(raw_text, doc=doc)
    consignees = parse_consignee_section(raw_text)

    if doc:
        doc.close()

    first_consignee = consignees[0] if consignees else {}

    record = {
        "file_name": filename,
        "contract_no": contract_no,
        "generated_date": gen_date,
        "consignee_address": first_consignee.get("consignee_address", NA),
        "consignee_contact_no": first_consignee.get("consignee_contact_no", NA),
        "consignee_email": first_consignee.get("consignee_email", NA),
        "buyer_email": buyer.get("email", NA),
        "paying_authority_email": paying_auth.get("email", NA),
        "seller_company_name": seller.get("company_name", NA),
        "seller_contact_no": seller.get("contact_no", NA),
        "seller_email": seller.get("email", NA),
        "seller_gstin": seller.get("gstin", NA),
        "seller_address": seller.get("address", NA),
        "product_name": product.get("product_name", NA),
        "brand": product.get("brand", NA),
        "category_name_quadrant": product.get("category_name_quadrant", NA),
        "ordered_quantity": product.get("ordered_quantity", NA),
        "unit_price": product.get("unit_price", NA),
        "total_order_value": product.get("total_order_value", NA),
    }

    # Run 4-Tier Validation Matrix
    status, score, errors, checks = validate_record(record)
    record["validation_status"] = status
    record["validation_score"] = score
    record["validation_errors"] = errors
    record["validation_checks"] = checks

    return record
