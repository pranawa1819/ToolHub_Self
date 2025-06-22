from django import forms
from hardware.models import Product_Review, Order
from django.contrib.auth.models import User
class ReviewForm(forms.ModelForm):
    review =  forms.CharField(widget=forms.Textarea(attrs={'placeholder':"write review"}))
    class Meta:
        model = Product_Review
        fields = ['review', 'rating']
       
            
class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['full_name', 'phone', 'address', 'delivery_area', 'notes', 'payment_method']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Enter full name'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Enter 10-digit phone number'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter your address'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Additional notes (optional)'}),
        }   