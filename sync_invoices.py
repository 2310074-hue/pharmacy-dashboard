import os, django, time
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from django.conf import settings
from MediApp.models import Sale, Invoice, InvoiceItem, User

t0 = time.time()
sales_without_invoice = Sale.objects.filter(invoice__isnull=True).order_by('date', 'id').select_related('customer', 'created_by').prefetch_related('items__medicine', 'items__batch')
count = sales_without_invoice.count()
print(f"Found {count} sales without invoices. Generating...")

default_user = User.objects.filter(is_superuser=True).first() or User.objects.first()

# Determine starting sequence
existing_invoices = Invoice.objects.all()
last_inv = existing_invoices.order_by('-id').first()
next_seq = 1

pharmacy_name = getattr(settings, 'PHARMACY_NAME', 'PharmaCare Pharmacy')
pharmacy_address = getattr(settings, 'PHARMACY_ADDRESS', 'Pharmacy address')
pharmacy_gstin = getattr(settings, 'PHARMACY_GSTIN', '')
pharmacy_phone = getattr(settings, 'PHARMACY_PHONE', '')

invoices_to_create = []
invoice_items_to_create = []

# Process in chunks using bulk_create or sequential generation
batch_size = 500
created_count = 0

for s in sales_without_invoice:
    year = s.date.year if s.date else timezone.now().year
    inv_num = f"INV-{year}-{s.id:05d}"
    
    items = list(s.items.all())
    subtotal_without_gst = Decimal('0')
    gst_total = Decimal('0')
    
    for item in items:
        if item.price is not None and item.quantity is not None:
            gross = Decimal(item.price) * Decimal(item.quantity)
            base = gross / Decimal('1.05')
            subtotal_without_gst += base
            gst_total += (gross - base)
            
    cgst = gst_total / Decimal('2')
    sgst = gst_total / Decimal('2')
    
    customer = s.customer
    inv = Invoice(
        invoice_number=inv_num,
        sale=s,
        customer=customer,
        created_by=s.created_by or default_user,
        invoice_date=s.date,
        pharmacy_name=pharmacy_name,
        pharmacy_address=pharmacy_address,
        pharmacy_gstin=pharmacy_gstin,
        pharmacy_phone=pharmacy_phone,
        customer_name=customer.name if customer else 'Walk-in Customer',
        customer_phone=customer.contact_number if customer else '',
        payment_method=s.payment_method or 'Cash',
        subtotal=subtotal_without_gst,
        gst_total=gst_total,
        cgst=cgst,
        sgst=sgst,
        discount=s.discount or Decimal('0'),
        final_amount=s.total_price or Decimal('0'),
    )
    invoices_to_create.append((inv, items))
    
    if len(invoices_to_create) >= batch_size:
        with transaction.atomic():
            for inv_obj, item_list in invoices_to_create:
                inv_obj.save()
                for it in item_list:
                    gross = Decimal(it.price) * Decimal(it.quantity)
                    base = gross / Decimal('1.05')
                    gst = gross - base
                    InvoiceItem.objects.create(
                        invoice=inv_obj,
                        medicine=it.medicine,
                        batch=it.batch,
                        medicine_name=it.medicine.name if it.medicine else 'Unknown Medicine',
                        batch_number=it.batch.batch_name if it.batch else '',
                        expiry_date=it.batch.expiry_date if it.batch else None,
                        quantity=it.quantity,
                        price=it.price,
                        gst_percent=Decimal('5'),
                        gst_amount=gst,
                        line_total=gross,
                    )
        created_count += len(invoices_to_create)
        print(f"Generated {created_count}/{count} invoices...")
        invoices_to_create = []

if invoices_to_create:
    with transaction.atomic():
        for inv_obj, item_list in invoices_to_create:
            inv_obj.save()
            for it in item_list:
                gross = Decimal(it.price) * Decimal(it.quantity)
                base = gross / Decimal('1.05')
                gst = gross - base
                InvoiceItem.objects.create(
                    invoice=inv_obj,
                    medicine=it.medicine,
                    batch=it.batch,
                    medicine_name=it.medicine.name if it.medicine else 'Unknown Medicine',
                    batch_number=it.batch.batch_name if it.batch else '',
                    expiry_date=it.batch.expiry_date if it.batch else None,
                    quantity=it.quantity,
                    price=it.price,
                    gst_percent=Decimal('5'),
                    gst_amount=gst,
                    line_total=gross,
                )
    created_count += len(invoices_to_create)

t1 = time.time()
print(f"DONE! Generated {created_count} invoices in {round(t1-t0, 2)} seconds.")
print(f"Total Invoices in DB now: {Invoice.objects.count()}")
