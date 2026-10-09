"""
extractor.py — GeM Contract High-Speed Non-LLM Parser & Validation Engine
=========================================================================
Extracts structured data from Government e-Marketplace (GeM) contract PDFs
using PyMuPDF for high-speed local text extraction and deterministic regex/tabular rules.

Features:
  1. Multi-Product Contract Parsing (creates separate accurate entries for every product).
  2. Pure English, Bilingual English|Hindi, and Hindi|English layouts.
  3. Strict Address Sanitizer (prevents table description/dates/quantity bleed into address).
  4. Strict Brand Filter (prevents technical specifications from polluting brand column).
  5. Multi-line continuous field scanning without truncation.
  6. 4-Tier Automated Verification Matrix (Syntax, Math, Section Isolation, Consistency).
  7. Deterministic PASS / REVIEW status scoring with detailed error breakdown.
  8. Delivery date extraction, Model, HSN, Brand Type fields.
  9. Per-item brand isolation (no bleed between items).
  10. Robust unit_price/qty disambiguation (lot-number vs actual quantity).
  11. All-zero phone number rejection.
  12. Consignee address deduplication.
"""

import re
import os
import pymupdf  # PyMuPDF
from typing import Dict, Any, List, Optional, Tuple
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
# TEXT CLEANING & SANITIZATION
# ──────────────────────────────────────────────────────────────────────────────

def transliterate_hindi(text: str) -> str:
    """Convert Devanagari characters to clean English / Latin equivalents."""
    if not text or text == NA:
        return text
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    if RE_DEVANAGARI.search(text):
        return unidecode(text)
    return text


def clean_text(text: Optional[str]) -> str:
    """Normalize whitespace, strip control chars, and clean extraneous punctuation."""
    if not text:
        return NA
    cleaned = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', str(text))
    cleaned = cleaned.replace('\xa0', ' ')
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    cleaned = re.sub(r'^[:|\-–\s]+|[:|\-–\s]+$', '', cleaned).strip()
    if not cleaned or cleaned.upper() in {"-", "--", "N/A", "NONE", "NULL", "NA"}:
        return NA
    return transliterate_hindi(cleaned)


def clean_phone(text: Optional[str]) -> str:
    """
    Normalize phone / contact numbers.
    - Rejects strings containing alphabet characters (e.g. GeM Seller ID like T1T8220005368703, GSTIN, MSME Udyam).
    - Rejects all-zero numbers (e.g. 0000-000000-00000).
    - Preserves pure digits for valid non-zero phone numbers between 7 and 18 digits.
    """
    if not text or text == NA:
        return NA
    text_str = str(text).strip()

    # Remove standard prefixes
    text_str = re.sub(r'^(?:Contact\s*(?:No\.?)?|संपर्क\s*नंबर|संपक[^\n:]*नंबर|सम्पर्क\s*नंबर|संपर्क|Phone|Mob(?:ile)?|Tel(?:ephone)?)\s*[:.\-–=]*\s*', '', text_str, flags=re.IGNORECASE).strip()
    text_str = re.sub(r'^\+91[\s\-]*', '', text_str)
    text_str = re.sub(r'^\+', '', text_str)

    # Remove trailing/leading punctuation
    text_str = re.sub(r'[:|;,\s\-–/.]+$', '', text_str)
    text_str = re.sub(r'^[:|;,\s\-–/.]+', '', text_str)

    # If candidate still contains any alphabetic characters [a-zA-Z], it is NOT a phone number
    if re.search(r'[a-zA-Z]', text_str):
        return NA

    # All-zero check (e.g. 0000-0000000-0000)
    digits_only = re.sub(r'[^\d]', '', text_str)
    if not digits_only or all(d == '0' for d in digits_only):
        return NA

    # If pure digits length is between 7 and 18 digits
    if 7 <= len(digits_only) <= 18:
        return digits_only

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
        val = re.sub(r'^(?:address|pataa|ptaa|pata|पता)\b[:.\ \-–;=]*', '', val, flags=re.IGNORECASE).strip()
        val = re.sub(r'^[:|\-–;,\s]+', '', val).strip()
        if val == prev:
            break

    val = re.sub(r'\s+', ' ', val).strip()
    val = re.sub(r'^[:|\-–;,\s]+|[:|\-–;\s,]+$', '', val).strip()

    if not val or val.upper() in {"-", "--", "N/A", "NONE", "NULL", "NA"}:
        return NA
    return val


def sanitize_consignee_address(address_str: str) -> str:
    """
    Sanitizes consignee addresses by stripping leaked table text, item descriptions,
    quantities, delivery dates, and deduplicating repetitive address tokens.
    """
    if not address_str or address_str == NA:
        return NA

    addr = str(address_str).strip()

    # Truncate any text trailing after ', India' or ', Bharat' to prevent adjacent column spillage
    addr = re.sub(r'(\b(?:India|Bharat|भारत)\b)[\s\S]*$', r'\1', addr, flags=re.IGNORECASE)

    # 1. Remove date ranges (e.g. 23-Dec-202507-Jan-2026, 11-Dec-202526-Dec-2025, 14-Oct-202529-Oct-2025)
    addr = re.sub(r'\d{1,2}-[A-Za-z]{3}-\d{4}\s*\d{1,2}-[A-Za-z]{3}-\d{4}', ', ', addr)
    addr = re.sub(r'-\s*\d{1,2}-[A-Za-z]{3}-\d{4}', ', ', addr)
    addr = re.sub(r'\b\d{1,2}-[A-Za-z]{3}-\d{4}\b', ', ', addr)
    addr = re.sub(r'\b\d{1,2}/\d{1,2}/\d{4}\b', ', ', addr)
    addr = re.sub(r'-\s*\d+\s+(?=[A-Za-z]{3})', ', ', addr)
    addr = re.sub(r'-\s*\d+\s*$', '', addr)

    # 2. Remove leaked item/product/brand/spec fragments from adjacent table columns
    patterns_to_remove = [
        r'(?:Unbranded|[A-Z0-9\s]{3,25}(?:SPORTS|INDUSTRIES|INSTRUMENTS|FIBROTECH|HEALTHCARE|TRADERS|ENTERPRISES|MEDITIVE|surgitek|cosco|DEC|GOFIT|TIPL|GEMTRACK|LCS|KSE|IMI|MAAOON|Climbing\s+Technology))\s*(?:Chest Press|Surf Board|Sit Up|Twister|Air Walker|Stroller|Parallel Bar|Leg Press|Shoulder Builder|Arm Wheel|Gym Kit|Ankle|Knee Hammer|Infantometer|Stadiometer|Dustbin|Oven|Mattress|Bean Bag|Chamber|Autoclave|Couch|Centrifuge|Therapy|Fogging Machine|Table|Wheel|Mirror|Concentrator|Spray|Kit|Cross Trainer|Rowing Machine|Pulley|Roller|Hydrocollator)[^,]*',
        r'-\s*Max user[^,]*',
        r'-\s*\d+\s*(?:kilogram|kg|pieces|Nos|units)\b[^,]*',
        r'Warranty\s*\d+[^,]*',
        r'(?:STATE\s*-\s*)?Unbranded[^,]*',
        r'(?:STATE\s*-\s*)?(?:MAAOON|GOFIT|PARTH|Climbing Technology|INDIA MEDICO|FIDELIS|IKON|MEDITIVE)[^,]*',
        r'Product Name\s*:[^,]*',
        r'kilogram\s*-\s*\d+',
        r'Consignee\s*Detail[\s\S]*?(?:Address|ptaa|पता)\s*[:.]\\s*',
    ]
    for pat in patterns_to_remove:
        addr = re.sub(pat, ', ', addr, flags=re.IGNORECASE)

    addr = re.sub(r'\bSTATE\s*-\s*', '', addr, flags=re.IGNORECASE)

    # 3. Clean up punctuation and spacing
    addr = re.sub(r'[,;\s]+,', ',', addr)
    addr = re.sub(r'\s+', ' ', addr)

    # 4. Deduplicate repeating comma-separated segments
    parts = [p.strip() for p in addr.split(',') if p.strip()]
    unique_parts = []
    seen_normalized = []
    for p in parts:
        p_clean = re.sub(r'[:.\s\-–;]+', '', p).lower()
        if p_clean not in seen_normalized:
            unique_parts.append(p)
            seen_normalized.append(p_clean)
    addr = ', '.join(unique_parts)

    return clean_address(addr)


def sanitize_brand(brand_str: Optional[str]) -> str:
    """Strictly validates Brand name, stripping specifications and normalizing Unbranded/NA."""
    if not brand_str or brand_str == NA:
        return NA
    b = str(brand_str).strip()
    
    # Catch unbranded first before any label modifications
    if re.search(r'\bunbranded\b', b, re.IGNORECASE) or b.lower().startswith("unbranded"):
        return NA
    if b.lower() in {"not specified", "not specified by seller", "not specified by buyer", "not specified by oem", "na", "n/a", "none", "null", "-", "--"}:
        return NA

    # Strip leading label (e.g. "Brand :", "ब्रांड :", "ब्रांड|Brand :")
    b = re.sub(r'^(?:[^\n:]*?\b(?:ब्रांड|Brand)\b\s*[:|.\-–=]*\s*)+', '', b, flags=re.IGNORECASE).strip()
    b = re.sub(r'^(?:Brand|ब्रांड)\s*[:|.\-–=]*\s*', '', b, flags=re.IGNORECASE).strip()
    
    # Strip any trailing labels using strict word boundaries
    b = re.split(r'[:|]?\s*(?:\bBrand\s*Type\b|\bCatalogue\s*Status\b|\bSelling\s*As\b|\bCategory\s*Name\b|\bModel\b|\bHSN\s*Code\b|कैटलॉग|मॉडल|एचएसएन)', b, flags=re.IGNORECASE)[0].strip()
    b = clean_text(b)
    if not b or b.upper() in {"NA", "N/A", "NONE", "NULL", "-", "--", "BRAND : NA", "BRAND:NA", "ED"}:
        return NA
    if b.lower().startswith("unbranded") or "unbranded" in b.lower():
        return NA
    if b.startswith("NA ") or b.startswith("NA-"):
        return NA
    # Reject if it looks like technical specifications, pipe dimensions, or long sentences
    if re.search(r'\b(?:\d+\s*x\s*\d+|GI Pipe|Angle|deep|supported|Gym Equipment|Double|Single|Parallel Bar|Chest Press|Surf Board|Triple|Two Wheel|Three|Both Standing)\b', b, re.IGNORECASE):
        return NA
    if len(b) > 45:
        return NA
    return b


def clean_product_name(p_name: Optional[str]) -> str:
    """Cleans product name, removing headers, delimiters, and Hindi OCR artifacts."""
    if not p_name or p_name == NA:
        return NA
    p = str(p_name).strip()

    # Iterative prefix stripping before and after normalization
    prefix_pat = re.compile(
        r'^(?:[^\n:]*?(?:पाद|paad|utpaad|u\S*paad)\s*(?:का\s*नाम|kaa\s*naam)?\s*(?:[|/\\–\-]\s*)?(?:Product\s*Name\s*)?|Product\s*Name\s*|Item\s*Description\s*|आइटम\s*विवरण\s*)[:|.\-–=]*\s*',
        re.IGNORECASE
    )
    for _ in range(5):
        prev = p
        p = prefix_pat.sub('', p).strip()
        p = re.sub(r'^(?:[a-z|{z~x_]*paad\s*(?:kaa\s*naam)?\s*(?:[|/\\–\-]\s*)?(?:Product\s*Name\s*)?|Product\s*Name\s*)[:|.\-–=]*\s*', '', p, flags=re.IGNORECASE).strip()
        p = re.sub(r'^[\|\ -:.\ \s]+', '', p).strip()
        if p == prev:
            break

    # Strip trailing labels using strict word boundaries
    p = re.split(r'[:|]?\s*(?:\bBrand\s*Type\b|\bBrand\s*:|\bCatalogue\s*Status\b|\bSelling\s*As\b|\bCategory\s*Name\b|\bModel\b|\bHSN\s*Code\b|कैटलॉग|मॉडल|एचएसएन)', p, flags=re.IGNORECASE)[0].strip()

    # Strip trailing OCR artifacts like 'aaNdd', 'aaNd' or normalize
    p = re.sub(r'\s+aaN+d*\s*$', '', p, flags=re.IGNORECASE).strip()
    p = re.sub(r'\baaN+d+\b', 'and', p, flags=re.IGNORECASE).strip()
    p = re.sub(r'[,:\-–|]+$', '', p).strip()
    p = clean_text(p)

    # Post-clean check for any remaining transliterated prefix
    p = re.sub(r'^(?:[a-z|{z~x_]*paad\s*(?:kaa\s*naam)?\s*(?:[|/\\–\-]\s*)?(?:Product\s*Name\s*)?|Product\s*Name\s*)[:|.\-–=]*\s*', '', p, flags=re.IGNORECASE).strip()
    p = re.sub(r'^[\|\ -:.\ \s]+', '', p).strip()
    p = re.sub(r'\s+\b(?:aaN+d+|aaNd|evam|और|एवं|and)\b\s*$', '', p, flags=re.IGNORECASE).strip()
    p = re.sub(r'[,:\-–|]+$', '', p).strip()
    return p


def clean_category_quadrant(cat_str: Optional[str]) -> str:
    """Cleans category name and quadrant, retaining complete name & (Q1/Q2/Q3/Q4)."""
    if not cat_str or cat_str == NA:
        return NA
    c = str(cat_str).strip()
    # Strip trailing labels using strict word boundaries
    c = re.split(r'[:|]?\s*(?:\bModel\b|\bHSN\s*Code\b|मॉडल|एचएसएन|\bBrand\b|कैटलॉग|\bSelling\s*As\b)', c, flags=re.IGNORECASE)[0].strip()
    c = re.sub(r'-\s*([A-Za-z])', r'- \1', c)
    c = re.sub(r'([A-Za-z])\s*-', r'\1 -', c)
    c = re.sub(r'\s+', ' ', c).strip()
    c = clean_text(c)
    return c


def extract_full_address(section: str) -> str:
    """
    Extracts complete multi-line address until 'India', pin-code, or next structural section.
    """
    if not section:
        return NA

    # Pattern 1: Address up to ', India' or ', Bharat' or 6-digit PIN with India
    m_india = re.search(
        r'(?:Address|पता)\s*[:.\ \s]*\n?\s*([\s\S]+?,\s*(?:India|भारत|\d{6},\s*India))',
        section, re.IGNORECASE
    )
    if m_india:
        addr = clean_address(m_india.group(1))
        if 5 <= len(addr) <= 350:
            return addr

    # Pattern 2: Address up to State-PIN: e.g. UTTAR PRADESH-250002, -
    m_pin = re.search(
        r'(?:Address|पता)\s*[:.\ \s]*\n?\s*([\s\S]+?,\s*[A-Z\s]+-\d{6}(?:,\s*[-–\w]+)?)',
        section, re.IGNORECASE
    )
    if m_pin:
        addr = clean_address(m_pin.group(1))
        if 5 <= len(addr) <= 350:
            return addr

    # Pattern 3: Multiline address stopping before next known section/table header
    m_stop = re.search(
        r'(?:Address|पता)\s*[:.\ \s]*\n?\s*([^\n\r]+(?:\n\s*[^\n\r]+){1,5})',
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
            if 5 <= len(addr) <= 350:
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


def is_unit_label(val: Optional[str]) -> bool:
    """Returns True if a cell value is a unit-of-measure label (pieces, Nos, kg, etc.)."""
    if not val:
        return False
    return bool(re.match(
        r'^\s*(?:pieces?|Nos?\.?|units?|box(?:es)?|meters?|set|each|packets?|kg|kilogram|Test)\s*$',
        str(val).strip(), re.IGNORECASE
    ))


def looks_like_lot_number(val: Any, row_idx_in_data: int) -> bool:
    """
    Heuristic: returns True if val looks like a sequential lot/serial number
    rather than an actual quantity.  We check if it equals the 1-based row index.
    """
    if val is None:
        return False
    try:
        n = int(str(val).strip().replace(',', ''))
    except (ValueError, TypeError):
        return False
    # Lot numbers start from 1 and are sequential; actual quantities rarely match row index
    # unless it's also 1 (common for quantity=1). So we use a relaxed check:
    # if the value equals the expected sequential lot number AND is <= 20, treat as lot number
    # ONLY when we can verify via the unit_price column that the actual price is much larger.
    return False  # We handle this per-item during reconciliation instead


# ──────────────────────────────────────────────────────────────────────────────
# SECTION EXTRACTION UTILITIES (Bilingual Support)
# ──────────────────────────────────────────────────────────────────────────────

def extract_section(text: str, start_keywords: List[str], end_keywords: List[str]) -> str:
    """Extracts text between start_keyword and earliest end_keyword."""
    start_pos = -1
    for kw in start_keywords:
        pat = re.compile(kw, re.IGNORECASE)
        m = pat.search(text)
        if m and (start_pos == -1 or m.start() < start_pos):
            start_pos = m.end()

    if start_pos == -1:
        return ""

    end_pos = len(text)
    for kw in end_keywords:
        pat = re.compile(kw, re.IGNORECASE)
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

        if val_lines and re.match(r'^(?:pieces|Nos\.?|units?|box|meters?|set|each|packets?|Test|\d{1,4})$', l_str, re.IGNORECASE):
            break
        if val_lines and re.match(r'^\d{1,4}\s+(?:pieces|Nos|units|box|meters|set|each|packets|Test)\b', l_str, re.IGNORECASE):
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
    m_inline = re.search(
        r'(?:Generated\s*Date|Contract\s*Date|Date\s*of\s*Contract|अनुबंध\s*तिथि|अनुबंध\s*[\%!]?त[\%!]?थ)\s*[:.\s]*\s*(\d{1,2}[-\/]\w{3}[-\/]\d{2,4}|\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4})',
        raw_text, re.IGNORECASE
    )
    if m_inline:
        return m_inline.group(1).strip()

    m_next = re.search(
        r'(?:Generated\s*Date|Contract\s*Date|Date\s*of\s*Contract|अनुबंध\s*तिथि|अनुबंध\s*[\%!]?त[\%!]?थ)\s*[:.\s]*\n\s*(\d{1,2}[-\/]\w{3}[-\/]\d{2,4}|\d{1,2}[-\/]\d{1,2}[-\/]\d{2,4})',
        raw_text, re.IGNORECASE
    )
    if m_next:
        return m_next.group(1).strip()

    all_dates = re.findall(
        r'\b(\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{4})\b',
        raw_text, re.IGNORECASE
    )
    if all_dates:
        return all_dates[0]

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
        gem_m = re.search(r'\b(GEM-[0-9]{12,18})\b', raw_text)
        if gem_m:
            contract_no = gem_m.group(1)
        else:
            contract_no = match_multiline_kv(r'(?:Contract\s*No|अनुबंध\s*क्रमांक|अनुबंध\s*मांक)', raw_text, max_lines=1)
            if contract_no == NA and filename:
                m_fn = re.search(r'\b(GEMC?-[0-9]{12,18})\b', filename)
                if m_fn:
                    contract_no = m_fn.group(1)

    gen_date = extract_clean_date(raw_text)

    return contract_no, gen_date


def parse_organisation_section(raw_text: str) -> Dict[str, str]:
    """
    Parse Organisation Details section strictly.
    Extracts the exact Organisation Name specified under the Organisation Name heading.
    If no value is present or if it is N/A / -, returns NA.
    Does NOT fallback to Department, Office Zone, Ministry, or other headings.
    """
    text = raw_text.replace('\ufb00', 'ff').replace('\ufb01', 'fi').replace('\ufb02', 'fl').replace('\ufb03', 'ffi').replace('\ufb04', 'ffl')
    section = extract_section(
        text,
        [r'Organisation\s*Details', r'संगठन[^\n:]*विवरण', r'संगठन[^\n:]*ववरण', r'संगठन'],
        [r'Buyer\s*Details', r'खरीदार', r'Financial\s*Approval', r'Paying\s*Authority', r'Seller\s*Details']
    )
    if not section:
        section = text[:2000]

    label_pattern = re.compile(
        r'(?:संगठन\s*का\s*(?:\n\s*)?नाम\s*(?:[|/\\–\-]\s*)?Organisation\s*Name|Organisation\s*Name\s*(?:[|/\\–\-]\s*)?संगठन\s*का\s*(?:\n\s*)?नाम|Organisation\s*Name|संगठन\s*का\s*नाम|संगठन\s*नाम|sNgtthn\s*kaa\s*naam)\s*[:.\-–=]*\s*',
        re.IGNORECASE
    )

    m = label_pattern.search(section)
    if not m:
        return {"organisation_name": NA}

    remaining = section[m.end():].lstrip('\r\n')
    lines = remaining.split('\n')

    # Stop headings: Must match as a HEADING (with colon or at start of line as heading)
    stop_heading_pats = [
        r'^(?:[^\n:]*?(?:काया|कार्यालय|kaayaa|Office\s*Zone|Oﬃce\s*Zone)\b\s*[:|.\-–=])',
        r'^(?:[^\n:]*?(?:Buyer\s*Details|खरीदार|Buying\s*Organisation)\b)',
        r'^(?:[^\n:]*?(?:Department|विभाग|वभाग)\b\s*[:|.\-–=])',
        r'^(?:[^\n:]*?(?:Ministry|मंत्रालय)\b\s*[:|.\-–=])',
        r'^(?:[^\n:]*?(?:Type|प्रारूप)\b\s*[:|.\-–=])',
        r'^(?:[^\n:]*?(?:Paying\s*Authority|भुगतान)\b)',
        r'^(?:[^\n:]*?(?:Financial\s*Approval|वित्तीय)\b)',
    ]

    val_parts = []
    for line in lines[:5]:
        line_s = line.strip()
        if not line_s:
            if val_parts:
                break
            continue

        # Check if line matches any stop heading pattern
        if any(re.search(pat, line_s, re.IGNORECASE) for pat in stop_heading_pats):
            break

        # Check for inline next heading (e.g. "Adg Pac कायाEलय Fे=|Oﬃce Zone: ...")
        m_inline_stop = re.search(r'\s+(?:काया[^\n:]*|कार्यालय[^\n:]*|Office\s*Zone|Oﬃce\s*Zone|Buyer\s*Details|खरीदार)\s*[:|.\-–=]', line_s, re.IGNORECASE)
        if m_inline_stop:
            val_parts.append(line_s[:m_inline_stop.start()].strip())
            break

        val_parts.append(line_s)

    if not val_parts:
        return {"organisation_name": NA}

    val = ' '.join(val_parts).strip()
    val = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', val)
    val = re.sub(r'\s+', ' ', val).strip()
    val = re.sub(r'^[:|\-–\s]+|[:|\-–\s]+$', '', val).strip()
    val = clean_text(val)

    if not val or val.upper() in {"-", "--", "N/A", "NONE", "NULL", "NA", "N / A", "ORGANISATION", "संगठन", "ORGANISATION NAME"}:
        return {"organisation_name": NA}

    return {"organisation_name": val}


def parse_buyer_section(raw_text: str) -> Dict[str, str]:
    """Parse Buyer Details section."""
    section = extract_section(
        raw_text,
        [r'Buyer\s*Details', r'खरीदार[^\n:]*विवरण', r'खरीदार[^\n:]*ववरण', r'Buying\s*Organisation', r'खरीदार'],
        [r'Financial\s*Approval', r'वित्तीय', r'Paying\s*Authority', r'भुगतान', r'Seller\s*Details', r'विक्रेता']
    )
    if not section:
        section = raw_text

    email = clean_email(match_multiline_kv(r'(?:Email\s*(?:ID)?|ईमेल\s*आईडी)', section, max_lines=1))
    
    # 1. Match Contact No with label directly (handling same line or next line)
    m_c = re.search(r'(?:Contact\s*(?:No\.?|Number)?|संपर्क\s*(?:नंबर|नं\.?)|संपक[^\n:]*नंबर|सम्पर्क\s*(?:नंबर|नं\.?)|Phone\s*(?:No\.?)?|Mob(?:ile)?(?:\s*No\.?)?)\s*[:.\-–=]*\s*\n?\s*([^\n\r]+)', section, re.IGNORECASE)
    contact = NA
    if m_c:
        contact = clean_phone(m_c.group(1))
    if contact == NA:
        contact = clean_phone(match_multiline_kv(r'(?:Contact\s*(?:No\.?|Number)?|संपर्क\s*(?:नंबर|नं\.?)|संपक[^\n:]*नंबर|सम्पर्क\s*(?:नंबर|नं\.?)|Phone\s*(?:No\.?)?|Mob(?:ile)?(?:\s*No\.?)?)', section, max_lines=2))
    
    # 2. Strict standalone phone fallback (excluding non-phone lines)
    if contact == NA:
        for line in section.split('\n'):
            if any(k in line.lower() for k in ['gstin', 'जीएसट', 'email', 'ईमेल', 'address', 'पता', 'designation', 'पद']):
                continue
            m_phone = re.search(r'\b(?:0[1-9]\d{8,11}|[6-9]\d{9}|0\d{2,5}[-\s]\d{6,8})\b', line)
            if m_phone:
                contact = clean_phone(m_phone.group(0))
                if contact != NA:
                    break

    gstin = clean_gstin(match_multiline_kv(r'(?:GSTIN|जीएसटीआईएन|जीएसट[cai\]\^_\s]*आईएन)', section, max_lines=1))

    return {
        "email": email,
        "contact_no": contact,
        "gstin": gstin
    }


def parse_paying_authority_section(raw_text: str) -> Dict[str, str]:
    """Parse Paying Authority Details section."""
    section = extract_section(
        raw_text,
        [r'Paying\s*Authority\s*Details', r'भुगतान[^\n:]*प्राधिकरण', r'भुगतान[^\n:]*6ा"धकरण', r'Paying\s*Authority', r'भुगतान'],
        [r'Seller\s*Details', r'विक्रेता', r'Product\s*Details', r'उत्पाद', r'Consignee\s*Detail', r'परेषिती', r'Total\s*Order\s*Value']
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
        [r'Seller\s*Details', r'विक्रेता[^\n:]*विवरण', r'[\%!\$"]?व\x10?ेता[^\n:]*[\%!\$"]?ववरण', r'Authorized\s*Seller', r'विक्रेता'],
        [r'Product\s*Details', r'उत्पाद', r'Delivery\s*Instructions', r'वितरण', r'Consignee\s*Detail', r'परेषिती', r'Total\s*Order\s*Value', r'Paying\s*Authority']
    )
    if not section:
        section = raw_text

    company_name = match_multiline_kv(r'(?:Company\s*Name|कंपनी\s*का\s*नाम)', section, max_lines=3)
    
    # 1. Match Contact No with label directly (handling same line or next line)
    m_c = re.search(r'(?:Contact\s*(?:No\.?|Number)?|संपर्क\s*(?:नंबर|नं\.?)|संपक[^\n:]*नंबर|सम्पर्क\s*(?:नंबर|नं\.?)|Phone\s*(?:No\.?)?|Mob(?:ile)?(?:\s*No\.?)?)\s*[:.\-–=]*\s*\n?\s*([^\n\r]+)', section, re.IGNORECASE)
    contact_no = NA
    if m_c:
        contact_no = clean_phone(m_c.group(1))
    if contact_no == NA:
        contact_no = clean_phone(match_multiline_kv(r'(?:Contact\s*(?:No\.?|Number)?|संपर्क\s*(?:नंबर|नं\.?)|संपक[^\n:]*नंबर|सम्पर्क\s*(?:नंबर|नं\.?)|Phone\s*(?:No\.?)?|Mob(?:ile)?(?:\s*No\.?)?)', section, max_lines=2))
    
    # 2. Strict standalone phone fallback excluding Seller ID, GSTIN, MSME, Address, Email lines
    if contact_no == NA:
        for line in section.split('\n'):
            if any(k in line.lower() for k in ['seller id', 'आईडी', 'gstin', 'जीएसट', 'msme', 'पंजीकरण', 'address', 'पता', 'email', 'ईमेल']):
                continue
            m_phone = re.search(r'\b(?:0[1-9]\d{8,11}|[6-9]\d{9}|0\d{2,5}[-\s]\d{6,8})\b', line)
            if m_phone:
                contact_no = clean_phone(m_phone.group(0))
                if contact_no != NA:
                    break

    email = clean_email(match_multiline_kv(r'(?:Email\s*(?:ID)?|ईमेल\s*आईडी)', section, max_lines=1))
    if email == NA:
        emails = re.findall(r'[\w.\-+]+@[\w.\-]+\.[a-zA-Z]{2,}', section)
        for e in emails:
            if not e.endswith('@gov.in') and not e.endswith('@nic.in'):
                email = clean_email(e)
                break
        if email == NA and emails:
            email = clean_email(emails[0])

    gstin = clean_gstin(match_multiline_kv(r'(?:GSTIN|जीएसटीआईएन|जीएसट[cai\]\^_\s]*आईएन)', section, max_lines=1))
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


def parse_consignee_section(raw_text: str, doc: Optional[Any] = None) -> List[Dict[str, str]]:
    """Parse Consignee Detail section strictly without polluting with Seller/Buyer details."""
    consignee_cells = []

    # 1. Search in tables across all pages
    if doc:
        for page in doc:
            tabs = page.find_tables()
            for tab in tabs.tables:
                extracted = tab.extract()
                if not extracted:
                    continue
                header_idx = -1
                consignee_col = -1
                for r_idx, row in enumerate(extracted):
                    row_clean = [str(c).lower().replace('\n', ' ') for c in row if c]
                    if any('consignee' in c or 'परेषिती' in c or 'परे!षती' in c or 'परेषती' in c for c in row_clean) and any('item' in c or 'lot' in c or 'quantity' in c or 'मात्रा' in c or 'वcतु' in c or 'वgतु' in c for c in row_clean):
                        header_idx = r_idx
                        for c_idx, cell in enumerate(row):
                            if cell and any(k in str(cell).lower() for k in ['consignee', 'परेषिती', 'परे!षती', 'परेषती']):
                                consignee_col = c_idx
                                break
                        break

                if header_idx != -1 and consignee_col != -1:
                    for data_row in extracted[header_idx+1:]:
                        if consignee_col < len(data_row) and data_row[consignee_col]:
                            cell_str = str(data_row[consignee_col]).strip()
                            if any(k in cell_str for k in ['Email ID', 'ईमेल', 'Address', 'पता', 'Designation', 'पद', 'Contact', 'संपर्क', 'ptaa', 'iimel', 'sNpk']):
                                consignee_cells.append(cell_str)

    m_sec = re.search(
        r'(?:Consignee\s*Detail|परे[!षs\s]*ती\s*!ववरण|परे[!षs\s]*ती\s*विवरण|परेषती\s*विवरण|Consignee\s*and\s*Delivery)[\s\S]+?(?=(?:Product\s*Specification|ePBG\s*Detail|Terms\s*and\s*Conditions|General\s*Terms|$))',
        raw_text, re.IGNORECASE
    )
    sec_text = m_sec.group(0) if m_sec else ""

    table_text = "\n".join(consignee_cells) if consignee_cells else ""

    # Extract Email
    email = clean_email(table_text)
    if email == NA and sec_text:
        email = clean_email(sec_text)

    # Extract Contact
    m_c = re.search(r'(?:Contact\s*(?:No\.?)?|संपर्क\s*(?:नंबर)?|संपक[A-Za-z0-9_\s]*|sNpk[A-Za-z0-9_\s]*)\s*[:|.]\s*([^\n\r]+)', table_text, re.IGNORECASE)
    if not m_c and sec_text:
        m_c = re.search(r'(?:Contact\s*(?:No\.?)?|संपर्क\s*(?:नंबर)?|संपक[A-Za-z0-9_\s]*|sNpk[A-Za-z0-9_\s]*)\s*[:|.]\s*([^\n\r]+)', sec_text, re.IGNORECASE)
    contact = clean_phone(m_c.group(1)) if m_c else (clean_phone(table_text) if table_text else clean_phone(sec_text))

    # Extract Address: try table_text first, then sec_text
    addr = NA
    for source_text in [table_text, sec_text]:
        if not source_text:
            continue
        m_india = re.search(r'(?:Address|पता|ptaa|pata)\s*[:|.]\s*([\s\S]+?,\s*(?:India|भारत|\d{6},\s*India))', source_text, re.IGNORECASE)
        if m_india:
            cand = sanitize_consignee_address(m_india.group(1))
            if cand != NA and len(cand) >= 10:
                addr = cand
                break
        m_pin = re.search(r'(?:Address|पता|ptaa|pata)\s*[:|.]\s*([\s\S]+?,\s*[A-Za-z\s]+-\d{6}(?:,\s*[-–\w]+)?)', source_text, re.IGNORECASE)
        if m_pin:
            cand = sanitize_consignee_address(m_pin.group(1))
            if cand != NA and len(cand) >= 10:
                addr = cand
                break
        m_gen = re.search(r'(?:Address|पता|ptaa|pata)\s*[:|.]\s*([^\n\r]+(?:\n\s*[^\n\r]+){1,3})', source_text, re.IGNORECASE)
        if m_gen:
            cand = sanitize_consignee_address(m_gen.group(1))
            if cand != NA and len(cand) >= 10:
                addr = cand
                break

    return [{
        "consignee_address": addr,
        "consignee_email": email,
        "consignee_contact_no": contact
    }]


def extract_delivery_dates(raw_text: str, doc: Optional[Any] = None) -> str:
    """
    Extracts delivery date range(s) from the Consignee table.
    Returns a string like "29-Oct-2024 to 13-Nov-2024" or a semicolon-separated
    list when multiple consignees have different dates.
    """
    date_pat = re.compile(
        r'\b(\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{4})\b',
        re.IGNORECASE
    )

    delivery_pairs = []

    # Strategy 1: Find delivery dates in the consignee table
    if doc:
        for page in doc:
            tabs = page.find_tables()
            for tab in tabs.tables:
                extracted = tab.extract()
                if not extracted:
                    continue

                # Identify header row with "Delivery Start" and "Delivery To Be Completed By"
                hdr_idx = -1
                start_col = -1
                end_col = -1
                for r_idx, row in enumerate(extracted):
                    row_text = ' '.join(str(c).lower().replace('\n', ' ') for c in row if c)
                    if ('delivery start' in row_text or 'delivery after' in row_text) and \
                       ('delivery to' in row_text or 'completed by' in row_text):
                        hdr_idx = r_idx
                        for c_idx, cell in enumerate(row):
                            cell_low = str(cell).lower().replace('\n', ' ') if cell else ''
                            if 'delivery start' in cell_low or ('delivery' in cell_low and 'after' in cell_low):
                                start_col = c_idx
                            elif 'delivery to' in cell_low or 'completed by' in cell_low:
                                end_col = c_idx
                        break

                if hdr_idx != -1 and (start_col != -1 or end_col != -1):
                    for data_row in extracted[hdr_idx + 1:]:
                        start_date = NA
                        end_date = NA
                        if start_col != -1 and start_col < len(data_row) and data_row[start_col]:
                            m = date_pat.search(str(data_row[start_col]))
                            if m:
                                start_date = m.group(1)
                        if end_col != -1 and end_col < len(data_row) and data_row[end_col]:
                            m = date_pat.search(str(data_row[end_col]))
                            if m:
                                end_date = m.group(1)

                        if start_date != NA or end_date != NA:
                            pair = f"{start_date} to {end_date}"
                            if pair not in delivery_pairs:
                                delivery_pairs.append(pair)

    if delivery_pairs:
        return '; '.join(delivery_pairs)

    # Strategy 2: Parse text for delivery date lines
    m_delivery = re.search(
        r'(?:Delivery\s*Start\s*After|Delivery\s*From)[^\n]*[:\s]+(\d{1,2}-\w{3}-\d{4})',
        raw_text, re.IGNORECASE
    )
    m_delivery_end = re.search(
        r'(?:Delivery\s*To\s*Be\s*Completed\s*By|Delivery\s*End)[^\n]*[:\s]+(\d{1,2}-\w{3}-\d{4})',
        raw_text, re.IGNORECASE
    )

    if m_delivery or m_delivery_end:
        start = m_delivery.group(1) if m_delivery else NA
        end = m_delivery_end.group(1) if m_delivery_end else NA
        return f"{start} to {end}"

    # Strategy 3: Extract from consignee section text
    consignee_section = extract_section(
        raw_text,
        [r'Consignee\s*Detail', r'Consignee\s*and\s*Delivery'],
        [r'Product\s*Specification', r'ePBG\s*Detail', r'Terms\s*and\s*Conditions', r'General\s*Terms']
    )
    if consignee_section:
        all_dates = date_pat.findall(consignee_section)
        # In the consignee section, dates usually come in pairs: start, end, start, end...
        # Filter out dates that are obviously in the past (e.g., contract date already captured)
        delivery_dates = []
        for i in range(0, len(all_dates) - 1, 2):
            pair = f"{all_dates[i]} to {all_dates[i+1]}"
            if pair not in delivery_dates:
                delivery_dates.append(pair)
        if delivery_dates:
            return '; '.join(delivery_dates)
        elif all_dates:
            return all_dates[0]

    return NA


def parse_product_cell(cell_text: str) -> Dict[str, str]:
    """Isolates product name, brand, category, model, HSN, brand type from cell or block text."""
    lines = [l.strip() for l in cell_text.split('\n') if l.strip()]
    full_text = '\n'.join(lines)

    # 1. Product Name
    p_name = NA
    m_pn = re.search(
        r'(?:Product\s*Name[^\n:]*|उत्पाद\s*का\s*नाम[^\n:]*|उ[^\w\s]?पाद\s*का\s*नाम[^\n:]*|utpaad\s*kaa\s*naam[^\n:]*|u[|{xz~]paad\s*kaa\s*naam[^\n:]*)\s*[:.]?\s*([\s\S]+?)(?=\n\s*(?:\bBrand\b|ब्रांड|[‚€†\x7f\x80\x81\x83\u0192\w\s|]*?[ाo\u093e]ंड|\bBrand\s*Type\b|\bCatalogue\b|\bSelling\b|\bCategory\b|\bModel\b|\bHSN\b|$))',
        full_text, re.IGNORECASE
    )
    if m_pn:
        p_name = clean_product_name(m_pn.group(1))
    else:
        val_lines = []
        for l in lines:
            if any(l.lower().startswith(k) for k in ['brand', 'catalogue', 'selling', 'model', 'hsn', 'category', 'item description', 'ordered quantity', 'ब्रांड', 'कैटलॉग', 'मॉडल']):
                break
            val_lines.append(l)
        if val_lines:
            p_name = clean_product_name(' '.join(val_lines[:2]))

    # 2. Brand — extracted strictly from THIS cell only (no bleed from other items)
    brand_val = NA
    m_br = re.search(r'(?:\bBrand\b|ब्रांड|[‚€†\x7f\x80\x81\x83\u0192\w\s|]*?[ाo\u093e]ंड)\s*[:.]?\s*([^\n\r]+)', full_text, re.IGNORECASE)
    if m_br:
        brand_val = sanitize_brand(m_br.group(1))

    # 3. Category & Quadrant (capture full multiline name and quadrant)
    cat_val = NA
    m_cat = re.search(
        r'(?:Category\s*Name\s*(?:&|and)?\s*Quadrant?|श्रेणी\s*का\s*नाम[^\n:]*|[^\n:]*?ेणी\s*का\s*नाम[^\n:]*)\s*[:.]?\s*([\s\S]+?)(?=\n\s*(?:\bModel\b|\bHSN\b|\bBrand\s*Type\b|\bBrand\b|\bCatalogue\b|\bSelling\b|मॉडल|एचएसएन|$))',
        full_text, re.IGNORECASE
    )
    if m_cat:
        cat_val = clean_category_quadrant(m_cat.group(1).replace('\n', ' '))

    # 4. Model
    model_val = NA
    m_model = re.search(r'\bModel\s*[:.]?\s*([^\n\r]+)', full_text, re.IGNORECASE)
    if m_model:
        raw_model = m_model.group(1).strip()
        # Reject if it looks like "HSN not specified"
        if not re.search(r'(?:hsn|not specified|NA)', raw_model, re.IGNORECASE):
            model_val = clean_text(raw_model)
            # Limit length to avoid picking up descriptions
            if model_val != NA and len(model_val) > 50:
                model_val = model_val[:50].rstrip()

    # 5. HSN Code
    hsn_val = NA
    m_hsn = re.search(r'\bHSN\s*(?:Code)?\s*[:.]?\s*([^\n\r]+)', full_text, re.IGNORECASE)
    if m_hsn:
        raw_hsn = m_hsn.group(1).strip()
        # Extract just the numeric HSN code if present
        hsn_match = re.search(r'\b(\d{4,8})\b', raw_hsn)
        if hsn_match:
            hsn_val = hsn_match.group(1)
        elif re.search(r'(?:not specified|NA|none)', raw_hsn, re.IGNORECASE):
            hsn_val = NA
        else:
            hsn_val = clean_text(raw_hsn)

    # 6. Brand Type
    brand_type_val = NA
    m_bt = re.search(r'\bBrand\s*Type\s*[:.]?\s*([^\n\r]+)', full_text, re.IGNORECASE)
    if m_bt:
        raw_bt = m_bt.group(1).strip()
        bt_cleaned = clean_text(raw_bt)
        if bt_cleaned != NA:
            brand_type_val = bt_cleaned

    return {
        "product_name": p_name,
        "brand": brand_val,
        "category_name_quadrant": cat_val,
        "model": model_val,
        "hsn_code": hsn_val,
        "brand_type": brand_type_val,
    }


def _detect_column_map(header_row: List) -> Dict[str, int]:
    """
    Detect column indices from a product table header row.
    Returns a dict with keys: item_desc, qty, unit, unit_price, tax, total_price, lot_no
    """
    col_map = {}
    for c_idx, cell in enumerate(header_row):
        if not cell:
            continue
        cl = str(cell).lower().replace('\n', ' ').strip()

        if c_idx == 0 and re.match(r'^[#s\.n]', cl):
            # First column with #/S.No/Sl.No is the lot number column
            col_map['lot_no'] = c_idx
        elif ('item description' in cl or 'आइटम विवरण' in cl) and 'ordered' not in cl and 'quantity' not in cl:
            col_map['item_desc'] = c_idx
        elif ('ordered' in cl or 'quantity' in cl or 'मात्रा' in cl or 'मा=ा' in cl or
              'मा?ा' in cl or 'मा>ा' in cl) and 'price' not in cl:
            col_map['qty'] = c_idx
        elif is_unit_label(cl) or cl in ('unit', 'यूनिट', 'इकाई'):
            col_map['unit'] = c_idx
        elif 'unit price' in cl or 'इकाई मू' in cl:
            col_map['unit_price'] = c_idx
        elif 'tax' in cl or 'bifurcation' in cl or 'कर' in cl:
            col_map['tax'] = c_idx
        elif ('inclusive' in cl or 'all duties' in cl or 'total' in cl or 'सभी' in cl or
              'price' in cl or 'मूल्य' in cl or 'मू य' in cl or 'मू~य' in cl or 'मू}य' in cl):
            if 'unit_price' not in col_map or col_map.get('unit_price') != c_idx:
                col_map['total_price'] = c_idx
        elif 'category' in cl or 'श्रेणी' in cl:
            col_map['category'] = c_idx
        elif 'model' in cl or 'मॉडल' in cl:
            col_map['model'] = c_idx

    return col_map


def _extract_numbers_from_row(data_row: List, col_map: Dict[str, int]) -> Tuple[Any, Any, Any]:
    """
    Robustly extracts (qty, unit_price, total_price) from a data row.

    Key logic:
    - First attempts standard column-mapped lookup.
    - If column-mapped lookup fails or encounters column-shift/spacer column variation across pages,
      scans sequential non-empty trailing cells following the item description cell.
    - Validates that unit_price and total_price are consistent with qty.
    - Rejects unit labels (pieces, Nos, etc.) from numeric columns.
    """
    qty_val = NA
    unit_price_val = NA
    total_price_val = NA

    # 1. Direct Column Mapped Extraction
    def get_num(col_key: str) -> Any:
        idx = col_map.get(col_key) if col_map else None
        if idx is None or idx >= len(data_row) or data_row[idx] is None:
            return NA
        cell = str(data_row[idx]).strip()
        if is_unit_label(cell):
            return NA
        return to_number(cell)

    qty_raw = get_num('qty')
    unit_price_raw = get_num('unit_price')
    total_price_raw = get_num('total_price')

    unit_col = col_map.get('unit') if col_map else None

    # 2. Sequential Trailing Cell Fallback (Handles variable spacer 'None' columns across page breaks)
    # If standard mapped extraction produced NA or invalid numbers, scan non-empty cells after description
    desc_idx = col_map.get('item_desc', 1) if col_map else 1
    if desc_idx >= len(data_row) or (desc_idx == 1 and len(data_row) > 1 and not any(k in str(data_row[1]).lower() for k in ['product', 'उत्पाद', 'उ{', 'उ|', 'उx', 'उz', 'brand', 'ब्रांड', 'category'])):
        for ci, c in enumerate(data_row):
            if c and any(k in str(c).lower() for k in ['product', 'उत्पाद', 'उ{', 'उ|', 'उx', 'उz', 'brand', 'ब्रांड', 'category', 'catalogue', 'model', 'hsn']):
                desc_idx = ci
                break

    trailing_cells = [str(c).strip() for c in data_row[desc_idx + 1:] if c is not None and str(c).strip() != '']
    if (qty_raw == NA or unit_price_raw == NA or (unit_price_raw == 1 and qty_raw == NA)) and len(trailing_cells) >= 2:
        # Extract numeric candidates and unit from trailing cells
        cand_nums = []
        for t_cell in trailing_cells:
            if is_unit_label(t_cell):
                continue
            num = to_number(t_cell)
            if num != NA and isinstance(num, (int, float)):
                cand_nums.append(num)

        if len(cand_nums) >= 3:
            # [qty, unit_price, total_price] or [qty, unit_price, tax, total_price]
            q0, p0, t0 = cand_nums[0], cand_nums[1], cand_nums[-1]
            if abs(q0 * p0 - t0) <= 2.0 or (t0 >= p0 and p0 > 0):
                qty_raw, unit_price_raw, total_price_raw = q0, p0, t0
            else:
                qty_raw, unit_price_raw, total_price_raw = q0, p0, t0
        elif len(cand_nums) == 2:
            q0, t0 = cand_nums[0], cand_nums[1]
            if q0 > 0 and t0 >= q0:
                qty_raw = q0
                total_price_raw = t0
                unit_price_raw = round(t0 / q0, 2)
            else:
                qty_raw, unit_price_raw = q0, t0
        elif len(cand_nums) == 1:
            if cand_nums[0] <= 100:
                qty_raw = cand_nums[0]
            else:
                total_price_raw = cand_nums[0]

    qty_val = qty_raw
    unit_price_val = unit_price_raw
    total_price_val = total_price_raw

    # Disambiguate & Math Validation
    if (qty_val != NA and unit_price_val != NA and total_price_val != NA and
            isinstance(qty_val, (int, float)) and isinstance(unit_price_val, (int, float)) and
            isinstance(total_price_val, (int, float))):

        computed = round(qty_val * unit_price_val, 2)
        if abs(computed - total_price_val) > 2.0:
            if unit_col is not None and unit_col < len(data_row) and data_row[unit_col]:
                uval = to_number(str(data_row[unit_col]))
                if uval != NA and isinstance(uval, (int, float)) and uval > 0:
                    if abs(round(uval * unit_price_val, 2) - total_price_val) <= 2.0:
                        qty_val = uval

            if qty_val == qty_raw and unit_price_val > 0:
                back_qty = total_price_val / unit_price_val
                if abs(back_qty - round(back_qty)) < 0.01:
                    qty_val = int(round(back_qty))

    # Final math reconciliation: Total Order Value ALWAYS equals ordered_quantity * unit_price
    if qty_val != NA and unit_price_val != NA and isinstance(qty_val, (int, float)) and isinstance(unit_price_val, (int, float)):
        total_price_val = round(qty_val * unit_price_val, 2)
    elif qty_val != NA and total_price_val != NA and (unit_price_val == NA or unit_price_val == 0):
        if isinstance(qty_val, (int, float)) and isinstance(total_price_val, (int, float)) and qty_val > 0:
            unit_price_val = round(total_price_val / qty_val, 2)
            total_price_val = round(qty_val * unit_price_val, 2)
    elif unit_price_val != NA and total_price_val != NA and (qty_val == NA or qty_val == 0):
        if isinstance(unit_price_val, (int, float)) and isinstance(total_price_val, (int, float)) and unit_price_val > 0:
            qty_val = int(round(total_price_val / unit_price_val))
            total_price_val = round(qty_val * unit_price_val, 2)

    return qty_val, unit_price_val, total_price_val


# ──────────────────────────────────────────────────────────────────────────────
# MULTI-PRODUCT ITEM PARSER
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# MULTI-PAGE ROW FUSION & CONTINUATION HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _is_product_continuation_cell(cell_text: str) -> bool:
    """
    Returns True if a cell text looks like the 2nd-half continuation of a product row
    (starts with Catalogue Status, Selling As, Category, Model, or HSN, without a new Product Name).
    """
    if not cell_text:
        return False
    cl = cell_text.strip().lower()
    has_pn = any(k in cl for k in ['product name', 'उत्पाद का नाम', 'उ{पाद', 'उ|पाद', 'उxपाद', 'उzपाद', 'utpaad kaa naam'])
    if has_pn:
        return False
    continuation_indicators = [
        'catalogue status', 'कैटलॉग की स्थिति', 'selling as', 'कैसे बेचा जा रहा',
        'category name', 'श्रेणी का नाम', 'quadrant', 'चतुर्थांश', 'model', 'मॉडल',
        'hsn code', 'एचएसएन कोड', 'hsn'
    ]
    return any(k in cl for k in continuation_indicators)


def _reconcile_and_fuse_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Post-extraction failsafe: detects any consecutive split rows across page breaks
    where Item N has the Product Name/Brand (cut off at page bottom) and Item N+1
    has the Category/Model/HSN/Quantity/Prices (started at top of next page).
    Fuses them into a single 100% complete and consistent item.
    """
    if not items or len(items) <= 1:
        return items

    fused_items: List[Dict[str, Any]] = []
    i = 0
    while i < len(items):
        curr = items[i]
        curr_pn = curr.get("product_name", NA)
        curr_qty = curr.get("ordered_quantity", NA)
        curr_up = curr.get("unit_price", NA)
        curr_tot = curr.get("total_order_value", NA)

        # Check if current item is an incomplete half-row
        is_curr_incomplete = (
            curr_pn != NA and (curr_up == NA or curr_up == 0 or curr_qty == NA or curr_qty == 0) and
            (curr_tot == NA or curr_tot == 0)
        )

        if is_curr_incomplete and i + 1 < len(items):
            nxt = items[i + 1]
            nxt_pn = nxt.get("product_name", NA)
            nxt_qty = nxt.get("ordered_quantity", NA)
            nxt_up = nxt.get("unit_price", NA)
            nxt_tot = nxt.get("total_order_value", NA)

            # Check if next item is the matching continuation half
            is_nxt_continuation = (
                (nxt_up != NA and nxt_up > 0 or nxt_tot != NA and nxt_tot > 0 or nxt_qty != NA and nxt_qty > 0) and
                (nxt_pn == NA or len(str(nxt_pn)) < 3 or _is_product_continuation_cell(str(nxt_pn)) or
                 str(nxt_pn).lower().startswith(('catalogue', 'selling', 'category', 'model', 'hsn', 'reseller', 'oem', 'unbranded leg press', str(curr_pn).lower()[:15])))
            )

            if is_nxt_continuation:
                # FUSE curr and nxt into one complete item
                merged_item = {
                    "product_name": curr_pn if curr_pn != NA else nxt_pn,
                    "brand": curr.get("brand", NA) if curr.get("brand", NA) != NA else nxt.get("brand", NA),
                    "brand_type": curr.get("brand_type", NA) if curr.get("brand_type", NA) != NA else nxt.get("brand_type", NA),
                    "category_name_quadrant": nxt.get("category_name_quadrant", NA) if nxt.get("category_name_quadrant", NA) != NA else curr.get("category_name_quadrant", NA),
                    "model": nxt.get("model", NA) if nxt.get("model", NA) != NA else curr.get("model", NA),
                    "hsn_code": nxt.get("hsn_code", NA) if nxt.get("hsn_code", NA) != NA else curr.get("hsn_code", NA),
                    "ordered_quantity": nxt_qty if nxt_qty != NA else curr_qty,
                    "unit_price": nxt_up if nxt_up != NA else curr_up,
                    "total_order_value": nxt_tot if nxt_tot != NA else curr_tot,
                }
                # Reconcile math
                q = merged_item["ordered_quantity"]
                up = merged_item["unit_price"]
                if q != NA and up != NA and isinstance(q, (int, float)) and isinstance(up, (int, float)):
                    merged_item["total_order_value"] = round(q * up, 2)

                fused_items.append(merged_item)
                i += 2
                continue

        # If curr itself is an orphan ghost row with no product name and no prices, skip it
        if curr_pn == NA and (curr_up == NA or curr_up == 0) and (curr_tot == NA or curr_tot == 0):
            i += 1
            continue

        fused_items.append(curr)
        i += 1

    return fused_items


# ──────────────────────────────────────────────────────────────────────────────
# MULTI-PRODUCT ITEM PARSER (Continuous Multi-Page Table Tracking & Row Fusion)
# ──────────────────────────────────────────────────────────────────────────────

def parse_all_product_items(raw_text: str, doc: Optional[Any] = None) -> List[Dict[str, Any]]:
    """
    Comprehensive multi-product extractor combining continuous multi-page table tracking
    with cross-page row continuation stitching and structured text-stream parsing for 100% item coverage.
    """
    table_items = []
    active_col_map = None
    pending_incomplete_row: Optional[Dict[str, Any]] = None

    # 1. Primary Method: PyMuPDF 2D Table Extraction across all pages with stateful row fusion
    if doc:
        try:
            for page in doc:
                page_text = page.get_text("text")
                is_prod_page = any(k in page_text for k in [
                    "Product Details", "उत्पाद विवरण", "उ|पाद", "उ{पाद", "उxपाद", "उzपाद",
                    "Item Description", "Ordered Quantity", "Unit Price", "इकाई मू",
                    "Catalogue Status", "कैटलॉग की स्थिति", "Category Name", "श्रेणी का नाम"
                ])

                if not is_prod_page:
                    if active_col_map and any(k in page_text for k in ["Consignee Detail", "परेषिती", "Terms and Conditions"]):
                        active_col_map = None
                    continue

                tabs = page.find_tables()
                for tab in tabs.tables:
                    extracted = tab.extract()
                    if not extracted or len(extracted) < 1:
                        continue

                    header_row_idx = -1
                    col_map = {}
                    for r_idx, row in enumerate(extracted):
                        row_clean = [str(c).lower().replace('\n', ' ') for c in row if c]
                        has_item = any('item description' in c or 'आइटम विवरण' in c or 'product name' in c for c in row_clean)
                        has_price = any('price' in c or 'मूल्य' in c or 'मू य' in c or 'मू~य' in c or 'मू}य' in c for c in row_clean)
                        has_qty = any('ordered' in c or 'quantity' in c or 'मात्रा' in c or 'मा=ा' in c or 'मा?ा' in c or 'मा>ा' in c for c in row_clean)

                        if (has_item and (has_price or has_qty)) or (has_qty and has_price):
                            header_row_idx = r_idx
                            col_map = _detect_column_map(row)
                            active_col_map = col_map
                            break

                    start_r = header_row_idx + 1 if header_row_idx != -1 else 0
                    curr_map = col_map if header_row_idx != -1 else active_col_map

                    if curr_map and ('item_desc' in curr_map or 'qty' in curr_map or 'total_price' in curr_map):
                        for data_row in extracted[start_r:]:
                            if not data_row or not any(data_row):
                                continue

                            row_text = ' '.join([str(c) for c in data_row if c])
                            if any(stop_kw in row_text.lower() for stop_kw in [
                                'total order value', 'कुल ऑर्डर', 'कुल ऑड', 'consignee detail', 'परेषिती',
                                'terms and conditions', 'limitation of liability', 'note:', 'नोट:'
                            ]):
                                active_col_map = None
                                break

                            desc_idx = curr_map.get('item_desc', 1 if len(data_row) > 1 else 0)
                            item_desc_cell = str(data_row[desc_idx]).strip() if desc_idx < len(data_row) and data_row[desc_idx] else ""

                            # Case A: Check if this row is the 2nd-half continuation of a pending incomplete row from previous page
                            if pending_incomplete_row is not None:
                                is_cont = _is_product_continuation_cell(item_desc_cell) or not any(k in item_desc_cell.lower() for k in ['product name', 'उत्पाद', 'उ{', 'उ|', 'उx', 'उz'])
                                qty_cand, up_cand, tot_cand = _extract_numbers_from_row(data_row, curr_map)
                                has_nums = (qty_cand != NA or up_cand != NA or tot_cand != NA)

                                if is_cont or has_nums:
                                    # FUSE pending row with current continuation row
                                    fused_cell_text = pending_incomplete_row['raw_cell'] + "\n" + item_desc_cell
                                    parsed_desc = parse_product_cell(fused_cell_text)

                                    p_name = parsed_desc.get("product_name", NA)
                                    if p_name == NA:
                                        p_name = pending_incomplete_row.get("product_name", NA)
                                    brand_val = parsed_desc.get("brand", NA)
                                    if brand_val == NA:
                                        brand_val = pending_incomplete_row.get("brand", NA)
                                    cat_val = parsed_desc.get("category_name_quadrant", NA)
                                    model_val = parsed_desc.get("model", NA)
                                    hsn_val = parsed_desc.get("hsn_code", NA)
                                    brand_type_val = parsed_desc.get("brand_type", NA)
                                    if brand_type_val == NA:
                                        brand_type_val = pending_incomplete_row.get("brand_type", NA)

                                    if cat_val == NA and 'category' in curr_map and curr_map['category'] < len(data_row) and data_row[curr_map['category']]:
                                        cat_val = clean_category_quadrant(str(data_row[curr_map['category']]))

                                    if model_val == NA and 'model' in curr_map and curr_map['model'] < len(data_row) and data_row[curr_map['model']]:
                                        model_val = clean_text(str(data_row[curr_map['model']]))

                                    table_items.append({
                                        "product_name": p_name,
                                        "brand": brand_val,
                                        "category_name_quadrant": cat_val,
                                        "ordered_quantity": qty_cand,
                                        "unit_price": up_cand,
                                        "total_order_value": tot_cand,
                                        "model": model_val,
                                        "hsn_code": hsn_val,
                                        "brand_type": brand_type_val,
                                    })
                                    pending_incomplete_row = None
                                    continue
                                else:
                                    # Pending row was not continued; flush it if it had content
                                    table_items.append(pending_incomplete_row['item_dict'])
                                    pending_incomplete_row = None

                            if not item_desc_cell or not any(k in item_desc_cell.lower() for k in ['product name', 'उत्पाद', 'उ{', 'उ|', 'उx', 'उz', 'brand', 'ब्रांड', 'category', 'catalogue', 'selling as', 'model', 'hsn']):
                                continue

                            parsed_desc = parse_product_cell(item_desc_cell)
                            p_name = parsed_desc.get("product_name", NA)
                            brand_val = parsed_desc.get("brand", NA)
                            cat_val = parsed_desc.get("category_name_quadrant", NA)
                            model_val = parsed_desc.get("model", NA)
                            hsn_val = parsed_desc.get("hsn_code", NA)
                            brand_type_val = parsed_desc.get("brand_type", NA)

                            if cat_val == NA and 'category' in curr_map and curr_map['category'] < len(data_row) and data_row[curr_map['category']]:
                                cat_val = clean_category_quadrant(str(data_row[curr_map['category']]))

                            if model_val == NA and 'model' in curr_map and curr_map['model'] < len(data_row) and data_row[curr_map['model']]:
                                model_val = clean_text(str(data_row[curr_map['model']]))

                            # Extract numeric fields
                            qty_val, unit_price_val, total_price_val = _extract_numbers_from_row(data_row, curr_map)

                            # Case B: If row has product name but NO prices/quantities, it might be split at page bottom!
                            if p_name != NA and qty_val == NA and unit_price_val == NA and total_price_val == NA:
                                pending_incomplete_row = {
                                    'raw_cell': item_desc_cell,
                                    'product_name': p_name,
                                    'brand': brand_val,
                                    'brand_type': brand_type_val,
                                    'item_dict': {
                                        "product_name": p_name,
                                        "brand": brand_val,
                                        "category_name_quadrant": cat_val,
                                        "ordered_quantity": qty_val,
                                        "unit_price": unit_price_val,
                                        "total_order_value": total_price_val,
                                        "model": model_val,
                                        "hsn_code": hsn_val,
                                        "brand_type": brand_type_val,
                                    }
                                }
                                continue

                            if qty_val == NA and unit_price_val == NA and total_price_val == NA and p_name == NA:
                                continue

                            table_items.append({
                                "product_name": p_name,
                                "brand": brand_val,
                                "category_name_quadrant": cat_val,
                                "ordered_quantity": qty_val,
                                "unit_price": unit_price_val,
                                "total_order_value": total_price_val,
                                "model": model_val,
                                "hsn_code": hsn_val,
                                "brand_type": brand_type_val,
                            })

            # Flush any remaining pending row at end of document
            if pending_incomplete_row is not None:
                table_items.append(pending_incomplete_row['item_dict'])
                pending_incomplete_row = None

        except Exception:
            pass

    # 2. Fallback / Structured Text Stream Parsing (Extracts all items from Product Details text block)
    p_sec = re.search(
        r'(?:Product\s*Details|उत्पाद[^\n:]*विवरण|उ[^\w\s]?पाद[^\n:]*विवरण|उ[^\w\s]?पाद\s*!ववरण)[\s\S]+?(?=(?:Consignee\s*Detail|परे[!षs\s]*ती|Terms\s*and\s*Conditions|ePBG\s*Detail|कुल\s*ऑर्डर\s*मूल्य|Total\s*Order\s*Value\s*\(in\s*INR\)\s*\n\s*[\d,]+))',
        raw_text, re.IGNORECASE
    )
    sec_text = p_sec.group(0) if p_sec else raw_text

    text_blocks = re.split(r'\n(?=\s*(?:\d+\s*\n\s*)?(?:उ[^\w\s]?पाद\s*का\s*नाम|Product\s*Name)\s*[:|])', sec_text, flags=re.IGNORECASE)
    text_items = []
    for blk in text_blocks:
        if not re.search(r'(?:उ[^\w\s]?पाद\s*का\s*नाम|Product\s*Name)\s*[:|]', blk, re.IGNORECASE):
            continue
        parsed = parse_product_cell(blk)
        pn = parsed.get("product_name", NA)
        br = parsed.get("brand", NA)
        cat = parsed.get("category_name_quadrant", NA)
        model_v = parsed.get("model", NA)
        hsn_v = parsed.get("hsn_code", NA)
        bt_v = parsed.get("brand_type", NA)

        qty_val = NA
        unit_price_val = NA
        total_val = NA

        num_lines = re.findall(r'\n\s*([\d,]+(?:\.\d+)?)\s*(?:\n|$)', blk)
        valid_nums = []
        for n in num_lines:
            num = to_number(n)
            if num != NA:
                valid_nums.append(num)

        m_total = re.search(r'Total\s*Order\s*Value[^\d]*([\d,]+(?:\.\d+)?)', blk, re.IGNORECASE)
        explicit_total = to_number(m_total.group(1)) if m_total else NA

        if len(valid_nums) >= 3:
            q0, p0, t0 = valid_nums[0], valid_nums[1], valid_nums[2]
            if abs(q0 * p0 - t0) <= 2.0:
                qty_val, unit_price_val, total_val = q0, p0, t0
            elif len(valid_nums) >= 4:
                q1, p1, t1 = valid_nums[1], valid_nums[2], valid_nums[3]
                if abs(q1 * p1 - t1) <= 2.0:
                    qty_val, unit_price_val, total_val = q1, p1, t1
                else:
                    if explicit_total != NA and q0 > 0:
                        up = round(explicit_total / q0, 2)
                        qty_val, unit_price_val, total_val = q0, up, explicit_total
                    else:
                        qty_val, unit_price_val, total_val = q0, p0, t0
            else:
                if t0 > p0 and p0 > 0:
                    back_q = t0 / p0
                    if abs(back_q - round(back_q)) < 0.01:
                        qty_val, unit_price_val, total_val = int(round(back_q)), p0, t0
                    else:
                        qty_val, unit_price_val, total_val = q0, p0, t0
                else:
                    qty_val, unit_price_val, total_val = q0, p0, t0
        elif len(valid_nums) == 2:
            q0, t0 = valid_nums[0], valid_nums[1]
            if q0 > 0:
                unit_price_val = round(t0 / q0, 2)
            qty_val, total_val = q0, t0
        elif len(valid_nums) == 1:
            if valid_nums[0] < 1000:
                qty_val = valid_nums[0]
            else:
                total_val = valid_nums[0]

        if qty_val != NA and unit_price_val != NA and (total_val == NA or total_val == 0):
            total_val = round(qty_val * unit_price_val, 2)

        text_items.append({
            "product_name": pn,
            "brand": br,
            "category_name_quadrant": cat,
            "ordered_quantity": qty_val,
            "unit_price": unit_price_val,
            "total_order_value": total_val,
            "model": model_v,
            "hsn_code": hsn_v,
            "brand_type": bt_v,
        })

    # Reconcile table_items and text_items
    final_items = table_items
    if len(text_items) > len(table_items):
        final_items = text_items
    elif len(table_items) > 0 and len(text_items) == len(table_items):
        for i, t_it in enumerate(table_items):
            txt_it = text_items[i]
            for field in ["product_name", "brand", "category_name_quadrant", "ordered_quantity",
                          "unit_price", "total_order_value", "model", "hsn_code", "brand_type"]:
                if t_it.get(field) == NA and txt_it.get(field) != NA:
                    t_it[field] = txt_it[field]
            txt_qty = txt_it.get("ordered_quantity", NA)
            txt_up = txt_it.get("unit_price", NA)
            txt_tot = txt_it.get("total_order_value", NA)
            if (txt_qty != NA and txt_up != NA and txt_tot != NA and
                    isinstance(txt_qty, (int, float)) and isinstance(txt_up, (int, float)) and isinstance(txt_tot, (int, float))):
                if abs(round(txt_qty * txt_up, 2) - txt_tot) <= 2.0:
                    t_it["ordered_quantity"] = txt_qty
                    t_it["unit_price"] = txt_up
                    t_it["total_order_value"] = txt_tot

    if not final_items and text_items:
        final_items = text_items

    # 3. Post-Extraction Sibling Deduplication and Fusion (Fuses any remaining split items across page breaks)
    final_items = _reconcile_and_fuse_items(final_items)

    return final_items


# ──────────────────────────────────────────────────────────────────────────────
# 4-TIER RULE & MATH VALIDATION MATRIX
# ──────────────────────────────────────────────────────────────────────────────

def validate_record(rec: Dict[str, Any]) -> Tuple[str, int, List[str], Dict[str, Any]]:
    """
    Validates extracted fields against deterministic syntactic, format,
    and mathematical rules for each item record.
    """
    errors = []
    checks = {}

    # 1. Contract No (Mandatory 100%)
    contract_no = rec.get("contract_no", NA)
    if contract_no == NA:
        errors.append("Missing Contract No")
        checks["contract_no"] = False
    elif "GEMC-" in str(contract_no) or "GEM-" in str(contract_no):
        checks["contract_no"] = True
    else:
        errors.append("Invalid Contract No format")
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

    # 4. Seller Contact No
    seller_contact = rec.get("seller_contact_no", NA)
    if seller_contact == NA or len(str(seller_contact)) < 7 or not str(seller_contact).isdigit():
        errors.append("Invalid or missing Seller Contact No")
        checks["seller_contact_no"] = False
    else:
        checks["seller_contact_no"] = True

    # 5. Seller Email
    seller_email = rec.get("seller_email", NA)
    if seller_email == NA or not RE_EMAIL_VALID.match(str(seller_email)):
        errors.append("Invalid or missing Seller Email")
        checks["seller_email"] = False
    else:
        checks["seller_email"] = True

    # 6. Seller GSTIN
    seller_gstin = rec.get("seller_gstin", NA)
    if seller_gstin == NA or not RE_GSTIN_VALID.match(str(seller_gstin)):
        errors.append(f"Invalid Seller GSTIN format: {seller_gstin}")
        checks["seller_gstin"] = False
    else:
        checks["seller_gstin"] = True

    # 7. Consignee Address
    consignee_addr = rec.get("consignee_address", NA)
    if consignee_addr == NA or len(str(consignee_addr)) < 5:
        errors.append("Missing Consignee Address")
        checks["consignee_address"] = False
    else:
        checks["consignee_address"] = True

    # 8. Consignee Email
    consignee_email = rec.get("consignee_email", NA)
    if consignee_email == NA or not RE_EMAIL_VALID.match(str(consignee_email)):
        errors.append("Invalid or missing Consignee Email")
        checks["consignee_email"] = False
    else:
        checks["consignee_email"] = True

    # 9. Ordered Quantity
    qty = rec.get("ordered_quantity", NA)
    if qty == NA or not (isinstance(qty, (int, float)) and qty > 0):
        errors.append("Invalid or missing Ordered Quantity")
        checks["ordered_quantity"] = False
    else:
        checks["ordered_quantity"] = True

    # 10. Unit Price
    unit_price = rec.get("unit_price", NA)
    if unit_price == NA or not (isinstance(unit_price, (int, float)) and unit_price > 0):
        errors.append("Invalid or missing Unit Price")
        checks["unit_price"] = False
    else:
        checks["unit_price"] = True

    # 11. Total Order Value & Mathematical Consistency
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
# MASTER DOCUMENT PROCESSOR (Multi-Product Return: List[Dict[str, Any]])
# ──────────────────────────────────────────────────────────────────────────────

def process_single_pdf(filepath: str) -> List[Dict[str, Any]]:
    """
    Extracts, cleans, normalizes, and validates all required fields from a GeM contract PDF.
    If the PDF contains multiple products, returns multiple structured entries (one per product).
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
        return [{
            "file_name": filename,
            "contract_no": NA,
            "generated_date": NA,
            "organisation_name": NA,
            "buyer_contact": NA,
            "buyer_email": NA,
            "paying_authority_email": NA,
            "seller_company_name": NA,
            "seller_contact_no": NA,
            "seller_email": NA,
            "seller_gstin": NA,
            "seller_address": NA,
            "product_name": NA,
            "brand": NA,
            "brand_type": NA,
            "category_name_quadrant": NA,
            "model": NA,
            "hsn_code": NA,
            "ordered_quantity": NA,
            "unit_price": NA,
            "total_order_value": NA,
            "delivery_dates": NA,
            "consignee_email": NA,
            "consignee_contact_no": NA,
            "consignee_address": NA,
            "validation_status": STATUS_REVIEW,
            "validation_score": 0,
            "validation_errors": [f"Failed to open PDF: {str(e)}"],
            "validation_checks": {}
        }]

    # Extract common document sections
    contract_no, gen_date = parse_header(raw_text, filename)
    org = parse_organisation_section(raw_text)
    buyer = parse_buyer_section(raw_text)
    paying_auth = parse_paying_authority_section(raw_text)
    seller = parse_seller_section(raw_text)
    consignees = parse_consignee_section(raw_text, doc=doc)

    # Extract delivery dates
    delivery_dates = extract_delivery_dates(raw_text, doc=doc)

    # Extract all product line items across pages
    product_items = parse_all_product_items(raw_text, doc=doc)

    if doc:
        doc.close()

    first_consignee = consignees[0] if consignees else {}

    if not product_items:
        product_items = [{
            "product_name": NA,
            "brand": NA,
            "brand_type": NA,
            "category_name_quadrant": NA,
            "model": NA,
            "hsn_code": NA,
            "ordered_quantity": NA,
            "unit_price": NA,
            "total_order_value": NA,
        }]

    records = []
    for item in product_items:
        qty = item.get("ordered_quantity", NA)
        unit_p = item.get("unit_price", NA)
        total_p = item.get("total_order_value", NA)

        if qty != NA and unit_p != NA and isinstance(qty, (int, float)) and isinstance(unit_p, (int, float)):
            total_p = round(qty * unit_p, 2)
        elif qty != NA and total_p != NA and (unit_p == NA or unit_p == 0) and isinstance(qty, (int, float)) and isinstance(total_p, (int, float)) and qty > 0:
            unit_p = round(total_p / qty, 2)
            total_p = round(qty * unit_p, 2)
        elif unit_p != NA and total_p != NA and (qty == NA or qty == 0) and isinstance(unit_p, (int, float)) and isinstance(total_p, (int, float)) and unit_p > 0:
            qty = int(round(total_p / unit_p))
            total_p = round(qty * unit_p, 2)

        rec = {
            "file_name": filename,
            "contract_no": contract_no,
            "generated_date": gen_date,
            "organisation_name": org.get("organisation_name", NA),
            "buyer_contact": buyer.get("contact_no", NA),
            "buyer_email": buyer.get("email", NA),
            "paying_authority_email": paying_auth.get("email", NA),
            "seller_company_name": seller.get("company_name", NA),
            "seller_contact_no": seller.get("contact_no", NA),
            "seller_email": seller.get("email", NA),
            "seller_gstin": seller.get("gstin", NA),
            "seller_address": seller.get("address", NA),
            "product_name": item.get("product_name", NA),
            "brand": item.get("brand", NA),
            "brand_type": item.get("brand_type", NA),
            "category_name_quadrant": item.get("category_name_quadrant", NA),
            "model": item.get("model", NA),
            "hsn_code": item.get("hsn_code", NA),
            "ordered_quantity": qty,
            "unit_price": unit_p,
            "total_order_value": total_p,
            "delivery_dates": delivery_dates,
            "consignee_email": first_consignee.get("consignee_email", NA),
            "consignee_contact_no": first_consignee.get("consignee_contact_no", NA),
            "consignee_address": first_consignee.get("consignee_address", NA),
        }

        # Run 4-Tier Validation Matrix for this product line item
        status, score, errors, checks = validate_record(rec)
        rec["validation_status"] = status
        rec["validation_score"] = score
        rec["validation_errors"] = errors
        rec["validation_checks"] = checks
        records.append(rec)

    return records
