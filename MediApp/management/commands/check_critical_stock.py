from django.core.management.base import BaseCommand
from django.conf import settings
from MediApp.forecasting import get_all_medicine_forecasts, send_forecast_critical_stock_email


class Command(BaseCommand):
    help = 'Evaluate 30-day inventory demand forecasts and dispatch critical stockout alert emails.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force send the summary alert email even if no critical shortages are found.',
        )
        parser.add_argument(
            '--recipient',
            type=str,
            default=None,
            help='Override recipient email address (default: sharmaneeraj3415@gmail.com).',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        recipient = options.get('recipient', None) or getattr(settings, 'EMAIL_HOST_USER', 'sharmaneeraj3415@gmail.com')

        self.stdout.write(self.style.NOTICE("Evaluating 30-day demand forecasts for inventory risk..."))

        all_fc = get_all_medicine_forecasts(days_ahead=30)
        critical = [f for f in all_fc if f['risk_level'] in ('CRITICAL', 'OUT_OF_STOCK')]
        high_risk = [f for f in all_fc if f['risk_level'] == 'HIGH']
        moderate = [f for f in all_fc if f['risk_level'] == 'MODERATE']
        safe = [f for f in all_fc if f['risk_level'] == 'ADEQUATE']

        self.stdout.write("------------------------------------------------------------")
        self.stdout.write(f"Catalog Analyzed: {len(all_fc)} medicines")
        self.stdout.write(f"  - Critical Shortages (< 7 days):   {len(critical)}")
        self.stdout.write(f"  - High Risk Shortages (< 15 days): {len(high_risk)}")
        self.stdout.write(f"  - Moderate Watchlist (< 30 days):  {len(moderate)}")
        self.stdout.write(f"  - Safe Inventory (30+ days):       {len(safe)}")
        self.stdout.write("------------------------------------------------------------")

        at_risk = critical + high_risk
        if at_risk:
            self.stdout.write(self.style.WARNING("Low Stock / Critical Medicines Detected:"))
            for item in at_risk:
                self.stdout.write(
                    f"  * {item['medicine_name']} ({item['category']}): "
                    f"Stock: {item['current_stock']} | 30d Demand: {item['total_30_day_demand']} | "
                    f"Days Left: {item['days_of_stock_left']}d | Reorder Target: +{item['recommended_reorder_qty']} units"
                )

        # Dispatch email
        result = send_forecast_critical_stock_email(recipient_email=recipient, force=force)

        if result.get('email_sent'):
            self.stdout.write(self.style.SUCCESS(f"\nSUCCESS: {result.get('message')}"))
        else:
            if at_risk:
                self.stdout.write(self.style.ERROR(f"\nFAILED to send email: {result.get('error')}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"\nNOTICE: {result.get('message')} (Use --force to send test alert)"))
