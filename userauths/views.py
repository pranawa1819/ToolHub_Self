from django.shortcuts import render, redirect
from userauths.form import UserRegisterForm
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth import get_user_model
# Create your views here.
User = get_user_model() 
#User = settings.AUTH_USER_MODEL
def register_view(request):
    
    if request.method == "POST":
        form = UserRegisterForm(request.POST or None) 
        if form.is_valid():
           new_user= form.save()
           username=form.cleaned_data.get('username')
           messages.success(request,f"Hey {username}, your account has been created successfully")
           new_user = authenticate(username=form.cleaned_data['email'], password=form.cleaned_data['password1'])
           login(request, new_user)
           return redirect("hardware:index")
    else:
        print("User cannot be registered")
        form = UserRegisterForm()
        

    context ={
        'form': form,
    }
    return render(request, 'userauths/sign-up.html',context)

def login_view(request):
    if request.user.is_authenticated:
        messages.warning(request, "You are already logged in")
        return redirect("hardware:index")
    
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, email=email, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, "You are logged in successfully")
                return redirect("hardware:index")
            else:
                messages.error(request, "Invalid email or password")  # Changed to error
                
        except User.DoesNotExist:
            messages.error(request, f"User with email {email} does not exist")  # Changed to error
    
    return render(request, 'userauths/login.html')
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully")
    return redirect("userauths:login")