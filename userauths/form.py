from django import forms  # it helps to create forms in Django that can be used in views and templates
from django.contrib.auth.forms import UserCreationForm # it provides a form for creating new users
from userauths.models import User # it imports the User model defined in models.py

class UserRegisterForm(UserCreationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={ 'placeholder': 'Username'})) #it creates a text input field for the username with a placeholder
    email= forms.EmailField(widget=forms.EmailInput(attrs={ 'placeholder': 'Email'})) # it creates an email input field with a placeholder
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={ 'placeholder': 'Password'})) # it creates a password input field for the first password
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={ 'placeholder': 'Confirm Password'})) # it creates a password input field for confirming the password
    
    class Meta:
        model = User  # specifies the model to use for the form
        fields = ['username', 'email', 'password1', 'password2'] # fields to include in the form

    