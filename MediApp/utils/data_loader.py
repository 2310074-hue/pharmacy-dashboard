from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import csv

from django.conf import settings
from django.utils import timezone

from MediApp.models import Category, Supplier, Medicine, Batch, Customer, Sale, SaleItem

CSV_DATE_FORMATS = ('%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S')


def parse_decimal(value, default='0.00'):
    if value is None:
        return Decimal(default)
    text = str(value).strip()
    if not text:
        return Decimal(default)
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        cleaned = text.replace(',', '').replace(' ', '')
        try:
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return Decimal(default)


def parse_int(value, default=0):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    try:
        return int(float(text)) if '.' in text else int(text)
    except ValueError:
        digits = ''.join(ch for ch in text if ch.isdigit())
        return int(digits) if digits else default


def parse_date(value):
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in CSV_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def parse_datetime(value):
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in CSV_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _csv_file(base_dir: Path, filenames):
    for filename in filenames:
        candidate = base_dir / filename
        if candidate.exists():
            return candidate
    return None


def import_csv_dataset(base_dir=None):
    base_dir = Path(base_dir or settings.BASE_DIR)
    if not base_dir.exists():
        return

    # Categories
    categories_path = _csv_file(base_dir, ['catrgories.csv', 'categories.csv'])
    if categories_path:
        with categories_path.open(newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                name = (row.get('name') or '').strip()
                if not name:
                    continue
                Category.objects.get_or_create(
                    name=name,
                    defaults={'description': (row.get('description') or '').strip()}
                )

    # Suppliers
    suppliers_path = base_dir / 'suppliers.csv'
    if suppliers_path.exists():
        with suppliers_path.open(newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                name = (row.get('name') or '').strip()
                if not name:
                    continue
                contact_number = (row.get('phone') or '').strip()[:15] or '0000000000'
                email = (row.get('email') or '').strip() or 'unknown@supplier.com'
                location_parts = [row.get('address', ''), row.get('city', ''), row.get('state', '')]
                location = ', '.join(part.strip() for part in location_parts if part and part.strip())[:100]
                Supplier.objects.get_or_create(
                    name=name,
                    defaults={
                        'location': location or 'Unknown',
                        'description': (row.get('contact_person') or '').strip(),
                        'contact_number': contact_number,
                        'email': email,
                    }
                )

    # Customers
    customers_path = base_dir / 'customers.csv'
    if customers_path.exists():
        with customers_path.open(newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                first_name = (row.get('first_name') or '').strip()
                last_name = (row.get('last_name') or '').strip()
                name = f"{first_name} {last_name}".strip() or 'Walk-in Customer'
                email = (row.get('email') or '').strip() or f"unknown+{row.get('id','unknown')}@example.com"
                contact_number = (row.get('phone') or '').strip()[:15] or '0000000000'
                Customer.objects.get_or_create(
                    email=email,
                    defaults={
                        'name': name[:100],
                        'contact_number': contact_number,
                    }
                )

    # Medicines and Batches
    medicines_path = base_dir / 'medicines.csv'
    if medicines_path.exists():
        with medicines_path.open(newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                medicine_name = (row.get('name') or '').strip()
                if not medicine_name:
                    continue
                category_name = (row.get('category') or '').strip()
                category = None
                if category_name:
                    category, _ = Category.objects.get_or_create(name=category_name)

                supplier_name = (row.get('supplier') or '').strip()
                supplier = None
                if supplier_name:
                    supplier, _ = Supplier.objects.get_or_create(
                        name=supplier_name,
                        defaults={
                            'location': 'Unknown',
                            'contact_number': '0000000000',
                            'email': 'unknown@supplier.com'
                        }
                    )

                price = parse_decimal(row.get('selling_price'))
                description = (row.get('description') or '').strip()
                medicine, _ = Medicine.objects.get_or_create(
                    name=medicine_name,
                    defaults={
                        'description': description,
                        'category': category,
                        'supplier': supplier,
                        'price': price,
                    }
                )

                batch_name = (row.get('batch_number') or 'default').strip() or 'default'
                expiry_date = parse_date(row.get('expiry_date'))
                quantity = parse_int(row.get('current_stock'))
                purchase_price = parse_decimal(row.get('purchase_price'))
                if expiry_date is None:
                    expiry_date = timezone.now().date() + timezone.timedelta(days=365)

                Batch.objects.get_or_create(
                    medicine=medicine,
                    batch_name=batch_name,
                    defaults={
                        'expiry_date': expiry_date,
                        'quantity': quantity,
                        'purchase_price': purchase_price,
                    }
                )

    # Sales and Sale Items
    sales_path = base_dir / 'sales.csv'
    sale_id_map = {}
    if sales_path.exists():
        with sales_path.open(newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                sale_id = (row.get('sale_id') or '').strip()
                customer_name = (row.get('customer_name') or '').strip() or 'Walk-in'
                customer = Customer.objects.filter(name__iexact=customer_name).first()
                if not customer:
                    customer = Customer.objects.create(
                        name=customer_name,
                        email=f"unknown+{sale_id}@example.com",
                        contact_number='0000000000'
                    )

                date = parse_datetime(row.get('created_at')) or timezone.now()
                payment_method = (row.get('payment_method') or 'Other').strip()
                if payment_method not in ('Cash', 'Card', 'UPI'):
                    payment_method = 'Other'

                status = (row.get('status') or 'Completed').strip()
                total_price = parse_decimal(row.get('total_amount'))
                discount = parse_decimal(row.get('discount_amount'))

                sale, _ = Sale.objects.get_or_create(
                    customer=customer,
                    date=date,
                    total_price=total_price,
                    payment_method=payment_method,
                    status=status,
                    defaults={'discount': discount}
                )
                sale_id_map[sale_id] = sale

    sales_items_path = base_dir / 'sales_item.csv'
    if sales_items_path.exists() and sale_id_map:
        with sales_items_path.open(newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                sale_id = (row.get('sale_id') or '').strip()
                sale = sale_id_map.get(sale_id)
                if not sale:
                    continue

                medicine_name = (row.get('medicine_name') or '').strip()
                medicine = Medicine.objects.filter(name__iexact=medicine_name).first()
                batch = None
                if medicine is not None:
                    batch = medicine.batches.filter(quantity__gt=0).order_by('expiry_date').first()

                quantity = parse_int(row.get('quantity'), default=1)
                price = parse_decimal(row.get('unit_price'))
                cost_price = parse_decimal(row.get('purchase_price') or row.get('cost_price'))

                SaleItem.objects.get_or_create(
                    sale=sale,
                    medicine=medicine,
                    batch=batch,
                    quantity=quantity,
                    price=price,
                    defaults={'cost_price': cost_price}
                )

    return True
