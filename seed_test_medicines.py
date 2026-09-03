import os, django, sys

sys.path.insert(0, 'd:/pharmacy_dashboard')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from MediApp.models import Medicine, Batch, Supplier, Category
from django.utils import timezone
from datetime import timedelta

today = timezone.now().date()

sun_pharma = Supplier.objects.get(name='Sun Pharma')
cipla      = Supplier.objects.get(name='Cipla')
dr_reddys  = Supplier.objects.filter(name__icontains="Reddy").first()
glenmark   = Supplier.objects.get(name='Glenmark')

cats = {c.name: c for c in Category.objects.all()}
cat_analgesic  = cats.get('Analgesics')
cat_antibiotic = cats.get('Antibiotics')
cat_antihist   = cats.get('Antihistamines')
cat_antidiab   = cats.get('Antidiabetics')
cat_antihyp    = cats.get('Antihypertensives')

# ---- 7-day filter medicines (expire in 4-6 days) ----
m1, _ = Medicine.objects.get_or_create(
    name='Dolo 650 [Test]',
    defaults={'price': 25, 'description': 'Fever and pain relief tablet', 'supplier': sun_pharma, 'category': cat_analgesic}
)
Batch.objects.get_or_create(
    medicine=m1, batch_name='DOLO-7DAY',
    defaults={'expiry_date': today + timedelta(days=4), 'quantity': 80, 'purchase_price': 18}
)
print(f"Created: {m1.name} - expires {today + timedelta(days=4)}")

m2, _ = Medicine.objects.get_or_create(
    name='Combiflam [Test]',
    defaults={'price': 35, 'description': 'Ibuprofen plus Paracetamol combination', 'supplier': cipla, 'category': cat_analgesic}
)
Batch.objects.get_or_create(
    medicine=m2, batch_name='COMBI-7DAY',
    defaults={'expiry_date': today + timedelta(days=6), 'quantity': 60, 'purchase_price': 25}
)
print(f"Created: {m2.name} - expires {today + timedelta(days=6)}")

# ---- 15-day filter medicines (expire in 9-13 days, NOT in 7-day range) ----
m3, _ = Medicine.objects.get_or_create(
    name='Allegra 180 [Test]',
    defaults={'price': 95, 'description': 'Fexofenadine antihistamine for allergies', 'supplier': dr_reddys, 'category': cat_antihist}
)
Batch.objects.get_or_create(
    medicine=m3, batch_name='ALLEGRA-15DAY',
    defaults={'expiry_date': today + timedelta(days=10), 'quantity': 45, 'purchase_price': 70}
)
print(f"Created: {m3.name} - expires {today + timedelta(days=10)}")

m4, _ = Medicine.objects.get_or_create(
    name='Azithromycin 500 [Test]',
    defaults={'price': 120, 'description': 'Antibiotic for bacterial infections', 'supplier': glenmark, 'category': cat_antibiotic}
)
Batch.objects.get_or_create(
    medicine=m4, batch_name='AZITH-15DAY',
    defaults={'expiry_date': today + timedelta(days=13), 'quantity': 30, 'purchase_price': 85}
)
print(f"Created: {m4.name} - expires {today + timedelta(days=13)}")

# ---- 30-day filter medicines (expire in 18-27 days, NOT in 7 or 15-day range) ----
m5, _ = Medicine.objects.get_or_create(
    name='Metformin 1000 [Test]',
    defaults={'price': 55, 'description': 'Type 2 diabetes management tablet', 'supplier': sun_pharma, 'category': cat_antidiab}
)
Batch.objects.get_or_create(
    medicine=m5, batch_name='MET1000-30DAY',
    defaults={'expiry_date': today + timedelta(days=20), 'quantity': 100, 'purchase_price': 40}
)
print(f"Created: {m5.name} - expires {today + timedelta(days=20)}")

m6, _ = Medicine.objects.get_or_create(
    name='Amlodipine 10 [Test]',
    defaults={'price': 70, 'description': 'Calcium channel blocker for hypertension', 'supplier': cipla, 'category': cat_antihyp}
)
Batch.objects.get_or_create(
    medicine=m6, batch_name='AMLO10-30DAY',
    defaults={'expiry_date': today + timedelta(days=27), 'quantity': 75, 'purchase_price': 50}
)
print(f"Created: {m6.name} - expires {today + timedelta(days=27)}")

print("")
print("Seeded successfully!")
print(f"  7-day  filter shows: Dolo 650 (4d), Combiflam (6d)")
print(f"  15-day filter adds:  Allegra 180 (10d), Azithromycin 500 (13d)")
print(f"  30-day filter adds:  Metformin 1000 (20d), Amlodipine 10 (27d)")
