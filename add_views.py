import os
from datetime import timedelta, datetime
import json

path = 'd:/pharmacy_dashboard/MediApp/views.py'
with open(path, 'r') as f:
    content = f.read()

new_views = """
@assistant_or_above
def payment_mode_report(request):
    \"\"\"Standalone view for displaying Payment Mode Tracking\"\"\"
    return render(request, 'reports/payment_mode_report.html')

@role_required(['admin', 'assistant'])
def payment_mode_data(request):
    \"\"\"API for payment mode distribution\"\"\"
    filter_type = request.GET.get('filter', 'month')
    today = timezone.now().date()
    
    start_date = today
    end_date = today
    
    if filter_type == 'today':
        start_date = today
    elif filter_type == 'week':
        start_date = today - timedelta(days=7)
    elif filter_type == 'month':
        start_date = today - timedelta(days=30)
    elif filter_type == 'year':
        start_date = today - timedelta(days=365)
    elif filter_type == 'custom':
        start_str = request.GET.get('start_date')
        end_str = request.GET.get('end_date')
        if start_str and end_str:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
            
    sales = Sale.objects.filter(
        date__date__gte=start_date,
        date__date__lte=end_date,
        status='Completed'
    ).values('payment_method').annotate(
        total_amount=Sum('total_price'),
        count=Count('id')
    ).order_by('-total_amount')
    
    labels = []
    amounts = []
    counts = []
    
    for item in sales:
        labels.append(item['payment_method'])
        amounts.append(float(item['total_amount'] or 0))
        counts.append(item['count'])
        
    return JsonResponse({
        'labels': labels,
        'amounts': amounts,
        'counts': counts
    })
"""

if 'def payment_mode_report' not in content:
    content += new_views
    with open(path, 'w') as f:
        f.write(content)
    print("Added views")
else:
    print("Already exists")
