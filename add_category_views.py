import os

path = 'd:/pharmacy_dashboard/MediApp/views.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

new_views = """
@pharmacist_or_admin
def category_list(request):
    \"\"\"List all medicine categories\"\"\"
    query = request.GET.get('q', '')
    if query:
        categories = Category.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        ).annotate(medicine_count=Count('medicines')).order_by('name')
    else:
        categories = Category.objects.annotate(medicine_count=Count('medicines')).order_by('name')
        
    return render(request, 'category/category_list.html', {
        'categories': categories,
        'search_query': query
    })

@pharmacist_or_admin
def add_category(request):
    \"\"\"Add a new category\"\"\"
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category {category.name} added successfully!')
            return redirect('category_list')
    else:
        form = CategoryForm()
        
    return render(request, 'category/add_category.html', {'form': form})

@pharmacist_or_admin
def edit_category(request, id):
    \"\"\"Edit an existing category\"\"\"
    category = get_object_or_404(Category, id=id)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category {category.name} updated successfully!')
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
        
    return render(request, 'category/edit_category.html', {
        'form': form,
        'category': category
    })

@admin_required
def delete_category(request, id):
    \"\"\"Delete a category\"\"\"
    category = get_object_or_404(Category, id=id)
    
    if request.method == 'POST':
        if category.medicines.exists():
            messages.error(request, 'Cannot delete category because it has associated medicines.')
        else:
            name = category.name
            category.delete()
            messages.success(request, f'Category {name} deleted successfully!')
        return redirect('category_list')
        
    return render(request, 'category/delete_category.html', {'category': category})
"""

if 'def category_list' not in content:
    content += new_views
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added category views")
else:
    print("Already exists")
