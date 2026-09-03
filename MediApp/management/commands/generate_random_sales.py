import random
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from MediApp.models import Sale, SaleItem, Customer, Medicine, Batch, InventoryLog

User = get_user_model()

class Command(BaseCommand):
    help = 'Generate random sales data to populate dashboard reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=200,
            help='Number of random sales to generate'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        customers = list(Customer.objects.all())
        medicines = list(Medicine.objects.prefetch_related('batches').all())
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()

        if not customers or not medicines:
            self.stdout.write(self.style.ERROR('Database must have customers and medicines before generating sales.'))
            return

        self.stdout.write(f'Generating {count} random sales...')
        
        now = timezone.now()
        start_date = now - timedelta(days=180) # Last 6 months

        payment_methods = ['Cash', 'Card', 'UPI', 'Other']
        weights = [0.4, 0.3, 0.25, 0.05] # 40% Cash, 30% Card, 25% UPI, 5% Other

        with transaction.atomic():
            for i in range(count):
                # Pick a random date
                random_days = random.randint(0, 180)
                random_seconds = random.randint(0, 86400)
                sale_date = start_date + timedelta(days=random_days, seconds=random_seconds)
                
                customer = random.choice(customers)
                payment_method = random.choices(payment_methods, weights=weights)[0]
                
                # Create Sale shell
                sale = Sale.objects.create(
                    customer=customer,
                    date=sale_date,
                    created_by=admin_user,
                    payment_method=payment_method,
                    status='Completed',
                    discount=Decimal('0.00'),
                    total_price=Decimal('0.00')
                )
                
                num_items = random.randint(1, 5)
                selected_meds = random.sample(medicines, min(num_items, len(medicines)))
                
                subtotal = Decimal('0.00')
                
                for med in selected_meds:
                    batches = med.batches.all()
                    if not batches:
                        continue
                        
                    batch = random.choice(batches)
                    quantity = random.randint(1, max(1, min(batch.quantity, 10)) if batch.quantity > 0 else 5)
                    
                    price = med.price
                    cost_price = batch.purchase_price
                    
                    # Create SaleItem
                    SaleItem.objects.create(
                        sale=sale,
                        medicine=med,
                        batch=batch,
                        quantity=quantity,
                        price=price,
                        cost_price=cost_price
                    )
                    
                    subtotal += price * quantity
                    
                    # Update Batch Quantity
                    if batch.quantity >= quantity:
                        batch.quantity -= quantity
                        batch.save()
                    
                    # Create InventoryLog
                    InventoryLog.objects.create(
                        medicine=med,
                        batch=batch,
                        action='sale',
                        quantity_change=-quantity,
                        performed_by=admin_user,
                        timestamp=sale_date,
                        notes=f'Auto-generated sale #{sale.id}'
                    )
                
                # Apply 0%, 5%, or 10% discount randomly
                discount_rate = Decimal(str(random.choice([0, 0.05, 0.10])))
                discount = (subtotal * discount_rate).quantize(Decimal('0.01'))
                
                sale.discount = discount
                sale.calculate_total()
                # Ensure correct date is preserved (save overrode it maybe)
                Sale.objects.filter(id=sale.id).update(date=sale_date)
                
        self.stdout.write(self.style.SUCCESS(f'Successfully generated {count} sales records!'))
