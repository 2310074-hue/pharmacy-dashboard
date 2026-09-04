from types import SimpleNamespace
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from .models import User, Medicine, Supplier, Category, Customer, Sale, Batch
from .views import owner_scope_queryset, is_admin_role


class ChatbotWorkflowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='chatbot_admin',
            email='chatbot_admin@example.com',
            password='pass1234',
            role='admin',
            is_superuser=True,
        )
        self.client.force_login(self.admin)

    @patch('MediApp.views._call_gemini_api', return_value='Open the Suppliers page and choose Add Supplier.')
    def test_chatbot_returns_gemini_response(self, mock_gemini):
        response = self.client.post(
            '/api/chatbot/',
            data='{"message": "how to add a new supplier"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(mock_gemini.called)
        self.assertEqual(mock_gemini.call_args[0][0], 'how to add a new supplier')
        self.assertIn('supplier', payload.get('reply', '').lower())

    @patch('MediApp.views._call_gemini_api', return_value='<script>alert(1)</script>')
    def test_chatbot_escapes_model_html(self, mock_gemini):
        response = self.client.post(
            '/api/chatbot/',
            data='{"message": "hello"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['reply'], '&lt;script&gt;alert(1)&lt;/script&gt;')


class RoleScopedDataIsolationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin_user',
            email='admin@example.com',
            password='pass1234',
            role='admin',
            is_superuser=True,
        )
        self.pharmacist = User.objects.create_user(
            username='pharmacist_user',
            email='pharma@example.com',
            password='pass1234',
            role='pharmacist',
        )

        self.category = Category.objects.create(name='Test Category', description='Test', created_by=self.admin)
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            location='Mumbai',
            contact_number='9999999999',
            email='supplier@example.com',
            created_by=self.admin,
        )

        self.admin_medicine = Medicine.objects.create(
            name='Admin Medicine',
            description='Admin owned stock',
            supplier=self.supplier,
            category=self.category,
            price=Decimal('50.00'),
            created_by=self.admin,
        )
        self.staff_medicine = Medicine.objects.create(
            name='Pharmacy Medicine',
            description='User owned stock',
            supplier=self.supplier,
            category=self.category,
            price=Decimal('75.00'),
            created_by=self.pharmacist,
        )

        self.admin_customer = Customer.objects.create(
            name='Admin Customer',
            email='admin.customer@example.com',
            contact_number='9000000000',
            created_by=self.admin,
        )
        self.staff_customer = Customer.objects.create(
            name='Staff Customer',
            email='staff.customer@example.com',
            contact_number='9000000001',
            created_by=self.pharmacist,
        )

        Sale.objects.create(created_by=self.admin, total_price=Decimal('1000.00'), discount=Decimal('0.00'), date=timezone.now())
        Sale.objects.create(created_by=self.pharmacist, total_price=Decimal('500.00'), discount=Decimal('0.00'), date=timezone.now())

    def test_admin_can_see_everything(self):
        request = SimpleNamespace(user=self.admin)
        medicines = owner_scope_queryset(request, Medicine.objects.all(), 'created_by')
        sales = owner_scope_queryset(request, Sale.objects.all(), 'created_by')

        self.assertEqual(medicines.count(), 2)
        self.assertEqual(sales.count(), 2)
        self.assertTrue(is_admin_role(self.admin))

    def test_non_admin_only_sees_own_records(self):
        request = SimpleNamespace(user=self.pharmacist)
        medicines = owner_scope_queryset(request, Medicine.objects.all(), 'created_by')
        sales = owner_scope_queryset(request, Sale.objects.all(), 'created_by')

        self.assertEqual(medicines.count(), 1)
        self.assertEqual(list(medicines.values_list('name', flat=True)), ['Pharmacy Medicine'])
        self.assertEqual(sales.count(), 1)
        self.assertEqual(list(sales.values_list('created_by__username', flat=True)), ['pharmacist_user'])
        self.assertFalse(is_admin_role(self.pharmacist))

    def test_smart_analytics_is_user_scoped_for_new_pharmacist(self):
        fresh = User.objects.create_user(
            username='fresh_pharmacist',
            email='fresh@example.com',
            password='pass1234',
            role='pharmacist',
        )

        self.client.login(username='fresh_pharmacist', password='pass1234')
        response = self.client.get('/api/smart-analytics/', {'filter': 'month'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        kpi = payload.get('kpi', {})

        self.assertEqual(kpi.get('total_revenue'), 0)
        self.assertEqual(kpi.get('total_profit'), 0)
        self.assertEqual(kpi.get('sale_count'), 0)
        self.assertEqual(kpi.get('avg_order_value'), 0)
        self.assertEqual(kpi.get('refund_rate'), 0)
        self.assertEqual(kpi.get('top_medicine'), '—')
        self.assertEqual(kpi.get('top_medicine_qty'), 0)
        self.assertEqual(payload.get('top_customers'), [])
        self.assertTrue(payload.get('insights'))
