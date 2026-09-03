from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Medicine, Batch, Customer, Supplier, Sale, MedicineReminder, Category

class UserRegistrationForm(UserCreationForm):
    """Form for user registration"""

    # Override password fields so they get the form-input CSS class
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Enter password'}),
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Confirm password'}),
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'contact_number', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. john_pharmacist'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'staff@pharmacy.com'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+91 9876543210'}),
        }


class MedicineForm(forms.ModelForm):
    """Form for adding/editing medicine"""
    class Meta:
        model = Medicine
        fields = ['name', 'category', 'description', 'supplier', 'price', 'reorder_threshold', 'preferred_supplier', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Medicine Name',
                'required': True
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Description',
                'rows': 3
            }),
            'supplier': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
                'required': True
            }),
            'reorder_threshold': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '10',
                'min': '0'
            }),
            'preferred_supplier': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 text-indigo-600 transition duration-150 ease-in-out',
            }),
        }


class BatchForm(forms.ModelForm):
    """Form for adding/editing batch"""
    class Meta:
        model = Batch
        fields = ['batch_name', 'add_date', 'expiry_date', 'quantity', 'purchase_price']
        widgets = {
            'batch_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Batch Name',
                'required': True
            }),
            'add_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'expiry_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Quantity',
                'min': '0',
                'required': True
            }),
            'purchase_price': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
                'required': True
            }),
        }


class CustomerForm(forms.ModelForm):
    """Form for adding/editing customer"""
    class Meta:
        model = Customer
        fields = ['name', 'email', 'contact_number', 'is_permanent']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Customer Name',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'customer@email.com',
                'required': True
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Contact Number',
                'required': True
            }),
            'is_permanent': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
        }


class SupplierForm(forms.ModelForm):
    """Form for adding/editing supplier"""
    class Meta:
        model = Supplier
        fields = ['name', 'location', 'description', 'contact_number', 'email']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Supplier Name',
                'required': True
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Location',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Description',
                'rows': 3
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Contact Number',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'supplier@email.com',
                'required': True
            }),
        }




class MedicineReminderForm(forms.ModelForm):
    class Meta:
        model = MedicineReminder
        fields = ['medicine', 'reminder_text', 'period', 'custom_days', 'send_at']
        widgets = {
            'send_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'reminder_text': forms.Textarea(attrs={'rows': 3}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'e.g. Antibiotics'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 3, 'placeholder': 'Optional description'}),
        }
