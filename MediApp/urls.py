# MediApp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Medicine
    path('medicine/', views.medicine_list, name='medicine_list'),
    path('medicine/add/', views.add_medicine, name='add_medicine'),
    path('medicine/<int:id>/edit/', views.edit_medicine, name='edit_medicine'),
    path('medicine/<int:id>/delete/', views.delete_medicine, name='delete_medicine'),
    path('medicine/<int:medicine_id>/notify-stock/', views.notify_stock_available, name='notify_stock_available'),
   
    path('medicine/batch/<int:id>/', views.get_batch, name='get_batch'),
    path('medicine/batch/save/', views.save_batch, name='save_batch'),
    path('medicine/batch/<int:id>/delete/', views.delete_batch, name='delete_batch'),
    path('medicine/export-stock/', views.export_all_medicine_stock, name='export_all_medicine_stock'),

    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/<int:id>/edit/', views.edit_category, name='edit_category'),
    path('categories/<int:id>/delete/', views.delete_category, name='delete_category'),

    
    # Sales
    path('sales/', views.sales_list, name='sales_list'),
    path('sales/add/', views.add_sale, name='add_sale'),
    path('sales/<int:id>/refund/', views.refund_sale, name='refund_sale'),
    path('sales/<int:id>/delete/', views.delete_sale, name='delete_sale'),

    # Purchase Orders / Reorder
    path('purchase-orders/', views.purchase_order_list, name='purchase_order_list'),
    path('purchase-orders/add/', views.purchase_order_add, name='purchase_order_add'),
    path('purchase-orders/<int:po_id>/receive/', views.purchase_order_receive, name='purchase_order_receive'),

    # Billing / Invoice
    path('billing/', views.invoice_history, name='invoice_history'),
    path('billing/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('billing/<int:invoice_id>/print/', views.invoice_print, name='invoice_print'),
    
    # Customer
    path('customer/', views.customer_list, name='customer_list'),
    path('customer/add/', views.add_customer, name='add_customer'),
    path('customer/<int:customer_id>/edit/', views.edit_customer, name='edit_customer'),
    path('customer/<int:id>/delete/', views.delete_customer, name='delete_customer'),

    path('customer/<int:customer_id>/reminder/create/', views.reminder_create, name='reminder_create'),
    path('reminder/<int:reminder_id>/json/', views.reminder_detail_json, name='reminder_detail_json'),

    path('reminder/<int:reminder_id>/update/', views.reminder_update, name='reminder_update'),
    path('reminder/<int:reminder_id>/delete/', views.reminder_delete, name='reminder_delete'),
    path('reminder/<int:reminder_id>/send-now/', views.send_reminder_now, name='send_reminder_now'),
    path('reminders/send-due/', views.send_due_reminders_view, name='send_due_reminders'),

    # Expiry Reminders (Customer Purchase Expiry Notification Module)
    path('expiry-reminders/', views.expiry_reminder_list, name='expiry_reminder_list'),
    path('expiry-reminders/send-bulk/', views.send_expiry_reminders_bulk, name='send_expiry_reminders_bulk'),
    path('expiry-reminders/<int:log_id>/send/', views.send_single_expiry_reminder, name='send_single_expiry_reminder'),
    path('expiry-reminders/sync/', views.sync_expiry_reminders_view, name='sync_expiry_reminders_view'),
    path('expiry-reminders/create-custom/', views.create_and_send_customer_expiry_reminders, name='create_and_send_customer_expiry_reminders'),
    path('api/customer-medicines-for-reminder/', views.api_customer_medicines_for_reminder, name='api_customer_medicines_for_reminder'),

    # Customer purchase history (JSON for AJAX)
    path('customer/<int:customer_id>/purchase-history/', views.customer_purchase_history_json, name='customer_purchase_history_json'),
    
    # Supplier
    path('supplier/', views.supplier_list, name='supplier_list'),
    path('supplier/add/', views.add_supplier, name='add_supplier'),
    path('supplier/<int:id>/edit/', views.edit_supplier, name='edit_supplier'),
    path('supplier/<int:id>/delete/', views.delete_supplier, name='delete_supplier'),
    path('supplier/<int:id>/', views.supplier_profile, name='supplier_profile'),
    path('supplier/<int:id>/export-stock/', views.export_supplier_stock, name='export_supplier_stock'),
    
    # AJAX APIs
    path('api/medicine-batches/', views.get_medicine_batches, name='get_medicine_batches'),
    path('api/search-medicines/', views.search_medicines, name='search_medicines'),
    path('api/search-customers/', views.search_customers, name='search_customers'),
    path('api/search-suppliers/', views.search_suppliers, name='search_suppliers'),
    path('api/chatbot/', views.chatbot_api, name='chatbot_api'),

    # Reports
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('profit-loss/', views.profit_loss_report, name='profit_loss_report'),
    path('payment-mode/', views.payment_mode_report, name='payment_mode_report'),
    path('reports/api/payment-mode/', views.payment_mode_data, name='payment_mode_data'),
    path('reports/api/top-products/', views.top_selling_products_data, name='top_products_data'),
    path('reports/api/sales-over-time/', views.total_sales_over_time_data, name='sales_over_time_data'),
    path('reports/api/profit-loss/', views.profit_loss_data, name='profit_loss_data'),
    path('reports/api/customer-registrations/', views.customer_registrations_data, name='customer_registrations_data'),
    path('reports/api/inventory-additions/', views.inventory_additions_data, name='inventory_additions_data'),
    
    # Excel exports (all charts)
    path('reports/export/top-products/', views.export_top_products_excel, name='export_top_products'),
    path('reports/export/sales-over-time/', views.export_sales_over_time_excel, name='export_sales_over_time'),
    path('reports/export/customer-registrations/', views.export_customer_registrations_excel, name='export_customer_registrations'),
    path('reports/export/inventory-additions/', views.export_inventory_additions_excel, name='export_inventory_additions'),

    # Smart Sales Analytics
    path('analytics/', views.smart_analytics, name='smart_analytics'),
    path('api/smart-analytics/', views.smart_analytics_data, name='smart_analytics_data'),

    # AI Demand Forecasting
    path('forecast/', views.demand_forecasting_view, name='demand_forecasting'),
    path('forecast/send-alert/', views.trigger_critical_stock_alert_now, name='trigger_critical_stock_alert_now'),
    path('api/forecast/<int:medicine_id>/', views.api_medicine_forecast, name='api_medicine_forecast'),
]

