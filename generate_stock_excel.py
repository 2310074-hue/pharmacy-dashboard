import os
import django
import csv
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from MediApp.models import Medicine, Batch

def generate_csv():
    data = []
    
    # We will gather information about each medicine and its batches
    medicines = Medicine.objects.all().prefetch_related('batches', 'supplier', 'category')
    
    for med in medicines:
        supplier_name = med.supplier.name if med.supplier else 'No Supplier'
        supplier_contact = med.supplier.contact_number if med.supplier else 'N/A'
        supplier_email = med.supplier.email if med.supplier else 'N/A'
        category_name = med.category.name if med.category else 'Uncategorized'
        
        # Aggregate batch details
        batches = med.batches.all()
        if not batches:
            data.append({
                'Medicine Name': med.name,
                'Description': med.description,
                'Category': category_name,
                'Supplier': supplier_name,
                'Supplier Contact': supplier_contact,
                'Supplier Email': supplier_email,
                'Price (Selling)': float(med.price),
                'Batch Name': 'N/A',
                'Purchase Price': 'N/A',
                'Quantity in Stock': 0,
                'Expiry Date': 'N/A',
                'Is Expired': 'N/A',
                'Total Medicine Stock': 0,
                'Low Stock Warning': 'Yes'
            })
            continue
            
        for batch in batches:
            data.append({
                'Medicine Name': med.name,
                'Description': med.description,
                'Category': category_name,
                'Supplier': supplier_name,
                'Supplier Contact': supplier_contact,
                'Supplier Email': supplier_email,
                'Price (Selling)': float(med.price),
                'Batch Name': batch.batch_name,
                'Purchase Price': float(batch.purchase_price) if batch.purchase_price else 0,
                'Quantity in Stock': batch.quantity,
                'Expiry Date': batch.expiry_date.strftime('%Y-%m-%d') if batch.expiry_date else 'N/A',
                'Is Expired': 'Yes' if batch.is_expired else 'No',
                'Total Medicine Stock': med.total_quantity,
                'Low Stock Warning': 'Yes' if med.is_low_stock else 'No'
            })
            
    output_file = 'supplied_medicine_stock.csv'
    if not data:
        print("No data available.")
        return
        
    keys = data[0].keys()
    with open(output_file, 'w', newline='', encoding='utf-8') as output_file_handle:
        dict_writer = csv.DictWriter(output_file_handle, keys)
        dict_writer.writeheader()
        dict_writer.writerows(data)
        
    print(f"Successfully generated {output_file}")

if __name__ == '__main__':
    generate_csv()
