import random
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from MediApp.models import Customer, Batch, Sale, SaleItem, User


class Command(BaseCommand):
    help = 'Seed sample purchase history data for all customers'

    def handle(self, *args, **options):
        staff = User.objects.first()
        if not staff:
            self.stdout.write(self.style.ERROR("No users found. Create a user first."))
            return

        batches_with_stock = list(Batch.objects.filter(quantity__gt=0).select_related('medicine'))
        if not batches_with_stock:
            self.stdout.write(self.style.ERROR("No batches with stock found."))
            return

        payment_methods = ['Cash', 'Card', 'UPI', 'Other']
        customers = Customer.objects.all()

        self.stdout.write(f"Seeding purchase history for {customers.count()} customers...")
        total_sales = 0

        for customer in customers:
            num_sales = random.randint(2, 5)

            for _ in range(num_sales):
                days_ago = random.randint(1, 90)
                sale_date = timezone.now() - timedelta(days=days_ago, hours=random.randint(0, 12))
                payment = random.choice(payment_methods)
                discount = Decimal(str(random.choice([0, 0, 0, 5, 10, 15, 20, 25, 50])))

                sale = Sale.objects.create(
                    customer=customer,
                    date=sale_date,
                    total_price=0,
                    discount=discount,
                    created_by=staff,
                    payment_method=payment,
                    status='Completed',
                )

                num_items = random.randint(1, 4)
                chosen_batches = random.sample(batches_with_stock, min(num_items, len(batches_with_stock)))

                subtotal = Decimal('0')
                for batch in chosen_batches:
                    qty = random.randint(1, 5)
                    markup = Decimal(str(round(random.uniform(1.3, 2.0), 2)))
                    sell_price = (batch.purchase_price * markup).quantize(Decimal('0.01'))
                    if sell_price <= 0:
                        sell_price = Decimal('10.00')

                    SaleItem.objects.create(
                        sale=sale,
                        medicine=batch.medicine,
                        batch=batch,
                        quantity=qty,
                        price=sell_price,
                        cost_price=batch.purchase_price,
                    )
                    subtotal += sell_price * qty

                sale.total_price = max(subtotal - discount, Decimal('0'))
                sale.save()
                total_sales += 1

        self.stdout.write(self.style.SUCCESS(f"Done! Created {total_sales} sample sales across {customers.count()} customers."))
