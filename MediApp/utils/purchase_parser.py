"""
Smart Distributor Purchase Invoice & Stock Parser Utility for PharmaCare.
Supports:
- Excel files (.xlsx, .xls)
- CSV files (.csv)
- Raw pasted text / TSV / CSV text from WhatsApp/Email
- Automatic column matching for Marg ERP, Vyapar, Busy, Tally, and custom distributor formats.
- Fuzzy date normalization (MM/YY, MM/YYYY, DD/MM/YYYY, ISO).
- Medicine fuzzy matching with existing catalog.
"""

import io
import re
import datetime
from decimal import Decimal
import pandas as pd
from django.utils import timezone
from MediApp.models import Medicine, Supplier, Category


# Column alias dictionary for intelligent header detection
COLUMN_ALIASES = {
    'medicine_name': [
        'item', 'item name', 'item_name', 'product', 'product name', 'product_name',
        'medicine', 'medicine name', 'medicine_name', 'description', 'particulars',
        'drug', 'drug name', 'item description', 'brand', 'brand name'
    ],
    'batch_name': [
        'batch', 'batch no', 'batch_no', 'batch number', 'b no', 'b.no', 'bno',
        'lot', 'lot no', 'lot number', 'batch/lot', 'batch #'
    ],
    'expiry_date': [
        'exp', 'exp.', 'expiry', 'exp date', 'exp_date', 'expiry date', 'expiry_date',
        'val till', 'valid till', 'exp. date', 'exp dt', 'exp_dt'
    ],
    'quantity': [
        'qty', 'quantity', 'billed qty', 'billed_qty', 'units', 'pcs', 'pack',
        'packs', 'total qty', 'inward qty', 'inward_qty'
    ],
    'free_quantity': [
        'free', 'free qty', 'free_qty', 'scheme', 'sch', 'sch qty', 'bonus',
        'free pcs', 'bonus qty'
    ],
    'purchase_price': [
        'rate', 'ptr', 'purchase rate', 'purchase_rate', 'cost', 'cost price',
        'cost_price', 'purchase price', 'purchase_price', 'net rate', 'net_rate',
        'buy price', 'unit price', 'unit rate'
    ],
    'mrp': [
        'mrp', 'm.r.p.', 'sale price', 'selling price', 'sale_price', 'selling_price',
        'max retail price', 'retail price', 'price'
    ],
    'category_name': [
        'category', 'category name', 'type', 'group', 'item group', 'classification'
    ]
}


def clean_currency_str(val):
    """Clean string value to numeric float/Decimal."""
    if val is None or pd.isna(val):
        return Decimal('0.00')
    if isinstance(val, (int, float, Decimal)):
        return Decimal(str(round(val, 2)))
    # Strip symbols
    s = str(val).replace('₹', '').replace('$', '').replace(',', '').strip()
    try:
        return Decimal(s) if s else Decimal('0.00')
    except Exception:
        return Decimal('0.00')


def parse_flexible_expiry_date(val):
    """
    Intelligently parse expiry date from diverse formats:
    - MM/YY, MM/YYYY, MM-YY, MM-YYYY (e.g. 05/27 -> 2027-05-31)
    - DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD
    - Pandas Timestamp / datetime.date
    """
    if val is None or pd.isna(val):
        # Default fallback: 1 year from now
        return (timezone.now().date() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')
    
    if isinstance(val, (datetime.date, datetime.datetime, pd.Timestamp)):
        return val.strftime('%Y-%m-%d')
    
    s = str(val).strip()
    if not s:
        return (timezone.now().date() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')

    # Pattern: MM/YY or MM/YYYY (e.g., 08/27, 08/2027, 8/27)
    m_month_year = re.match(r'^(\d{1,2})[\/\-](\d{2,4})$', s)
    if m_month_year:
        month = int(m_month_year.group(1))
        year = int(m_month_year.group(2))
        if year < 100:
            year += 2000
        if 1 <= month <= 12:
            # End of month date
            if month == 12:
                next_month = datetime.date(year + 1, 1, 1)
            else:
                next_month = datetime.date(year, month + 1, 1)
            last_day = next_month - datetime.timedelta(days=1)
            return last_day.strftime('%Y-%m-%d')

    # Pattern: DD/MM/YYYY or DD-MM-YYYY
    m_full = re.match(r'^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})$', s)
    if m_full:
        day = int(m_full.group(1))
        month = int(m_full.group(2))
        year = int(m_full.group(3))
        if year < 100:
            year += 2000
        try:
            return datetime.date(year, month, day).strftime('%Y-%m-%d')
        except ValueError:
            pass

    # Try pandas to_datetime
    try:
        dt = pd.to_datetime(s, dayfirst=True)
        return dt.strftime('%Y-%m-%d')
    except Exception:
        pass

    # Fallback to 1 year
    return (timezone.now().date() + datetime.timedelta(days=365)).strftime('%Y-%m-%d')


def detect_column_mapping(df_columns):
    """
    Match DataFrame column headers to standard fields using aliases.
    """
    mapping = {}
    normalized_cols = {col: str(col).strip().lower() for col in df_columns}
    
    for standard_field, aliases in COLUMN_ALIASES.items():
        for col_raw, col_norm in normalized_cols.items():
            if col_norm in aliases:
                mapping[standard_field] = col_raw
                break
        
        # If not exact alias match, check substring
        if standard_field not in mapping:
            for col_raw, col_norm in normalized_cols.items():
                if any(alias in col_norm for alias in aliases if len(alias) >= 3):
                    mapping[standard_field] = col_raw
                    break
                    
    return mapping


def parse_purchase_invoice_file(file_obj_or_content, filename=""):
    """
    Parse uploaded Excel (.xlsx, .xls) or CSV file.
    Returns structured list of parsed medicine rows with match status.
    """
    lower_fn = filename.lower()
    df = None

    try:
        if lower_fn.endswith('.xlsx') or lower_fn.endswith('.xls'):
            df = pd.read_excel(file_obj_or_content)
        elif lower_fn.endswith('.csv'):
            try:
                df = pd.read_csv(file_obj_or_content)
            except Exception:
                # Retry with latin1 encoding
                if hasattr(file_obj_or_content, 'seek'):
                    file_obj_or_content.seek(0)
                df = pd.read_csv(file_obj_or_content, encoding='latin1')
        else:
            # Try text/csv or excel auto-detect
            try:
                df = pd.read_excel(file_obj_or_content)
            except Exception:
                if hasattr(file_obj_or_content, 'seek'):
                    file_obj_or_content.seek(0)
                df = pd.read_csv(file_obj_or_content, sep=None, engine='python')
    except Exception as e:
        return {
            'success': False,
            'error': f"File reading failed: {str(e)}",
            'items': []
        }

    if df is None or df.empty:
        return {
            'success': False,
            'error': "The uploaded file contains no data or could not be read.",
            'items': []
        }

    return process_parsed_dataframe(df)


def parse_pasted_purchase_text(raw_text):
    """
    Parse raw pasted table data (comma-separated, tab-separated, or pipe-separated).
    """
    if not raw_text or not raw_text.strip():
        return {'success': False, 'error': "No text provided to parse.", 'items': []}

    try:
        # Detect delimiter
        first_line = raw_text.strip().split('\n')[0]
        sep = '\t' if '\t' in first_line else (',' if ',' in first_line else ('|' if '|' in first_line else None))
        
        df = pd.read_csv(io.StringIO(raw_text), sep=sep, engine='python')
        return process_parsed_dataframe(df)
    except Exception as e:
        return {'success': False, 'error': f"Failed to parse pasted text: {str(e)}", 'items': []}


def process_parsed_dataframe(df):
    """
    Process DataFrame rows into normalized dictionary entries and match against existing DB medicines.
    """
    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]
    mapping = detect_column_mapping(df.columns)

    if 'medicine_name' not in mapping:
        return {
            'success': False,
            'error': "Could not detect Medicine / Item Name column in the file. Please ensure column is labeled 'Medicine', 'Item Name', or 'Product'.",
            'detected_columns': list(df.columns),
            'items': []
        }

    # Fetch existing medicines for fast matching
    existing_medicines = {m.name.strip().lower(): m for m in Medicine.objects.all()}
    
    parsed_items = []
    total_bill_amount = Decimal('0.00')

    for idx, row in df.iterrows():
        med_name_val = row.get(mapping.get('medicine_name', ''))
        if pd.isna(med_name_val) or not str(med_name_val).strip():
            continue

        med_name = str(med_name_val).strip()

        # Batch
        batch_col = mapping.get('batch_name')
        batch_name = str(row.get(batch_col)).strip() if batch_col and not pd.isna(row.get(batch_col)) else f"BAT-{timezone.now().strftime('%y%m')}-{idx+1:02d}"

        # Expiry Date
        exp_col = mapping.get('expiry_date')
        expiry_val = row.get(exp_col) if exp_col else None
        expiry_date = parse_flexible_expiry_date(expiry_val)

        # Quantity
        qty_col = mapping.get('quantity')
        try:
            qty_raw = row.get(qty_col, 1)
            quantity = int(float(qty_raw)) if not pd.isna(qty_raw) and float(qty_raw) > 0 else 1
        except Exception:
            quantity = 1

        # Free Scheme Quantity
        free_col = mapping.get('free_quantity')
        try:
            free_raw = row.get(free_col, 0)
            free_qty = int(float(free_raw)) if not pd.isna(free_raw) and float(free_raw) > 0 else 0
        except Exception:
            free_qty = 0

        total_quantity = quantity + free_qty

        # Purchase Price (Rate)
        rate_col = mapping.get('purchase_price')
        purchase_price = clean_currency_str(row.get(rate_col)) if rate_col else Decimal('0.00')

        # MRP
        mrp_col = mapping.get('mrp')
        mrp = clean_currency_str(row.get(mrp_col)) if mrp_col else Decimal('0.00')
        if mrp <= Decimal('0.00') and purchase_price > Decimal('0.00'):
            # Default MRP estimate = Purchase Price * 1.25 (25% margin)
            mrp = round(purchase_price * Decimal('1.25'), 2)
        elif mrp <= Decimal('0.00'):
            mrp = Decimal('10.00')

        if purchase_price <= Decimal('0.00') and mrp > Decimal('0.00'):
            purchase_price = round(mrp * Decimal('0.75'), 2)

        line_total = round(purchase_price * Decimal(str(quantity)), 2)
        total_bill_amount += line_total

        # Match with DB Medicine
        matched_medicine = existing_medicines.get(med_name.lower())
        matched_id = matched_medicine.id if matched_medicine else None
        match_status = 'Existing' if matched_medicine else 'New Item'

        # Category
        cat_col = mapping.get('category_name')
        category_name = str(row.get(cat_col)).strip() if cat_col and not pd.isna(row.get(cat_col)) else ''

        parsed_items.append({
            'row_index': idx,
            'medicine_name': med_name,
            'matched_medicine_id': matched_id,
            'match_status': match_status,
            'batch_name': batch_name,
            'expiry_date': expiry_date,
            'quantity': quantity,
            'free_quantity': free_qty,
            'total_quantity': total_quantity,
            'purchase_price': float(purchase_price),
            'mrp': float(mrp),
            'line_total': float(line_total),
            'category_name': category_name,
        })

    return {
        'success': True,
        'detected_mapping': mapping,
        'total_items_count': len(parsed_items),
        'total_bill_amount': float(total_bill_amount),
        'items': parsed_items
    }
