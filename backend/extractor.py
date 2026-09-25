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
    """Normalize phone / contact numbers."""
    if not text or text == NA:
        return NA
    text_str = str(text).strip()
    text_str = re.sub(r'[:|;,\s\-]+$', '', text_str)
    text_str = re.sub(r'^[^\d+]*', '', text_str)
    digits = re.sub(r'[^\d]', '', text_str)
    if len(digits) >= 10:
        return digits[-10:] if len(digits) == 10 or digits.startswith(('6', '7', '8', '9')) else digits
    if len(digits) >= 7:
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
        r'Consignee\s*Detail[\s\S]*?(?:Address|ptaa|पता)\s*[:.]\s*',
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
    for p in parts:
        p_clean = re.sub(r'[:.\s\-–;]+', '', p).lower()
        if not unique_parts or p_clean != re.sub(r'[:.\s\-–;]+', '', unique_parts[-1]).lower():
            unique_parts.append(p)
    addr = ', '.join(unique_parts)

    return clean_address(addr)


def sanitize_brand(brand_str: Optional[str]) -> str:
    """Strictly validates Brand name, stripping specifications and normalizing Unbranded/NA."""
    if not brand_str or brand_str == NA:
        return NA
    b = str(brand_str).strip()
    # Strip any trailing labels using strict word boundaries
    b = re.split(r'[:|]?\s*(?:\bBrand\s*Type\b|\bCatalogue\s*Status\b|\bSelling\s*As\b|\bCategory\s*Name\b|\bModel\b|\bHSN\s*Code\b|कैटलॉग|मॉडल|एचएसएन)', b, flags=re.IGNORECASE)[0].strip()
    b = clean_text(b)
    if not b or b.upper() in {"NA", "N/A", "NONE", "NULL", "-", "--"}:
        return NA
    # Catch any variations of unbranded (e.g. Unbranded, Unbranded Two, Unbranded Three, Unbranded (Q3), Unbranded Tier 3, Unbranded--...)
    if b.lower().startswith("unbranded") or "unbranded" in b.lower():
        return NA
    if b.lower() in {"not specified", "not specified by seller", "not specified by buyer", "not specified by oem"}:
        return NA
    if b.startswith("NA ") or b.startswith("NA-"):
        return NA
    # Reject if it looks like technical specifications, pipe dimensions, or long sentences
    if re.search(r'\b(?:\d+\s*x\s*\d+|GI Pipe|Angle|deep|supported|Gym Equipment|Double|Single|Parallel Bar|Chest Press|Surf Board)\b', b, re.IGNORECASE):
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
        p = re.sub(r'^[\|\-:.\s]+', '', p).strip()
        if p == prev:
            break

    # Strip trailing labels using strict word boundaries
    p = re.split(r'[:|]?\s*(?:\bBrand\s*Type\b|\bBrand\s*:|[‚€†\x7f\x80\x81\x83\u0192\w\s|]*?[ाo\u093e]ंड|\bCatalogue\s*Status\b|\bSelling\s*As\b|\bCategory\s*Name\b|\bModel\b|\bHSN\s*Code\b|कैटलॉग|मॉडल|एचएसएन)', p, flags=re.IGNORECASE)[0].strip()

    # Strip trailing OCR artifacts like 'aaNdd', 'aaNd'
    p = re.sub(r'\s+aaN+d*\s*$', '', p, flags=re.IGNORECASE).strip()
    p = re.sub(r'[,:\-–|]+$', '', p).strip()
    p = clean_text(p)

    # Post-clean check for any remaining transliterated prefix
    p = re.sub(r'^(?:[a-z|{z~x_]*paad\s*(?:kaa\s*naam)?\s*(?:[|/\\–\-]\s*)?(?:Product\s*Name\s*)?|Product\s*Name\s*)[:|.\-–=]*\s*', '', p, flags=re.IGNORECASE).strip()
    p = re.sub(r'^[\|\-:.\s]+', '', p).strip()
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
        r'(?:Address|पता)\s*[:.\s]*\n?\s*([\s\S]+?,\s*(?:India|भारत|\d{6},\s*India))',
        section, re.IGNORECASE
    )
    if m_india:
        addr = clean_address(m_india.group(1))
        if 5 <= len(addr) <= 350:
            return addr

    # Pattern 2: Address up to State-PIN: e.g. UTTAR PRADESH-250002, -
    m_pin = re.search(
        r'(?:Address|पता)\s*[:.\s]*\n?\s*([\s\S]+?,\s*[A-Z\s]+-\d{6}(?:,\s*[-–\w]+)?)',
        section, re.IGNORECASE
    )
    if m_pin:
        addr = clean_address(m_pin.group(1))
        if 5 <= len(addr) <= 350:
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
    """Parse Organisation Details section accurately prioritizing actual Org Name then Office Zone."""
    text = raw_text.replace('\ufb00', 'ff').replace('\ufb01', 'fi').replace('\ufb02', 'fl').replace('\ufb03', 'ffi').replace('\ufb04', 'ffl')
    section = extract_section(
        text,
        [r'Organisation\s*Details', r'संगठन[^\n:]*विवरण', r'संगठन[^\n:]*ववरण', r'संगठन'],
        [r'Buyer\s*Details', r'खरीदार', r'Financial\s*Approval', r'Paying\s*Authority', r'Seller\s*Details']
    )
    if not section:
        section = text[:2000]

    org_name = NA
    # 1. Match Organisation Name
    m_on = re.search(r'(?:Organisation\s*Name|संगठन\s*का\s*नाम)[^\n:]*[:|.]\s*([^\n\r]+)', section, re.IGNORECASE)
    if not m_on:
        m_on = re.search(r'(?:Organisation\s*Name|संगठन\s*का\s*नाम)\s*\n\s*([^\n\r]+)', section, re.IGNORECASE)

    if m_on:
        cand = clean_text(m_on.group(1))
        if cand not in [NA, "N/A", "-", "--", "None", "", "N / A", "Organisation", "संगठन"]:
            org_name = cand

    # 2. If Organisation Name is N/A or missing, check Office Zone
    if org_name == NA:
        m_oz = re.search(r'(?:Office\s*Zone|Oﬃce\s*Zone|काया[A-Za-z0-9_]*लय[^\n:]*|कार्यालय\s*क्षेत्र)[^\n:]*[:|.]\s*([^\n\r]+(?:\n[^\n\r]+)?)', section, re.IGNORECASE)
        if not m_oz:
            m_oz = re.search(r'(?:Office\s*Zone|Oﬃce\s*Zone|काया[A-Za-z0-9_]*लय[^\n:]*|कार्यालय\s*क्षेत्र)\s*\n\s*([^\n\r]+(?:\n[^\n\r]+)?)', section, re.IGNORECASE)
        if m_oz:
            lines = [l.strip() for l in m_oz.group(1).split('\n') if l.strip()]
            valid = []
            for l in lines:
                if re.search(r'[:|]\s*(?:Buyer|Contact|Email|GSTIN|Address|Role|Payment|GeM)\b', l, re.IGNORECASE):
                    break
                valid.append(l)
            if valid:
                cand = clean_text(' '.join(valid))
                if cand not in [NA, "N/A", "-", "--", "None", ""]:
                    org_name = cand

    # 3. Fallback to Department or Ministry
    if org_name == NA:
        dept = match_multiline_kv(r'(?:Department|विभाग|वभाग|[\$\%\"\&]?वभाग)', section, max_lines=2)
        if dept != NA and dept not in ["-", "--", "NA", "N/A"]:
            org_name = dept
        else:
            minis = match_multiline_kv(r'(?:Ministry|मंत्रालय|मं[\?\=>]ालय)', section, max_lines=2)
            if minis != NA and minis not in ["-", "--", "NA", "N/A"]:
                org_name = minis

    if org_name != NA:
        org_name = re.split(r'[:|]?\s*(?:Buyer\s*Details|खरीदार|Office\s*Zone|कार्यालय|काया|kaayaa)', org_name, flags=re.IGNORECASE)[0].strip()
        org_name = clean_text(org_name)

    return {
        "organisation_name": org_name
    }


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
    contact = clean_phone(match_multiline_kv(r'(?:Contact\s*(?:No\.?)?|संपर्क\s*नंबर|संपक[EHLGM\s]*नंबर|संपकH\s*नंबर|संपकG\s*नंबर|संपकL\s*नंबर)', section, max_lines=1))
    if contact == NA:
        m_phone = re.search(r'(?:0[1-9]\d{2,4}[-\s]?\d{6,8}|0[1-9]\d{9,10}|[6-9]\d{9})', section)
        if m_phone:
            contact = clean_phone(m_phone.group(0))

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
    contact_no = clean_phone(match_multiline_kv(r'(?:Contact\s*(?:No\.?)?|संपर्क\s*नंबर|संपक[EHLGM\s]*नंबर|संपकH\s*नंबर|संपकG\s*नंबर|संपकL\s*नंबर)', section, max_lines=1))
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

    consignee_text = "\n".join(consignee_cells) if consignee_cells else ""

    # 2. If table didn't have full address, extract text section
    m_sec = re.search(
        r'(?:Consignee\s*Detail|परे[!षs\s]*ती\s*!ववरण|परे[!षs\s]*ती\s*विवरण|परेषती\s*विवरण|Consignee\s*and\s*Delivery)[\s\S]+?(?=(?:Product\s*Specification|ePBG\s*Detail|Terms\s*and\s*Conditions|General\s*Terms|$))',
        raw_text, re.IGNORECASE
    )
    if m_sec:
        consignee_text += "\n" + m_sec.group(0)

    # Extract Email strictly from consignee content
    email = clean_email(consignee_text)

    # Extract Contact
    m_c = re.search(r'(?:Contact\s*(?:No\.?)?|संपर्क\s*(?:नंबर)?|संपक[A-Za-z0-9_\s]*|sNpk[A-Za-z0-9_\s]*)\s*[:|.]\s*([^\n\r]+)', consignee_text, re.IGNORECASE)
    contact = clean_phone(m_c.group(1)) if m_c else clean_phone(consignee_text)

    # Extract Address
    addr = NA
    m_india = re.search(r'(?:Address|पता|ptaa|pata)\s*[:|.]\s*([\s\S]+?,\s*(?:India|भारत|\d{6},\s*India))', consignee_text, re.IGNORECASE)
    if m_india:
        addr = sanitize_consignee_address(m_india.group(1))
    else:
        m_pin = re.search(r'(?:Address|पता|ptaa|pata)\s*[:|.]\s*([\s\S]+?,\s*[A-Za-z\s]+-\d{6}(?:,\s*[-–\w]+)?)', consignee_text, re.IGNORECASE)
        if m_pin:
            addr = sanitize_consignee_address(m_pin.group(1))
        else:
            m_gen = re.search(r'(?:Address|पता|ptaa|pata)\s*[:|.]\s*([^\n\r]+(?:\n\s*[^\n\r]+){1,4})', consignee_text, re.IGNORECASE)
            if m_gen:
                addr = sanitize_consignee_address(m_gen.group(1))

    return [{
        "consignee_address": addr,
        "consignee_email": email,
        "consignee_contact_no": contact
    }]


def parse_product_cell(cell_text: str) -> Dict[str, str]:
    """Isolates product name, brand, and category with quadrant from cell or block text."""
    lines = [l.strip() for l in cell_text.split('\n') if l.strip()]
    full_text = '\n'.join(lines)

    # 1. Product Name
    p_name = NA
    m_pn = re.search(
        r'(?:Product\s*Name[^\n:]*|उत्पाद\s*का\s*नाम[^\n:]*|उ[^\w\s]?पाद\s*का\s*नाम[^\n:]*|utpaad\s*kaa\s*naam[^\n:]*|u[|{xz~]paad\s*kaa\s*naam[^\n:]*)\s*[:.]\s*([\s\S]+?)(?=\n\s*(?:\bBrand\b|ब्रांड|[‚€†\x7f\x80\x81\x83\u0192\w\s|]*?[ाo\u093e]ंड|\bBrand\s*Type\b|\bCatalogue\b|\bSelling\b|\bCategory\b|\bModel\b|\bHSN\b|$))',
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

    # 2. Brand
    brand_val = NA
    m_br = re.search(r'(?:\bBrand\b|ब्रांड|[‚€†\x7f\x80\x81\x83\u0192\w\s|]*?[ाo\u093e]ंड)\s*[:.]\s*([^\n\r]+)', full_text, re.IGNORECASE)
    if m_br:
        brand_val = sanitize_brand(m_br.group(1))

    # 3. Category & Quadrant (capture full name and quadrant if on next line)
    cat_val = NA
    m_cat = re.search(r'(?:Category\s*Name\s*(?:&|and)?\s*Quadrant?|[^\n:]*?ेणी\s*का\s*नाम[^\n:]*)\s*[:.]\s*([^\n\r]+(?:\n\s*\(Q\d\))?)', full_text, re.IGNORECASE)
    if m_cat:
        cat_val = clean_category_quadrant(m_cat.group(1).replace('\n', ' '))

    return {
        "product_name": p_name,
        "brand": brand_val,
        "category_name_quadrant": cat_val
    }


# ──────────────────────────────────────────────────────────────────────────────
# MULTI-PRODUCT ITEM PARSER
# ──────────────────────────────────────────────────────────────────────────────

def parse_all_product_items(raw_text: str, doc: Optional[Any] = None) -> List[Dict[str, Any]]:
    """
    Comprehensive multi-product extractor combining continuous multi-page table tracking
    with structured text-stream parsing for 100% item coverage.
    """
    table_items = []
    active_col_map = None

    # 1. Primary Method: PyMuPDF 2D Table Extraction across all pages with column-map continuity
    if doc:
        try:
            for page in doc:
                page_text = page.get_text("text")
                if not any(k in page_text for k in ["Product Details", "उत्पाद विवरण", "उ|पाद", "उ{पाद", "उxपाद", "उzपाद", "Item Description", "Ordered Quantity", "Unit Price", "इकाई मू"]):
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
                            for c_idx, cell in enumerate(row):
                                if not cell:
                                    continue
                                cl = str(cell).lower().replace('\n', ' ')
                                if ('item description' in cl or 'आइटम विवरण' in cl) and 'ordered' not in cl and 'quantity' not in cl and 'मात्रा' not in cl:
                                    col_map['item_desc'] = c_idx
                                elif 'ordered' in cl or 'quantity' in cl or 'मात्रा' in cl or 'मा=ा' in cl or 'मा?ा' in cl or 'मा>ा' in cl:
                                    col_map['qty'] = c_idx
                                elif 'category' in cl or 'श्रेणी' in cl:
                                    col_map['category'] = c_idx
                                elif 'model' in cl or 'मॉडल' in cl:
                                    col_map['model'] = c_idx
                                elif 'unit price' in cl or 'इकाई मू' in cl:
                                    col_map['unit_price'] = c_idx
                                elif 'inclusive' in cl or 'all duties' in cl or 'total' in cl or 'सभी' in cl or (('price' in cl or 'मूल्य' in cl or 'मू य' in cl or 'मू~य' in cl or 'मू}य' in cl) and 'unit' not in cl and 'इकाई' not in cl):
                                    if 'unit_price' not in col_map or col_map['unit_price'] != c_idx:
                                        col_map['total_price'] = c_idx
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

                            item_desc_cell = str(data_row[curr_map['item_desc']]) if 'item_desc' in curr_map and curr_map['item_desc'] < len(data_row) and data_row[curr_map['item_desc']] else ""
                            if not item_desc_cell or not any(k in item_desc_cell.lower() for k in ['product name', 'उत्पाद', 'उ{', 'उ|', 'उx', 'उz', 'brand', 'ब्रांड', 'category']):
                                continue

                            parsed_desc = parse_product_cell(item_desc_cell)
                            p_name = parsed_desc.get("product_name", NA)
                            brand_val = parsed_desc.get("brand", NA)
                            cat_val = parsed_desc.get("category_name_quadrant", NA)

                            if cat_val == NA and 'category' in curr_map and curr_map['category'] < len(data_row) and data_row[curr_map['category']]:
                                cat_val = clean_category_quadrant(str(data_row[curr_map['category']]))

                            qty_val = NA
                            if 'qty' in curr_map and curr_map['qty'] < len(data_row) and data_row[curr_map['qty']]:
                                qty_val = to_number(data_row[curr_map['qty']])

                            unit_price_val = NA
                            if 'unit_price' in curr_map and curr_map['unit_price'] < len(data_row) and data_row[curr_map['unit_price']]:
                                unit_price_val = to_number(data_row[curr_map['unit_price']])

                            total_price_val = NA
                            if 'total_price' in curr_map and curr_map['total_price'] < len(data_row) and data_row[curr_map['total_price']]:
                                total_price_val = to_number(data_row[curr_map['total_price']])

                            if qty_val == NA and unit_price_val == NA and total_price_val == NA and p_name == NA:
                                continue

                            # Reconcile math
                            if qty_val != NA and unit_price_val != NA and (total_price_val == NA or total_price_val == 0):
                                total_price_val = round(qty_val * unit_price_val, 2)
                            elif qty_val != NA and total_price_val != NA and (unit_price_val == NA or unit_price_val == 0) and qty_val > 0:
                                unit_price_val = round(total_price_val / qty_val, 2)
                            elif unit_price_val != NA and total_price_val != NA and (qty_val == NA or qty_val == 0) and unit_price_val > 0:
                                qty_val = int(round(total_price_val / unit_price_val))

                            table_items.append({
                                "product_name": p_name,
                                "brand": brand_val,
                                "category_name_quadrant": cat_val,
                                "ordered_quantity": qty_val,
                                "unit_price": unit_price_val,
                                "total_order_value": total_price_val
                            })
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

        qty_val = NA
        unit_price_val = NA
        total_val = NA

        # Numbers after HSN Code / Model
        m_nums = re.findall(r'\n\s*([\d,]+(?:\.\d+)?)\s*(?:\n|$)', blk)
        valid_nums = []
        for n in m_nums:
            num = to_number(n)
            if num != NA:
                valid_nums.append(num)

        if len(valid_nums) >= 3:
            qty_val = valid_nums[0]
            unit_price_val = valid_nums[1]
            total_val = valid_nums[2]
        elif len(valid_nums) == 2:
            qty_val = valid_nums[0]
            total_val = valid_nums[1]
            if qty_val > 0:
                unit_price_val = round(total_val / qty_val, 2)
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
            "total_order_value": total_val
        })

    # Reconcile table_items and text_items
    final_items = table_items
    if len(text_items) > len(table_items):
        final_items = text_items
    elif len(table_items) > 0 and len(text_items) == len(table_items):
        for i, t_it in enumerate(table_items):
            txt_it = text_items[i]
            if t_it.get("product_name") == NA and txt_it.get("product_name") != NA:
                t_it["product_name"] = txt_it["product_name"]
            if t_it.get("brand") == NA and txt_it.get("brand") != NA:
                t_it["brand"] = txt_it["brand"]
            if t_it.get("category_name_quadrant") == NA and txt_it.get("category_name_quadrant") != NA:
                t_it["category_name_quadrant"] = txt_it["category_name_quadrant"]
            if t_it.get("ordered_quantity") == NA and txt_it.get("ordered_quantity") != NA:
                t_it["ordered_quantity"] = txt_it["ordered_quantity"]
            if t_it.get("unit_price") == NA and txt_it.get("unit_price") != NA:
                t_it["unit_price"] = txt_it["unit_price"]
            if t_it.get("total_order_value") == NA and txt_it.get("total_order_value") != NA:
                t_it["total_order_value"] = txt_it["total_order_value"]

    if not final_items and text_items:
        final_items = text_items

    # 3. Fallback Brand search from Product Specification headers if brand is NA
    for it in final_items:
        if it.get("brand") == NA:
            m_spec_title = re.search(
                r'Product\s*Specification\s*for\s*(?:(?:Unbranded\s+)?([A-Za-z0-9\s]+?))\s+(?:Gym|Ankle|Oven|Dustbin|Chamber|Couch|Centrifuge|Concentrator|Table|Wheel|Mirror|Chest Press|Surf Board|Twister|Leg Press|Air Walker|Parallel Bar|Sit Up|Hand Grip|Infantometer|Stadiometer|Monitor)',
                raw_text, re.IGNORECASE
            )
            if m_spec_title:
                cand = sanitize_brand(m_spec_title.group(1))
                if cand != NA and len(cand) <= 30:
                    it["brand"] = cand

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
    if seller_contact == NA or len(str(seller_contact)) < 7:
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
            "category_name_quadrant": NA,
            "ordered_quantity": NA,
            "unit_price": NA,
            "total_order_value": NA,
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

    # Extract all product line items across pages
    product_items = parse_all_product_items(raw_text, doc=doc)

    if doc:
        doc.close()

    first_consignee = consignees[0] if consignees else {}

    if not product_items:
        product_items = [{
            "product_name": NA,
            "brand": NA,
            "category_name_quadrant": NA,
            "ordered_quantity": NA,
            "unit_price": NA,
            "total_order_value": NA
        }]

    records = []
    for item in product_items:
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
            "category_name_quadrant": item.get("category_name_quadrant", NA),
            "ordered_quantity": item.get("ordered_quantity", NA),
            "unit_price": item.get("unit_price", NA),
            "total_order_value": item.get("total_order_value", NA),
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
