import random
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from MediApp.models import Medicine, Customer, Sale, SaleItem, User, Batch

# 85 Authentic Real Indian Customer Profiles across India
REAL_INDIAN_CUSTOMERS = [
    ("Aarav Sharma", "aarav.sharma78@gmail.com", "9810123456"),
    ("Rajesh Kumar", "rajesh.kumar54@gmail.com", "9820234567"),
    ("Priya Verma", "priya.verma89@yahoo.com", "9830345678"),
    ("Amit Patel", "amit.patel92@rediffmail.com", "9840456789"),
    ("Sunita Gupta", "sunita.gupta65@gmail.com", "9850567890"),
    ("Vikram Singh", "vikram.singh81@outlook.com", "9860678901"),
    ("Neha Reddy", "neha.reddy90@gmail.com", "9870789012"),
    ("Rahul Mehra", "rahul.mehra84@yahoo.com", "9880890123"),
    ("Deepa Nair", "deepa.nair79@gmail.com", "9890901234"),
    ("Suresh Krishnan", "suresh.krishnan72@yahoo.com", "9711012345"),
    ("Meera Joshi", "meera.joshi88@gmail.com", "9722123456"),
    ("Ankit Shah", "ankit.shah86@outlook.com", "9733234567"),
    ("Kavya Menon", "kavya.menon94@gmail.com", "9744345678"),
    ("Arjun Rao", "arjun.rao85@yahoo.com", "9755456789"),
    ("Lakshmi Venkatesh", "lakshmi.v76@gmail.com", "9766567890"),
    ("Vijay Shetty", "vijay.shetty80@outlook.com", "9777678901"),
    ("Pooja Deshmukh", "pooja.deshmukh91@gmail.com", "9788789012"),
    ("Ravi Kulkarni", "ravi.kulkarni77@yahoo.com", "9799890123"),
    ("Anjali Sinha", "anjali.sinha87@gmail.com", "9910901234"),
    ("Manoj Tiwari", "manoj.tiwari75@outlook.com", "9921012345"),
    ("Swapna Pillai", "swapna.pillai83@gmail.com", "9932123456"),
    ("Ganesh Iyer", "ganesh.iyer79@yahoo.com", "9943234567"),
    ("Shilpa Bhatia", "shilpa.bhatia90@gmail.com", "9954345678"),
    ("Kiran Kumar", "kiran.kumar82@outlook.com", "9965456789"),
    ("Radhika Mishra", "radhika.mishra93@gmail.com", "9976567890"),
    ("Rohan Mukherjee", "rohan.mukherjee88@gmail.com", "9987678901"),
    ("Sneha Banerjee", "sneha.banerjee91@yahoo.com", "9998789012"),
    ("Sanjay Malhotra", "sanjay.malhotra74@gmail.com", "9811890123"),
    ("Alok Pandey", "alok.pandey85@outlook.com", "9822901234"),
    ("Ritu Saxena", "ritu.saxena89@gmail.com", "9833012345"),
    ("Harpreet Kaur", "harpreet.kaur86@gmail.com", "9844123456"),
    ("Manpreet Singh", "manpreet.singh80@yahoo.com", "9855234567"),
    ("Swati Kulkarni", "swati.kulkarni88@gmail.com", "9866345678"),
    ("Devendra Patil", "devendra.patil76@outlook.com", "9877456789"),
    ("Divya Sundaram", "divya.sundaram92@gmail.com", "9888567890"),
    ("Karthik Subramanian", "karthik.subramanian84@yahoo.com", "9899678901"),
    ("Sonal Agrawal", "sonal.agrawal87@gmail.com", "9712789012"),
    ("Nitin Bhatt", "nitin.bhatt83@gmail.com", "9723890123"),
    ("Pankaj Choudhary", "pankaj.choudhary79@outlook.com", "9734901234"),
    ("Tanvi Chauhan", "tanvi.chauhan95@gmail.com", "9745012345"),
    ("Deepak Rawat", "deepak.rawat81@yahoo.com", "9756123456"),
    ("Shubham Agarwal", "shubham.agarwal90@gmail.com", "9767234567"),
    ("Bhavna Goswami", "bhavna.goswami86@gmail.com", "9778345678"),
    ("Chetan Mahajan", "chetan.mahajan82@outlook.com", "9789456789"),
    ("Dinesh Hegde", "dinesh.hegde75@gmail.com", "9790567890"),
    ("Gauri Nadkarni", "gauri.nadkarni89@yahoo.com", "9911678901"),
    ("Hemant Rathi", "hemant.rathi78@gmail.com", "9922789012"),
    ("Ishaan Kapoor", "ishaan.kapoor94@outlook.com", "9933890123"),
    ("Jaya Bhaduri", "jaya.bhaduri68@gmail.com", "9944901234"),
    ("Kamal Nath", "kamal.nath71@yahoo.com", "9955012345"),
    ("Lata Joshi", "lata.joshi62@gmail.com", "9966123456"),
    ("Madhav Sharma", "madhav.sharma85@gmail.com", "9977234567"),
    ("Namrata Shirodkar", "namrata.s80@outlook.com", "9988345678"),
    ("Omkar Salve", "omkar.salve92@gmail.com", "9999456789"),
    ("Pradeep Jadhav", "pradeep.jadhav74@yahoo.com", "9812567890"),
    ("Rekha Grewal", "rekha.grewal79@gmail.com", "9823678901"),
    ("Sandeep Sawant", "sandeep.sawant83@gmail.com", "9834789012"),
    ("Tarun Mathur", "tarun.mathur88@outlook.com", "9845890123"),
    ("Umesh Chawla", "umesh.chawla76@yahoo.com", "9856901234"),
    ("Varun Dhawan", "varun.dhawan90@gmail.com", "9867012345"),
    ("Yashoda Bai", "yashoda.bai65@gmail.com", "9878123456"),
    ("Abhay Deol", "abhay.deol82@outlook.com", "9889234567"),
    ("Babita Bisht", "babita.bisht87@gmail.com", "9890345678"),
    ("Chirag Singhal", "chirag.singhal91@yahoo.com", "9713456789"),
    ("Geetika Kaul", "geetika.kaul89@gmail.com", "9724567890"),
    ("Himanshu Trivedi", "himanshu.trivedi84@gmail.com", "9735678901"),
    ("Jitendra Rathore", "jitendra.rathore77@outlook.com", "9746789012"),
    ("Kailash Chand", "kailash.chand70@yahoo.com", "9757890123"),
    ("Mamta Kulkarni", "mamta.kulkarni80@gmail.com", "9768901234"),
    ("Naveen Patnaik", "naveen.patnaik69@gmail.com", "9779012345"),
    ("Pankhuri Awasthi", "pankhuri.awasthi93@outlook.com", "9780123456"),
    ("Rupali Ganguly", "rupali.ganguly82@gmail.com", "9791234567"),
    ("Sameer Deshpande", "sameer.deshpande85@yahoo.com", "9912345678"),
    ("Tejasvi Surya", "tejasvi.surya90@gmail.com", "9923456789"),
    ("Urvashi Rautela", "urvashi.rautela94@gmail.com", "9934567890"),
    ("Yogesh Bindra", "yogesh.bindra83@outlook.com", "9945678901"),
    ("Ananya Roy", "ananya.roy92@gmail.com", "9814123456"),
    ("Bhupendra Yadav", "bhupendra.yadav78@yahoo.com", "9825234567"),
    ("Chitra Raghavan", "chitra.raghavan85@outlook.com", "9836345678"),
    ("Darshan Somaiya", "darshan.somaiya91@gmail.com", "9847456789"),
    ("Esha Deora", "esha.deora88@gmail.com", "9858567890"),
    ("Farhan Qureshi", "farhan.qureshi83@yahoo.com", "9869678901"),
    ("Giriraj Singh", "giriraj.singh74@outlook.com", "9870789012"),
    ("Harish Nambiar", "harish.nambiar80@gmail.com", "9881890123"),
]


class Command(BaseCommand):
    help = 'Generate 12 months of realistic historical sales data for demand forecasting with diverse Indian customers.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing sales data before generating new 12-month historical data.'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help='Number of historical days to generate (default: 365).'
        )

    def handle(self, *args, **options):
        clear_existing = options.get('clear', False)
        days_count = options.get('days', 365)

        medicines = list(Medicine.objects.all())
        if not medicines:
            self.stderr.write(self.style.ERROR("No medicines found in database! Please add medicines first."))
            return

        admin_user = User.objects.filter(is_staff=True).first() or User.objects.first()

        # Seed diverse real Indian customers into database
        self.stdout.write("Seeding authentic Indian customers into database...")
        for name, email, phone in REAL_INDIAN_CUSTOMERS:
            Customer.objects.get_or_create(
                name=name,
                defaults={
                    'email': email,
                    'contact_number': phone,
                    'created_by': admin_user,
                    'is_permanent': random.choice([True, False, False])
                }
            )

        customers = list(Customer.objects.all())
        self.stdout.write(f"Active Indian Customer Pool: {len(customers)} customers.")

        existing_sales_count = Sale.objects.count()
        if existing_sales_count > 0:
            if clear_existing:
                self.stdout.write(self.style.WARNING(f"Clearing {existing_sales_count} existing sales and items..."))
                SaleItem.objects.all().delete()
                Sale.objects.all().delete()
                self.stdout.write(self.style.SUCCESS("Existing sales data cleared successfully."))
            else:
                self.stdout.write(self.style.WARNING(
                    f"Warning: Database already has {existing_sales_count} sales records.\n"
                    "Use --clear if you want to wipe and regenerate a fresh 12-month dataset."
                ))

        self.stdout.write(self.style.NOTICE(
            f"Generating {days_count} days of historical sales across {len(medicines)} medicines and {len(customers)} customers..."
        ))

        # Reference price fallback mapping if medicine.price == 0
        price_fallbacks = {
            'Amoxicillin 500mg': Decimal('15.00'),
            'Azithromycin 500mg': Decimal('45.00'),
            'Doxycycline 100mg': Decimal('12.00'),
            'Ibuprofen 400mg': Decimal('8.00'),
        }

        # Medicine category profiles for realistic demand simulation
        def get_medicine_profile(medicine):
            cat_name = medicine.category.name if medicine.category else ''

            if 'antibiotic' in cat_name.lower():
                return {'base_qty': (3, 9), 'pattern': 'antibiotic', 'growth': 0.05}
            elif 'antihypertensive' in cat_name.lower() or 'cardiovascular' in cat_name.lower():
                return {'base_qty': (6, 14), 'pattern': 'chronic', 'growth': 0.18}
            elif 'antidiabetic' in cat_name.lower():
                return {'base_qty': (8, 16), 'pattern': 'chronic', 'growth': 0.15}
            elif 'antihistamine' in cat_name.lower():
                return {'base_qty': (4, 12), 'pattern': 'allergy', 'growth': 0.08}
            elif 'antipyretic' in cat_name.lower() or 'analgesic' in cat_name.lower():
                return {'base_qty': (10, 22), 'pattern': 'fever_pain', 'growth': 0.10}
            elif 'bronchodilator' in cat_name.lower():
                return {'base_qty': (2, 6), 'pattern': 'respiratory', 'growth': 0.06}
            elif 'gastrointestinal' in cat_name.lower():
                return {'base_qty': (6, 14), 'pattern': 'gastro', 'growth': 0.12}
            elif 'dermatological' in cat_name.lower():
                return {'base_qty': (2, 7), 'pattern': 'skin', 'growth': 0.05}
            elif 'vitamin' in cat_name.lower():
                return {'base_qty': (5, 12), 'pattern': 'wellness', 'growth': 0.14}
            else:
                return {'base_qty': (4, 10), 'pattern': 'general', 'growth': 0.10}

        def get_seasonal_multiplier(pattern, current_date, day_idx, total_days):
            month = current_date.month
            day_of_week = current_date.weekday()

            mult = 1.0

            if day_of_week in (5, 6):
                mult *= random.uniform(1.15, 1.30)
            else:
                mult *= random.uniform(0.90, 1.10)

            trend = 1.0 + (day_idx / total_days) * 0.15
            mult *= trend

            if pattern == 'antibiotic':
                if month in (7, 8, 9):
                    mult *= random.uniform(1.4, 1.8)
                elif month in (11, 12, 1):
                    mult *= random.uniform(1.3, 1.6)
                elif month in (4, 5):
                    mult *= random.uniform(0.7, 0.9)
            elif pattern == 'chronic':
                day_of_month = current_date.day
                if day_of_month in (1, 2, 3, 4, 5, 28, 29, 30):
                    mult *= random.uniform(1.2, 1.4)
            elif pattern == 'allergy':
                if month in (2, 3, 4):
                    mult *= random.uniform(1.5, 2.1)
                elif month in (9, 10):
                    mult *= random.uniform(1.3, 1.7)
            elif pattern == 'fever_pain':
                if month in (7, 8, 9, 11, 12, 1):
                    mult *= random.uniform(1.25, 1.55)
            elif pattern == 'respiratory':
                if month in (11, 12, 1, 2):
                    mult *= random.uniform(1.4, 1.9)
            elif pattern == 'skin':
                if month in (5, 6, 7, 8):
                    mult *= random.uniform(1.3, 1.7)
            elif pattern == 'wellness':
                if month in (12, 1, 2):
                    mult *= random.uniform(1.2, 1.5)

            return mult

        stockout_windows = {}
        for med in medicines:
            stockouts = set()
            num_stockouts = random.randint(1, 3)
            for _ in range(num_stockouts):
                start_day = random.randint(30, days_count - 20)
                duration = random.randint(2, 4)
                for d in range(start_day, start_day + duration):
                    stockouts.add(d)
            stockout_windows[med.id] = stockouts

        end_date = timezone.now()
        start_date = end_date - timedelta(days=days_count)

        payment_methods = ['Cash', 'Cash', 'UPI', 'UPI', 'UPI', 'Card', 'Other']
        total_sales_created = 0
        total_items_created = 0
        med_units_sold = {med.id: 0 for med in medicines}

        batch_cache = {}
        for med in medicines:
            batch_cache[med.id] = med.batches.first()

        sales_to_create = []

        self.stdout.write("Generating simulation days with diverse Indian customer sales...")
        for day_idx in range(days_count):
            current_dt = start_date + timedelta(days=day_idx)
            hour = random.randint(9, 21)
            minute = random.randint(0, 59)
            sale_time = current_dt.replace(hour=hour, minute=minute, second=0)

            daily_tx_count = random.randint(6, 18)
            for _ in range(daily_tx_count):
                # 82% Registered Indian Customer, 18% Walk-in Customer
                if random.random() < 0.82:
                    customer = random.choice(customers)
                else:
                    customer = None

                payment_method = random.choice(payment_methods)

                sale = Sale(
                    customer=customer,
                    date=sale_time + timedelta(minutes=random.randint(-180, 180)),
                    created_by=admin_user,
                    payment_method=payment_method,
                    status='Completed',
                    discount=Decimal('0.00'),
                    total_price=Decimal('0.00')
                )
                sales_to_create.append((sale, []))

                tx_meds = random.sample(medicines, k=random.randint(1, min(3, len(medicines))))
                tx_subtotal = Decimal('0.00')

                for med in tx_meds:
                    if day_idx in stockout_windows.get(med.id, set()):
                        continue

                    profile = get_medicine_profile(med)
                    multiplier = get_seasonal_multiplier(profile['pattern'], current_dt, day_idx, days_count)

                    qty = max(1, int(round(random.uniform(1, 3) * multiplier * random.uniform(0.8, 1.2))))
                    if qty > 10:
                        qty = 10

                    unit_price = med.price
                    if unit_price <= Decimal('0.00'):
                        unit_price = price_fallbacks.get(med.name, Decimal('10.00'))

                    unit_price = round(unit_price * Decimal(str(random.uniform(0.98, 1.02))), 2)
                    cost_price = round(unit_price * Decimal('0.70'), 2)

                    batch = batch_cache.get(med.id)
                    item = SaleItem(
                        medicine=med,
                        batch=batch,
                        quantity=qty,
                        price=unit_price,
                        cost_price=cost_price
                    )
                    sales_to_create[-1][1].append(item)
                    med_units_sold[med.id] += qty
                    tx_subtotal += unit_price * qty

                # Occasional discount for senior citizen / high value orders
                discount_amt = Decimal('0.00')
                if tx_subtotal > Decimal('200.00') and random.random() < 0.25:
                    discount_amt = round(tx_subtotal * Decimal('0.05'), 2) # 5% discount

                sales_to_create[-1][0].discount = discount_amt
                sales_to_create[-1][0].total_price = max(Decimal('0.00'), tx_subtotal - discount_amt)

        self.stdout.write("Writing generated sales to database in bulk...")

        with transaction.atomic():
            for sale_obj, items_list in sales_to_create:
                if items_list:
                    sale_obj.save()
                    for item in items_list:
                        item.sale = sale_obj
                        item.save()
                        total_items_created += 1
                    total_sales_created += 1

        # Summary output
        self.stdout.write(self.style.SUCCESS("\n========================================================"))
        self.stdout.write(self.style.SUCCESS("HISTORICAL SALES GENERATION COMPLETED SUCCESSFULLY!"))
        self.stdout.write(self.style.SUCCESS("========================================================"))
        self.stdout.write(f"Date Range Covered: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({days_count} days)")
        self.stdout.write(f"Total Sales Invoices Created: {total_sales_created}")
        self.stdout.write(f"Total Sale Items Recorded: {total_items_created}")
        self.stdout.write(f"Unique Indian Customer Pool: {len(customers)} active customers")
        self.stdout.write("\nPer-Medicine Total Units Sold (12-Month Historical Data):")
        self.stdout.write("--------------------------------------------------------")
        for med in sorted(medicines, key=lambda m: med_units_sold.get(m.id, 0), reverse=True):
            cat = med.category.name if med.category else 'General'
            units = med_units_sold.get(med.id, 0)
            self.stdout.write(f"- {med.name:<25} ({cat:<20}): {units:>5} units")
        self.stdout.write("--------------------------------------------------------\n")
