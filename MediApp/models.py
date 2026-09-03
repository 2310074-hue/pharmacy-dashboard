from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import timedelta

class User(AbstractUser):
    """Custom user model with role-based access"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('pharmacist', 'Pharmacist'),
        ('assistant', 'Assistant'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='assistant')
    contact_number = models.CharField(max_length=15, blank=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Category(models.Model):
    """Category model for classifying medicines"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='categories_created'
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Supplier(models.Model):
    """Supplier model for tracking medicine suppliers"""
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    contact_number = models.CharField(max_length=15)
    email = models.EmailField()
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suppliers_created'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Medicine(models.Model):
    """Medicine model with supplier relationship"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    supplier = models.ForeignKey(
        Supplier, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='supplied_medicines'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medicines'
    )
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medicines_created'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    reorder_threshold = models.PositiveIntegerField(default=10)
    preferred_supplier = models.ForeignKey(
        'Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preferred_medicines'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Uncheck this if the medicine is discontinued or no longer available'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def total_quantity(self):
        """Calculate total quantity across all batches"""
        return sum(batch.quantity for batch in self.batches.all())
    
    @property
    def is_low_stock(self):
        """Check if medicine is low on stock (less than 50 units)"""
        return self.total_quantity < 50

    @property
    def nearest_active_batch(self):
        """Return the nearest non-expired batch with stock, or nearest overall batch if all expired."""
        today = timezone.now().date()
        active = (
            self.batches
            .filter(expiry_date__gte=today, quantity__gt=0)
            .order_by('expiry_date')
            .first()
        )
        if active:
            return active
        # Fallback: return any nearest batch (expired or zero stock)
        return self.batches.order_by('expiry_date').first()


class Batch(models.Model):
    """Batch model for tracking medicine inventory"""
    medicine = models.ForeignKey(
        Medicine, 
        on_delete=models.CASCADE, 
        related_name='batches'
    )
    batch_name = models.CharField(max_length=50)
    add_date = models.DateField(default=timezone.now)
    expiry_date = models.DateField()
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    purchase_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Cost price per unit for this batch'
    )
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='batches_created'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    reminder_sent = models.BooleanField(default=False, help_text='Set to True after sending expiry reminders for this batch')

    class Meta:
        ordering = ['expiry_date']
        verbose_name_plural = 'Batches'

    def __str__(self):
        return f"{self.batch_name} - {self.medicine.name}"
    
    @property
    def is_expired(self):
        """Check if batch is expired"""
        if self.expiry_date is None:
            return False
        return timezone.now().date() > self.expiry_date
    
    @property
    def days_to_expiry(self):
        """Calculate days until expiry"""
        if self.expiry_date is None:
            return None
        return (self.expiry_date - timezone.now().date()).days


class Customer(models.Model):
    """Customer model for tracking pharmacy customers"""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    contact_number = models.CharField(max_length=15)
    is_permanent = models.BooleanField(
        default=False,
        help_text='Mark as permanent/loyal member to receive stock availability notifications.'
    )
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customers_created'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class MedicineReminder(models.Model):
    PERIOD_CHOICES = [
        ('one_time', 'One time'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom (days)'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='reminders')
    medicine = models.ForeignKey(Medicine, on_delete=models.SET_NULL, null=True)
    reminder_text = models.CharField(max_length=200)
    created_at = models.DateTimeField(default=timezone.now)

    # Scheduling options:
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, default='one_time')
    custom_days = models.PositiveIntegerField(null=True, blank=True)  # used if period == 'custom'
    send_at = models.DateTimeField(null=True, blank=True)  # optional next send timestamp (explicit)
    next_send = models.DateTimeField(null=True, blank=True)  # computed next send time (used by scheduler)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Reminder for {self.customer.name}"

    def schedule_next(self, from_dt=None):
        """Compute and set next_send based on period and custom_days.
           Call once after save, or let the scheduler update next_send.
        """
        if from_dt is None:
            from_dt = timezone.now()

        if self.send_at:
            # If a send_at is explicitly given and is in future, use that; otherwise compute below
            if self.send_at > from_dt:
                self.next_send = self.send_at
                return

        if self.period == 'one_time':
            # send immediately (or at send_at if set)
            self.next_send = self.send_at or from_dt
        elif self.period == 'daily':
            self.next_send = (self.send_at or from_dt) + timedelta(days=1)
        elif self.period == 'weekly':
            self.next_send = (self.send_at or from_dt) + timedelta(weeks=1)
        elif self.period == 'monthly':
            # crude monthly increment: +30 days
            self.next_send = (self.send_at or from_dt) + timedelta(days=30)
        elif self.period == 'custom' and self.custom_days:
            self.next_send = (self.send_at or from_dt) + timedelta(days=self.custom_days)
        else:
            self.next_send = None


class ExpiryReminderLog(models.Model):
    """Log for expiry reminders sent to customers."""
    customer_email = models.EmailField()
    customer_name = models.CharField(max_length=200, blank=True)
    medicine_name = models.CharField(max_length=200)
    expiry_date = models.DateField()
    reminder_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Expiry reminder to {self.customer_email} for {self.medicine_name}"


class ReminderLog(models.Model):
    """Generic record of reminders sent."""
    medicine_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    sent_at = models.DateTimeField(null=True, blank=True)
    success = models.BooleanField(default=False)
    message = models.TextField(blank=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"Reminder to {self.customer_email} for {self.medicine_name} at {self.sent_at}"


class Sale(models.Model):
    """Sale model for tracking pharmacy sales"""
    PAYMENT_CHOICES = [
        ('Cash', 'Cash'),
        ('Card', 'Card'),
        ('UPI', 'UPI'),
        ('Other', 'Other')
    ]
    STATUS_CHOICES = [
        ('Completed', 'Completed'),
        ('Refunded', 'Refunded')
    ]

    customer = models.ForeignKey(
        Customer, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='sales'
    )
    date = models.DateTimeField(default=timezone.now)
    total_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(Decimal('0'))]
    )
    # NEW: Discount field with default 0
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Discount amount applied to the sale'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sales_created'
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='Cash')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Completed')

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Sale #{self.id} - {self.date.strftime('%Y-%m-%d')}"
    
    def calculate_total(self):
        """Calculate total price from sale items minus discount"""
        subtotal = sum(
            item.price * item.quantity 
            for item in self.items.all()
        )
        self.total_price = subtotal - self.discount
        self.save()
    
    @property
    def subtotal(self):
        """Calculate subtotal before discount"""
        return sum(item.price * item.quantity for item in self.items.all())
    
    @property
    def final_amount(self):
        """Final amount after discount"""
        return self.total_price


class SaleItem(models.Model):
    """Sale item model for individual items in a sale"""
    sale = models.ForeignKey(
        Sale, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    medicine = models.ForeignKey(
        Medicine, 
        on_delete=models.SET_NULL, 
        null=True
    )
    batch = models.ForeignKey(
        Batch, 
        on_delete=models.SET_NULL, 
        null=True
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Historical cost price at time of sale'
    )

    def __str__(self):
        medicine_name = self.medicine.name if self.medicine else 'Unknown Medicine'
        quantity = self.quantity if self.quantity is not None else 0
        return f"{medicine_name} x{quantity}"
    
    @property
    def subtotal(self):
        """Calculate subtotal for this item"""
        if self.price is None or self.quantity is None:
            return Decimal('0.00')
        return self.price * self.quantity


class InventoryLog(models.Model):
    """Inventory log for tracking inventory changes"""
    ACTION_CHOICES = [
        ('add', 'Added'),
        ('update', 'Updated'),
        ('sale', 'Sold'),
        ('refund', 'Refunded'),
    ]
    
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.CASCADE,
        related_name='inventory_logs'
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='inventory_logs',
        null=True
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    quantity_change = models.IntegerField()
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='inventory_actions'
    )
    timestamp = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_action_display()} - {self.medicine.name} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"


class PurchaseOrder(models.Model):
    """Owner-scoped purchase order header for restocking."""
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Received', 'Received'),
        ('Cancelled', 'Cancelled'),
    ]

    order_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_orders'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    order_date = models.DateTimeField(default=timezone.now)
    expected_date = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_orders_created'
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['-order_date']

    def __str__(self):
        return self.order_number


class PurchaseOrderItem(models.Model):
    """Purchase order line items."""
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_order_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.medicine.name if self.medicine else 'Medicine'} x {self.quantity}"


class Invoice(models.Model):
    """Owner-scoped retail invoice record that mirrors the completed sale."""
    invoice_number = models.CharField(max_length=50, unique=True)
    sale = models.OneToOneField(
        Sale,
        on_delete=models.CASCADE,
        related_name='invoice'
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices_created'
    )
    invoice_date = models.DateTimeField(default=timezone.now)

    pharmacy_name = models.CharField(max_length=150, default='PharmaCare Pharmacy')
    pharmacy_address = models.TextField(default='Pharmacy address')
    pharmacy_gstin = models.CharField(max_length=30, blank=True, default='')
    pharmacy_phone = models.CharField(max_length=30, blank=True, default='')

    customer_name = models.CharField(max_length=100, blank=True, default='Walk-in Customer')
    customer_phone = models.CharField(max_length=30, blank=True, default='')

    payment_method = models.CharField(max_length=20, blank=True, default='Cash')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cgst = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sgst = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['-invoice_date']

    def __str__(self):
        return self.invoice_number


class InvoiceItem(models.Model):
    """Line items captured inside a generated invoice."""
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='invoice_items'
    )
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice_items'
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice_items'
    )
    medicine_name = models.CharField(max_length=160)
    batch_number = models.CharField(max_length=80, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.medicine_name} x {self.quantity} ({self.invoice.invoice_number})"