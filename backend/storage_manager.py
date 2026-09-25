"""
storage_manager.py — Excel & JSON Multi-Batch Append & Storage Engine
====================================================================
Manages saving, updating, and appending extracted contract records into:
  1. output/gem_contracts.xlsx (Formatted, styled master sheet)
  2. output/gem_contracts.json (Structured JSON array)
  3. output/records.jsonl (Append-friendly line-by-line log)

Handles multi-batch execution seamlessly without overwriting existing data.
Resilient against Windows Excel file locks.
"""

import os
import json
import time
from typing import List, Dict, Any, Tuple
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


EXCEL_FILENAME = "gem_contracts.xlsx"
JSON_FILENAME = "gem_contracts.json"
JSONL_FILENAME = "records.jsonl"
BATCH_EXCEL_FILENAME = "gem_contracts_batch.xlsx"
BATCH_JSON_FILENAME = "current_batch.json"
DEFAULT_OUTPUT_DIR = "output"

# Styles
HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
HEADER_BORDER = Border(
    left=Side(style="thin", color="3A5A80"),
    right=Side(style="thin", color="3A5A80"),
    top=Side(style="medium", color="16365C"),
    bottom=Side(style="medium", color="16365C"),
)

PASS_FILL = PatternFill(start_color="E2F0D9", end_color="E2F0D9", fill_type="solid")
PASS_FONT = Font(name="Calibri", size=10, bold=True, color="385723")

REVIEW_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
REVIEW_FONT = Font(name="Calibri", size=10, bold=True, color="B25900")

EVEN_FILL = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
ODD_FILL = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

CELL_FONT = Font(name="Calibri", size=10)
EMAIL_FONT = Font(name="Calibri", size=10, color="0563C1", underline="single")
CELL_ALIGN_LEFT = Alignment(horizontal="left", vertical="center")
CELL_ALIGN_RIGHT = Alignment(horizontal="right", vertical="center")
CELL_ALIGN_CENTER = Alignment(horizontal="center", vertical="center")

THIN_BORDER = Border(
    left=Side(style="thin", color="E0E0E0"),
    right=Side(style="thin", color="E0E0E0"),
    top=Side(style="thin", color="E0E0E0"),
    bottom=Side(style="thin", color="E0E0E0"),
)


# 1. Server Master Columns (Retains Validation Status and Validation Score for internal audit)
MASTER_COLUMNS = [
    ("S.No", "s_no", 8),
    ("Validation Status", "validation_status", 16),
    ("Validation Score (%)", "validation_score", 18),
    ("Contract No", "contract_no", 28),
    ("Generated Date", "generated_date", 16),
    ("Organisation Name", "organisation_name", 30),
    ("Buyer Contact", "buyer_contact", 18),
    ("Buyer Email", "buyer_email", 30),
    ("Paying Authority Email", "paying_authority_email", 30),
    ("Seller Company Name", "seller_company_name", 30),
    ("Seller Contact No", "seller_contact_no", 18),
    ("Seller Email", "seller_email", 30),
    ("Seller GSTIN", "seller_gstin", 20),
    ("Seller Address", "seller_address", 40),
    ("Products Name", "product_name", 35),
    ("Brand", "brand", 22),
    ("Category & Quadrant", "category_name_quadrant", 35),
    ("Ordered Quantity", "ordered_quantity", 18),
    ("Unit Price (INR)", "unit_price", 18),
    ("Total Order Value (INR)", "total_order_value", 24),
    ("Consignee Email", "consignee_email", 30),
    ("Consignee Contact", "consignee_contact_no", 20),
    ("Consignee Address", "consignee_address", 40),
    ("File Name", "file_name", 35),
]

# 2. User Output Columns (22 columns strictly matching Final output.xlsx)
USER_OUTPUT_COLUMNS = [
    ("S.No", "s_no", 8),
    ("Contract No", "contract_no", 28),
    ("Generated Date", "generated_date", 16),
    ("Organisation Name", "organisation_name", 30),
    ("Buyer Contact", "buyer_contact", 18),
    ("Buyer Email", "buyer_email", 30),
    ("Paying Authority Email", "paying_authority_email", 30),
    ("Seller Company Name", "seller_company_name", 30),
    ("Seller Contact No", "seller_contact_no", 18),
    ("Seller Email", "seller_email", 30),
    ("Seller GSTIN", "seller_gstin", 20),
    ("Seller Address", "seller_address", 40),
    ("Products Name", "product_name", 35),
    ("Brand", "brand", 22),
    ("Category & Quadrant", "category_name_quadrant", 35),
    ("Ordered Quantity", "ordered_quantity", 18),
    ("Unit Price (INR)", "unit_price", 18),
    ("Total Order Value (INR)", "total_order_value", 24),
    ("Consignee Email", "consignee_email", 30),
    ("Consignee Contact", "consignee_contact_no", 20),
    ("Consignee Address", "consignee_address", 40),
    ("File Name", "file_name", 35),
]

# Compatibility alias
COLUMNS = MASTER_COLUMNS


def ensure_output_dir(output_dir: str = DEFAULT_OUTPUT_DIR) -> str:
    """Ensure output directory exists."""
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def load_existing_json(output_dir: str = DEFAULT_OUTPUT_DIR) -> List[Dict[str, Any]]:
    """Load existing records from gem_contracts.json if present."""
    json_path = os.path.join(output_dir, JSON_FILENAME)
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []


def load_batch_json(output_dir: str = DEFAULT_OUTPUT_DIR) -> List[Dict[str, Any]]:
    """Load records for only the current batch."""
    batch_json_path = os.path.join(output_dir, BATCH_JSON_FILENAME)
    if os.path.exists(batch_json_path):
        try:
            with open(batch_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []


def clear_batch_json(output_dir: str = DEFAULT_OUTPUT_DIR) -> None:
    """Clears current batch JSON and output files."""
    for fname in [BATCH_JSON_FILENAME, JSON_FILENAME, JSONL_FILENAME, BATCH_EXCEL_FILENAME]:
        p = os.path.join(output_dir, fname)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass


import hashlib


def get_record_signature(r: Dict[str, Any]) -> str:
    """
    Computes a deterministic content signature based on the actual extracted data fields.
    If file names are the same but columns/data are different, signatures will differ.
    """
    fields = [
        str(r.get("contract_no", "")).strip(),
        str(r.get("generated_date", "")).strip(),
        str(r.get("organisation_name", "")).strip(),
        str(r.get("buyer_contact", "")).strip(),
        str(r.get("buyer_email", "")).strip(),
        str(r.get("paying_authority_email", "")).strip(),
        str(r.get("seller_company_name", "")).strip(),
        str(r.get("seller_contact_no", "")).strip(),
        str(r.get("seller_email", "")).strip(),
        str(r.get("seller_gstin", "")).strip(),
        str(r.get("seller_address", "")).strip(),
        str(r.get("product_name", "")).strip(),
        str(r.get("brand", "")).strip(),
        str(r.get("category_name_quadrant", "")).strip(),
        str(r.get("ordered_quantity", "")).strip(),
        str(r.get("unit_price", "")).strip(),
        str(r.get("total_order_value", "")).strip(),
        str(r.get("consignee_email", "")).strip(),
        str(r.get("consignee_contact_no", "")).strip(),
        str(r.get("consignee_address", "")).strip(),
        str(r.get("file_name", "")).strip(),
    ]
    raw_str = "||".join(fields)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


def save_batch_records(batch_records: List[Dict[str, Any]], output_dir: str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    """
    Saves batch records strictly for the current batch:
    1. Saves output/current_batch.json & output/gem_contracts.json (batch data for UI display)
    2. Generates output/gem_contracts_batch.xlsx & output/gem_contracts.xlsx containing ONLY this batch's records (fresh Excel, no mixing with past batches)
    3. Generates output/records.jsonl for current batch
    """
    ensure_output_dir(output_dir)

    # 1. Save Batch JSON & master JSON (always fresh for this batch)
    batch_json_path = os.path.join(output_dir, BATCH_JSON_FILENAME)
    master_json_path = os.path.join(output_dir, JSON_FILENAME)
    jsonl_path = os.path.join(output_dir, JSONL_FILENAME)

    try:
        with open(batch_json_path, 'w', encoding='utf-8') as f:
            json.dump(batch_records, f, indent=2, ensure_ascii=False)
        with open(master_json_path, 'w', encoding='utf-8') as f:
            json.dump(batch_records, f, indent=2, ensure_ascii=False)
        with open(jsonl_path, 'w', encoding='utf-8') as f:
            for r in batch_records:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"Error saving batch JSON: {e}")

    # 2. Save User Output Batch Excel & Master Excel (fresh workbook with only this batch's records)
    batch_excel_path = os.path.join(output_dir, BATCH_EXCEL_FILENAME)
    master_excel_path = os.path.join(output_dir, EXCEL_FILENAME)
    try:
        write_styled_excel(batch_records, batch_excel_path, is_master=False)
        write_styled_excel(batch_records, master_excel_path, is_master=False)
    except Exception as e:
        print(f"Error saving batch Excel: {e}")

    return {
        "batch_count": len(batch_records),
        "batch_json": batch_json_path,
        "batch_excel": batch_excel_path,
        "master_total": len(batch_records)
    }


def save_and_append_records(new_records: List[Dict[str, Any]], output_dir: str = DEFAULT_OUTPUT_DIR, reprocess_all: bool = False) -> Dict[str, Any]:
    """
    Saves records fresh for the current batch without appending old batches.
    """
    return save_batch_records(new_records, output_dir)


def write_styled_excel(records: List[Dict[str, Any]], excel_path: str, is_master: bool = False) -> str:
    """
    Generates an aesthetic, professionally styled Excel file with file lock handling.
    - If is_master=True: includes Validation Status and Validation Score (%) for server master audit.
    - If is_master=False: excludes validation columns for clean client-facing output.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "GeM_Contracts_Master" if is_master else "GeM_Contracts"

    columns = MASTER_COLUMNS if is_master else USER_OUTPUT_COLUMNS

    ws.row_dimensions[1].height = 28

    for col_idx, (col_title, _, width) in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_title)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = HEADER_ALIGN
        cell.border = HEADER_BORDER
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = width

    for row_idx, r in enumerate(records, start=2):
        ws.row_dimensions[row_idx].height = 22
        is_even = (row_idx % 2 == 0)
        base_fill = EVEN_FILL if is_even else ODD_FILL

        for col_idx, (_, field_key, _) in enumerate(columns, start=1):
            if field_key == "s_no":
                val = row_idx - 1
            elif field_key == "validation_errors_str":
                errs = r.get("validation_errors", [])
                val = "; ".join(errs) if errs else "None"
            else:
                val = r.get(field_key, "NA")

            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = CELL_FONT
            cell.border = THIN_BORDER
            cell.fill = base_fill

            if field_key in ("s_no", "contract_no", "generated_date", "buyer_contact", "seller_contact_no", "consignee_contact_no", "ordered_quantity", "validation_score"):
                cell.alignment = CELL_ALIGN_CENTER
            elif field_key in ("unit_price", "total_order_value"):
                cell.alignment = CELL_ALIGN_RIGHT
                if isinstance(val, (int, float)):
                    cell.number_format = '#,##0.00'
            elif field_key == "validation_status":
                cell.alignment = CELL_ALIGN_CENTER
                if val == "PASS":
                    cell.fill = PASS_FILL
                    cell.font = PASS_FONT
                else:
                    cell.fill = REVIEW_FILL
                    cell.font = REVIEW_FONT
            elif field_key in ("seller_email", "consignee_email", "buyer_email", "paying_authority_email") and val != "NA" and "@" in str(val):
                email_val = str(val).strip()
                cell.value = email_val
                cell.hyperlink = f"mailto:{email_val}"
                cell.font = EMAIL_FONT
                cell.alignment = CELL_ALIGN_LEFT
            else:
                cell.alignment = CELL_ALIGN_LEFT

    if records:
        last_col = get_column_letter(len(columns))
        ws.auto_filter.ref = f"A1:{last_col}{len(records) + 1}"

    ws.freeze_panes = "A2"

    target_path = excel_path
    try:
        wb.save(target_path)
    except PermissionError:
        # If open in Excel, save with timestamp / temp name
        target_path = excel_path.replace(".xlsx", f"_updated_{int(time.time())}.xlsx")
        wb.save(target_path)

    return target_path
