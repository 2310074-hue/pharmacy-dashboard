from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .forms import UserRegistrationForm
from .models import (
    User, Supplier, Medicine, Batch,
    Customer, MedicineReminder, Sale,
    SaleItem, InventoryLog, Category
)
from .tasks import send_reminder_to_customer, send_expiry_reminders, send_reminders_for_batch
from django.contrib import messages
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings
from django.core.mail import send_mail
from django.utils.html import format_html
from datetime import timedelta
from .models import ExpiryReminderLog
from .utils.email_utils import get_email_connection


class ExpiryDateFilter(admin.SimpleListFilter):
    """Custom sidebar filter for filtering records by expiry timeline."""
    title = 'Expiry date'
    parameter_name = 'expiry_timeline'

    def lookups(self, request, model_admin):
        return (
            ('7_days', 'Expiring in 7 days'),
            ('30_days', 'Expiring in 30 days'),
            ('expired', 'Already expired'),
        )

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == '7_days':
            return queryset.filter(expiry_date__gte=today, expiry_date__lte=today + timedelta(days=7))
        elif self.value() == '30_days':
            return queryset.filter(expiry_date__gte=today, expiry_date__lte=today + timedelta(days=30))
        elif self.value() == 'expired':
            return queryset.filter(expiry_date__lt=today)
        return queryset

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserRegistrationForm
    model = User

    list_display = ('username', 'email', 'role', 'contact_number', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'contact_number')
    ordering = ('username',)

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'role', 'contact_number')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'first_name', 'last_name',
                'role', 'contact_number', 'password1', 'password2'
            ),
        }),
    )


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'contact_number', 'email', 'created_at')
    search_fields = ('name', 'location', 'email')
    list_filter = ('location', 'created_at')
    ordering = ('-created_at',)


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'supplier', 'price', 'total_quantity', 'is_low_stock', 'created_at')
    list_filter = ('supplier',)
    search_fields = ('name', 'description')
    readonly_fields = ('total_quantity', 'is_low_stock')
    ordering = ('name',)


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('batch_name', 'medicine', 'quantity', 'expiry_date', 'is_expired', 'days_to_expiry', 'reminder_sent')
    list_filter = ('expiry_date', 'medicine')
    search_fields = ('batch_name', 'medicine__name')
    readonly_fields = ('is_expired', 'days_to_expiry')
    ordering = ('expiry_date',)
    actions = ['send_expiry_reminder']

    def send_expiry_reminder(self, request, queryset):
        # For manual admin action: send reminders now synchronously and log results
        total_sent = 0
        total_errors = 0
        for batch in queryset:
            res = send_reminders_for_batch(batch)
            total_sent += res.get('sent_count', 0)
            total_errors += len(res.get('errors', []))
        self.message_user(request, f"Sent {total_sent} reminders; {total_errors} errors.", level=messages.SUCCESS)
    send_expiry_reminder.short_description = 'Send expiry reminders for selected batches'


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'contact_number', 'is_permanent', 'total_purchases_count', 'created_at')
    list_filter = ('is_permanent', 'created_at')
    search_fields = ('name', 'email', 'contact_number')
    ordering = ('-created_at',)  # Ensures newest registered customers are always shown on top
    actions = ['send_reminders_to_customer']

    @admin.display(description='Purchases', ordering='sales')
    def total_purchases_count(self, obj):
        count = obj.sales.count()
        if count > 0:
            return format_html('<span style="background:#e0f2fe; color:#0369a1; padding:2px 8px; border-radius:12px; font-weight:700; font-size:11px;">{} orders</span>', count)
        return format_html('<span style="color:#94a3b8; font-size:11px;">{} orders</span>', 0)

    def send_reminders_to_customer(self, request, queryset):
        # send reminders for expiring batches to selected customers only
        sent = 0
        for customer in queryset:
            email = customer.email
            # find batches expiring within 7 days
            today = timezone.now().date()
            cutoff = today + timedelta(days=7)
            batches = Batch.objects.filter(expiry_date__gte=today, expiry_date__lte=cutoff, quantity__gt=0)
            for batch in batches:
                send_reminder_to_customer.delay(batch.id, email)
                sent += 1
        self.message_user(request, f"Queued {sent} reminders to selected customers.", level=messages.SUCCESS)
    send_reminders_to_customer.short_description = 'Send expiry reminders to selected customers (for expiring batches)'


@admin.register(MedicineReminder)
class MedicineReminderAdmin(admin.ModelAdmin):
    list_display = ('customer', 'medicine', 'reminder_text', 'created_at')
    search_fields = ('customer__name', 'medicine__name', 'reminder_text')
    ordering = ('-created_at',)
    actions = ['send_expiry_reminder_email_to_selected_customers', 'send_manual_reminder']

    @admin.action(description='Send expiry reminder email to selected customers')
    def send_expiry_reminder_email_to_selected_customers(self, request, queryset):
        """
        Sends bulk medicine expiry reminder email to selected customers via send_mail().
        Skips customers without email, logs results, and provides user feedback message.
        """
        sent_count = 0
        skipped_count = 0
        failed_count = 0

        for reminder in queryset:
            customer = reminder.customer
            customer_email = customer.email.strip() if (customer and customer.email) else ''
            customer_name = customer.name if customer else 'Customer'

            # Skip any customer with no email on file (don't crash)
            if not customer_email:
                skipped_count += 1
                continue

            medicine_name = reminder.medicine.name if reminder.medicine else (reminder.reminder_text or 'Medicine')

            # Determine expiry date / timeline
            expiry_str = 'Soon'
            if reminder.medicine:
                nearest_batch = reminder.medicine.batches.filter(quantity__gt=0).order_by('expiry_date').first()
                if nearest_batch and nearest_batch.expiry_date:
                    expiry_str = nearest_batch.expiry_date.strftime('%d-%b-%Y')
            elif reminder.send_at:
                expiry_str = reminder.send_at.strftime('%d-%b-%Y')

            # =========================================================================
            # ✉️ [EMAIL TEMPLATE START] — Edit the Subject & Body text below anytime:
            # =========================================================================
            subject = 'Your Medicine is Expiring Soon'
            body = (
                f"Dear {customer_name},\n\n"
                f"This is a reminder that your medicine {medicine_name} is expiring on {expiry_str}. "
                f"Please replace or restock it in time to avoid any inconvenience.\n\n"
                f"Thank you,\n"
                f"PharmaCare Team"
            )
            # =========================================================================
            # ✉️ [EMAIL TEMPLATE END]
            # =========================================================================

            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[customer_email],
                    fail_silently=False
                )
                sent_count += 1
                ExpiryReminderLog.objects.create(
                    customer_email=customer_email,
                    customer_name=customer_name,
                    medicine_name=medicine_name,
                    expiry_date=timezone.now().date(),
                    reminder_sent=True,
                    sent_at=timezone.now(),
                    message=body
                )
            except Exception as exc:
                failed_count += 1
                ExpiryReminderLog.objects.create(
                    customer_email=customer_email,
                    customer_name=customer_name,
                    medicine_name=medicine_name,
                    expiry_date=timezone.now().date(),
                    reminder_sent=False,
                    sent_at=timezone.now(),
                    message=f"Error: {exc}"
                )

        # Summary message to user
        if sent_count > 0 and failed_count == 0 and skipped_count == 0:
            self.message_user(
                request,
                f"✅ Successfully sent expiry reminder email(s) to {sent_count} customer(s).",
                level=messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                f"📧 Reminder Email Results: {sent_count} sent successfully, {skipped_count} skipped (no email on file), {failed_count} failed.",
                level=messages.INFO if sent_count > 0 else messages.WARNING
            )

    def send_manual_reminder(self, request, queryset):
        sent = 0
        for reminder in queryset:
            customer = reminder.customer
            email = customer.email if customer else None
            if not email:
                continue
            subject = 'Medicine Expiry Reminder'
            context = {'customer_name': customer.name, 'medicine_name': reminder.medicine.name if reminder.medicine else reminder.reminder_text, 'expiry_date': ''}
            message = render_to_string('email/medicine_expiry_reminder.txt', context)
            try:
                html_content = render_to_string('email/medicine_expiry_reminder.html', context)
                text_content = message
                msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [email])
                msg.attach_alternative(html_content, "text/html")
                msg.send(fail_silently=False)
                ExpiryReminderLog.objects.create(customer_email=email, customer_name=customer.name, medicine_name=reminder.medicine.name if reminder.medicine else '', expiry_date=reminder.send_at.date() if reminder.send_at else None, reminder_sent=True, sent_at=timezone.now(), message=text_content)
                sent += 1
            except Exception as e:
                ExpiryReminderLog.objects.create(customer_email=email, customer_name=customer.name, medicine_name=reminder.medicine.name if reminder.medicine else '', expiry_date=reminder.send_at.date() if reminder.send_at else None, reminder_sent=False, message=str(e))
        self.message_user(request, f"Sent {sent} reminders (or attempted).", level=messages.SUCCESS)
    send_manual_reminder.short_description = 'Send selected reminders now'


from django import forms


class ExpiryReminderLogAdminForm(forms.ModelForm):
    class Meta:
        model = ExpiryReminderLog
        fields = '__all__'
        widgets = {
            'customer_name': forms.TextInput(attrs={
                'list': 'customer_name_list',
                'placeholder': 'Type or select customer name...',
                'autocomplete': 'off',
                'style': 'width: 100%; max-width: 480px;',
            }),
            'customer_email': forms.TextInput(attrs={
                'list': 'customer_email_list',
                'placeholder': 'Type or select customer email...',
                'autocomplete': 'off',
                'style': 'width: 100%; max-width: 480px;',
            }),
            'medicine_name': forms.TextInput(attrs={
                'list': 'medicine_name_list',
                'placeholder': 'Type or select medicine name...',
                'autocomplete': 'off',
                'style': 'width: 100%; max-width: 480px;',
            }),
        }


def sync_customer_expiry_logs():
    """
    Scans customer sales history and batches to automatically create/update ExpiryReminderLog records
    for all medicines expiring soon (within next 90 days or expired in last 30 days).
    """
    today = timezone.now().date()
    cutoff_past = today - timedelta(days=30)
    cutoff_future = today + timedelta(days=90)

    recent_items = SaleItem.objects.filter(
        sale__customer__isnull=False,
        batch__isnull=False,
        batch__expiry_date__range=[cutoff_past, cutoff_future]
    ).select_related('sale__customer', 'medicine', 'batch')

    created_count = 0
    for item in recent_items:
        cust = item.sale.customer
        if not cust or not cust.email or not item.batch or not item.batch.expiry_date:
            continue
        
        email = cust.email.strip().lower()
        med_name = item.medicine.name if item.medicine else ''
        exp_date = item.batch.expiry_date

        _, created = ExpiryReminderLog.objects.get_or_create(
            customer_email=email,
            medicine_name=med_name,
            expiry_date=exp_date,
            defaults={
                'customer_name': cust.name,
                'reminder_sent': False
            }
        )
        if created:
            created_count += 1
    return created_count


@admin.register(ExpiryReminderLog)
class ExpiryReminderLogAdmin(admin.ModelAdmin):
    form = ExpiryReminderLogAdminForm
    list_display = (
        'customer_name',
        'customer_email',
        'medicine_name',
        'expiry_date',
        'expiry_status',
        'reminder_sent',
        'sent_at'
    )
    list_filter = (ExpiryDateFilter, 'reminder_sent')
    search_fields = ('customer_email', 'customer_name', 'medicine_name')
    ordering = ('expiry_date',)  # Sort soonest-expiring medicines first
    readonly_fields = ('sent_at',)
    actions = ['send_expiry_reminder_email_to_selected_customers', 'sync_all_customer_expiry_alerts']

    def changelist_view(self, request, extra_context=None):
        # Automatically scan and synchronize all customer purchase expiry alerts on page load
        try:
            sync_customer_expiry_logs()
        except Exception:
            pass
        return super().changelist_view(request, extra_context=extra_context)

    @admin.action(description='🔄 Sync all customer expiry alerts from sales history')
    def sync_all_customer_expiry_alerts(self, request, queryset):
        new_records = sync_customer_expiry_logs()
        self.message_user(
            request,
            f"✅ Synchronized customer expiry records! {new_records} new alerts added.",
            level=messages.SUCCESS
        )

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['all_customers'] = Customer.objects.order_by('name')
        extra_context['all_medicines'] = Medicine.objects.prefetch_related('batches').order_by('name')
        return super().changeform_view(request, object_id=object_id, form_url=form_url, extra_context=extra_context)

    @admin.display(description='Status / Timeline', ordering='expiry_date')
    def expiry_status(self, obj):
        """Color-coded indicator pill for quick visual scanning of expiry status."""
        if not obj.expiry_date:
            return format_html('<span style="color: #64748b; font-weight: 600;">No Date</span>')

        today = timezone.now().date()
        days_left = (obj.expiry_date - today).days

        if days_left < 0:
            return format_html(
                '<span style="display:inline-flex; align-items:center; gap:4px; background:#fee2e2; color:#991b1b; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:700; border:1px solid #fca5a5;">'
                '🔴 Expired ({}d ago)</span>',
                abs(days_left)
            )
        elif days_left <= 7:
            return format_html(
                '<span style="display:inline-flex; align-items:center; gap:4px; background:#fee2e2; color:#b91c1c; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:700; border:1px solid #f87171;">'
                '🔴 {} days left (Critical)</span>',
                days_left
            )
        elif days_left <= 30:
            return format_html(
                '<span style="display:inline-flex; align-items:center; gap:4px; background:#fef3c7; color:#92400e; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:700; border:1px solid #fde68a;">'
                '🟠 {} days left (Expiring Soon)</span>',
                days_left
            )
        else:
            return format_html(
                '<span style="display:inline-flex; align-items:center; gap:4px; background:#ecfdf5; color:#065f46; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:700; border:1px solid #a7f3d0;">'
                '🟢 {} days left (Safe)</span>',
                days_left
            )

    def save_model(self, request, obj, form, change):
        """
        Automatically sends the reminder email to the customer immediately when clicking
        'Save' or 'Save and add another' on the Add/Change admin form.
        """
        email = (obj.customer_email or '').strip()
        customer_name = obj.customer_name or 'Customer'
        medicine_name = obj.medicine_name or 'Medicine'
        expiry_str = obj.expiry_date.strftime('%d-%b-%Y') if obj.expiry_date else 'Soon'
        subject = f"Your Medicine is Expiring Soon - {medicine_name}"

        plain_body = (
            f"Dear {customer_name},\n\n"
            f"This is an important reminder that your medicine {medicine_name} is reaching its expiry date on {expiry_str}.\n\n"
            f"Medicine Details:\n"
            f"- Customer Name: {customer_name}\n"
            f"- Medicine Name: {medicine_name}\n"
            f"- Expiry Date: {expiry_str}\n\n"
            f"Please replace or restock it in time to avoid any health risk or inconvenience.\n\n"
            f"Thank you,\n"
            f"PharmaCare Healthcare Team"
        )

        now_str = timezone.now().strftime("%d-%b-%Y %I:%M %p")
        ref_id = f"EXP-{obj.id or 'NEW'}"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin:0; padding:16px; background-color:#f8fafc; font-family:'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
          <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width:600px; margin:0 auto; background-color:#ffffff; border-radius:12px; overflow:hidden; border:1px solid #e2e8f0; box-shadow:0 4px 6px -1px rgba(0,0,0,0.08);">
            <tr>
              <td style="background:linear-gradient(135deg, #0891b2 0%, #0e7490 100%); padding:24px 28px; text-align:center; color:#ffffff;">
                <h1 style="margin:0; font-size:22px; font-weight:700; color:#ffffff;">PharmaCare Pharmacy</h1>
                <p style="margin:6px 0 0 0; font-size:13px; color:#e0f2fe;">Medicine Expiry Notification Alert</p>
              </td>
            </tr>
            <tr>
              <td style="padding:28px 28px 20px 28px; color:#334155; line-height:1.6;">
                <p style="font-size:16px; font-weight:600; color:#0f172a; margin-top:0;">Dear {customer_name},</p>
                <p style="font-size:14px; color:#475569; margin:12px 0 20px 0;">
                  This is an important reminder that your medicine <strong>{medicine_name}</strong> is expiring on <span style="color:#b91c1c; font-weight:700;">{expiry_str}</span>.
                </p>
                
                <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background:#f8fafc; border-radius:8px; border:1px solid #cbd5e1; margin:20px 0; padding:16px;">
                  <tr>
                    <td style="padding:6px 12px; font-size:13px; color:#64748b; font-weight:600; width:40%;">Customer Name:</td>
                    <td style="padding:6px 12px; font-size:14px; color:#0f172a; font-weight:700;">{customer_name}</td>
                  </tr>
                  <tr>
                    <td style="padding:6px 12px; font-size:13px; color:#64748b; font-weight:600;">Medicine Name:</td>
                    <td style="padding:6px 12px; font-size:14px; color:#0891b2; font-weight:700;">{medicine_name}</td>
                  </tr>
                  <tr>
                    <td style="padding:6px 12px; font-size:13px; color:#64748b; font-weight:600;">Expiry Date:</td>
                    <td style="padding:6px 12px; font-size:14px; color:#dc2626; font-weight:700;">{expiry_str}</td>
                  </tr>
                  <tr>
                    <td style="padding:6px 12px; font-size:13px; color:#64748b; font-weight:600;">Action Required:</td>
                    <td style="padding:6px 12px; font-size:13px; color:#059669; font-weight:600;">Replace or Restock Soon</td>
                  </tr>
                </table>

                <p style="font-size:14px; color:#475569; margin:18px 0;">
                  Please replace or restock it in time to avoid any health risk or inconvenience.
                </p>
                
                <p style="margin:24px 0 0 0; font-size:14px; color:#334155;">
                  Thank you,<br>
                  <strong style="color:#0891b2;">PharmaCare Healthcare Team</strong>
                </p>
              </td>
            </tr>
            <tr>
              <td style="background:#f1f5f9; padding:14px 28px; text-align:center; font-size:11px; color:#94a3b8; border-top:1px solid #e2e8f0;">
                PharmaCare Management System • Reference #{ref_id} • Sent at {now_str}
              </td>
            </tr>
          </table>
        </body>
        </html>
        """

        if email:
            try:
                send_mail(
                    subject=subject,
                    message=plain_body,
                    html_message=html_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                    connection=get_email_connection()
                )
                obj.reminder_sent = True
                obj.sent_at = timezone.now()
                if not obj.message:
                    obj.message = plain_body
                super().save_model(request, obj, form, change)
                self.message_user(
                    request,
                    f"✅ Reminder email was sent automatically to {email}!",
                    level=messages.SUCCESS
                )
            except Exception as exc:
                obj.reminder_sent = False
                obj.message = f"Send Failed: {exc}"
                super().save_model(request, obj, form, change)
                self.message_user(
                    request,
                    f"⚠️ Record saved, but failed to send email to {email}: {exc}",
                    level=messages.ERROR
                )
        else:
            super().save_model(request, obj, form, change)
            self.message_user(
                request,
                "⚠️ Record saved without sending email (No email address provided).",
                level=messages.WARNING
            )

    @admin.action(description='Send expiry reminder email to selected customers')
    def send_expiry_reminder_email_to_selected_customers(self, request, queryset):
        sent_count = 0
        skipped_count = 0
        failed_count = 0
        conn = get_email_connection()

        for log in queryset:
            email = (log.customer_email or '').strip()
            if not email:
                skipped_count += 1
                continue

            customer_name = log.customer_name or 'Customer'
            medicine_name = log.medicine_name or 'Medicine'
            expiry_str = log.expiry_date.strftime('%d-%b-%Y') if log.expiry_date else 'Soon'
            now_str = timezone.now().strftime("%d-%b-%Y %I:%M %p")
            ref_id = f"EXP-{log.id}"

            subject = f"Your Medicine is Expiring Soon - {medicine_name}"

            plain_body = (
                f"Dear {customer_name},\n\n"
                f"This is an important reminder that your medicine {medicine_name} is reaching its expiry date on {expiry_str}.\n\n"
                f"Medicine Details:\n"
                f"- Customer Name: {customer_name}\n"
                f"- Medicine Name: {medicine_name}\n"
                f"- Expiry Date: {expiry_str}\n\n"
                f"Please replace or restock it in time to avoid any health risk or inconvenience.\n\n"
                f"Thank you,\n"
                f"PharmaCare Healthcare Team\n"
                f"Ref: {ref_id} | Dispatched: {now_str}"
            )

            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="margin:0; padding:16px; background-color:#f8fafc; font-family:'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
              <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width:600px; margin:0 auto; background-color:#ffffff; border-radius:12px; overflow:hidden; border:1px solid #e2e8f0; box-shadow:0 4px 6px -1px rgba(0,0,0,0.08);">
                <tr>
                  <td style="background:linear-gradient(135deg, #0891b2 0%, #0e7490 100%); padding:24px 28px; text-align:center; color:#ffffff;">
                    <h1 style="margin:0; font-size:22px; font-weight:700; color:#ffffff;">PharmaCare Pharmacy</h1>
                    <p style="margin:6px 0 0 0; font-size:13px; color:#e0f2fe;">Medicine Expiry Notification Alert</p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:28px 28px 20px 28px; color:#334155; line-height:1.6;">
                    <p style="font-size:16px; font-weight:600; color:#0f172a; margin-top:0;">Dear {customer_name},</p>
                    <p style="font-size:14px; color:#475569; margin:12px 0 20px 0;">
                      This is an important reminder that your medicine <strong>{medicine_name}</strong> is expiring on <span style="color:#b91c1c; font-weight:700;">{expiry_str}</span>.
                    </p>
                    
                    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background:#f8fafc; border-radius:8px; border:1px solid #cbd5e1; margin:20px 0; padding:16px;">
                      <tr>
                        <td style="padding:6px 12px; font-size:13px; color:#64748b; font-weight:600; width:40%;">Customer Name:</td>
                        <td style="padding:6px 12px; font-size:14px; color:#0f172a; font-weight:700;">{customer_name}</td>
                      </tr>
                      <tr>
                        <td style="padding:6px 12px; font-size:13px; color:#64748b; font-weight:600;">Medicine Name:</td>
                        <td style="padding:6px 12px; font-size:14px; color:#0891b2; font-weight:700;">{medicine_name}</td>
                      </tr>
                      <tr>
                        <td style="padding:6px 12px; font-size:13px; color:#64748b; font-weight:600;">Expiry Date:</td>
                        <td style="padding:6px 12px; font-size:14px; color:#dc2626; font-weight:700;">{expiry_str}</td>
                      </tr>
                      <tr>
                        <td style="padding:6px 12px; font-size:13px; color:#64748b; font-weight:600;">Action Required:</td>
                        <td style="padding:6px 12px; font-size:13px; color:#059669; font-weight:600;">Replace or Restock Soon</td>
                      </tr>
                    </table>

                    <p style="font-size:14px; color:#475569; margin:18px 0;">
                      Please replace or restock it in time to avoid any health risk or inconvenience.
                    </p>
                    
                    <p style="margin:24px 0 0 0; font-size:14px; color:#334155;">
                      Thank you,<br>
                      <strong style="color:#0891b2;">PharmaCare Healthcare Team</strong>
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="background:#f1f5f9; padding:14px 28px; text-align:center; font-size:11px; color:#94a3b8; border-top:1px solid #e2e8f0;">
                    PharmaCare Management System • Reference #{ref_id} • Sent at {now_str}
                  </td>
                </tr>
              </table>
            </body>
            </html>
            """

            try:
                send_mail(
                    subject=subject,
                    message=plain_body,
                    html_message=html_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                    connection=conn
                )
                sent_count += 1
                log.reminder_sent = True
                log.sent_at = timezone.now()
                log.save(update_fields=['reminder_sent', 'sent_at'])
            except Exception as exc:
                failed_count += 1

        self.message_user(
            request,
            f"📧 Expiry reminder results: {sent_count} sent successfully, {skipped_count} skipped (no email), {failed_count} failed.",
            level=messages.SUCCESS if sent_count > 0 and failed_count == 0 else messages.INFO
        )


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'date', 'total_price', 'created_by')
    list_filter = ('date', 'created_by')
    search_fields = ('customer__name',)
    inlines = [SaleItemInline]
    ordering = ('-date',)


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'medicine', 'batch', 'quantity', 'price', 'subtotal')
    search_fields = ('medicine__name', 'batch__batch_name')
    readonly_fields = ('subtotal',)


@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'batch', 'action', 'quantity_change', 'performed_by', 'timestamp')
    list_filter = ('action', 'performed_by', 'timestamp')
    search_fields = ('medicine__name', 'batch__batch_name', 'performed_by__username')
    ordering = ('-timestamp',)
