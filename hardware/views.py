from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse,HttpResponseBadRequest
from hardware.models import Product, Category, cartOrder,cartOrderItem, Wishlist, ProductImage,Product_Review,Order,OrderItem,ProductView,SearchHistory
from hardware.form import ReviewForm , OrderForm
from django.contrib.auth.models import User
import uuid
from decimal import Decimal
from django.contrib import messages
from django.core.mail import send_mail
from .utils import track_product_view
from django.contrib.auth import update_session_auth_hash
from django.conf import settings
from django.views.static import serve
from django.urls import reverse
import hmac
import hashlib
import base64
import json
from .recommender import build_user_item_matrix, knn_recommend
from .recommender import recommend_for_user



# # view for index page.
def index(request):
    featured_products = Product.objects.filter(featured=True)

    # ---------- KNN based recommendations ----------
    if request.user.is_authenticated:
        recommendations = recommend_for_user(request.user, top_n=8)
    else:
        # Fall back to globally featured products for anonymous users
        recommendations = Product.objects.filter(featured=True)[:4]

    context = {
        'featured_products': featured_products,
        'products': Product.objects.all(),
        'recommendations': recommendations,
    }
    return render(request, 'hardware/index.html', context)

#view for landing page
def landingpage(request):
    return render(request, 'hardware/landingpage.html')

#view for signup page
def signuppage(request):
    return render(request, 'userauths/sign-up.html')


#view for login page 
def loginpage(request):
    return render(request, 'userauths/login.html')


#view for aboutus page
def aboutpage(request):
    return render(request, 'hardware/aboutus.html')


#view for contact page
def contactpage(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        full_message = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"

        send_mail(
            subject,
            full_message,
            email,
            ['toolhubofficial@example.com'],  # Your business email
            fail_silently=False,
        )
        messages.success(request, "Message sent successfully!")
    return render(request, 'hardware/contact.html')



#view for profile page
def profilepage(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    user = request.user 
    orders = cartOrder.objects.filter(user=request.user).order_by('-order_date')  #Fetch all user orders.
    
    for order in orders:
        order.items = cartOrderItem.objects.filter(order=order)    #
    
    # Get 4 most recently viewed products
    recently_viewed = Product.objects.filter(
        productview__user=user
    ).order_by('-productview__viewed_at').distinct()[:4]
    
    context = {
        'user': user,
        'orders': orders,
        'recently_viewed': recently_viewed,
        'MEDIA_URL': settings.MEDIA_URL
    }
    return render(request, 'hardware/profile.html', context)


#view for update profile page
def updateprofilepage(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    user = request.user
    
    if request.method == "POST":
        # Update basic info
        user.username = request.POST.get("username")
        user.email = request.POST.get("email")
        
        # Handle profile image upload
        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']
        
        # Handle password change
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")
        
        if new_password and confirm_password:
            if new_password == confirm_password:
                user.set_password(new_password)
                update_session_auth_hash(request, user)  # Keep the user logged in
                messages.success(request, "Password updated successfully!")
            else:
                messages.error(request, "Passwords don't match!")
        
        user.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('hardware:profile')

    context = {
        'user': user,
    }
    return render(request, 'hardware/update.html', context)



#view for collection page
def collectionpage(request):
    
    categories = Category.objects.all()
    context ={
        'categories': categories
    }
    
    return render(request, 'hardware/collection.html',context)



#view for product category pages
def powertools(request):
    products = Product.objects.filter(category__name='Power Tools')
    context = {
        'products': products
    }
    
    return render(request, 'hardware/powertool.html', context)




def handTools(request):
    products = Product.objects.filter(category__name='Hand Tools')
    context = {
        'products': products
    }
    
    return render(request, 'hardware/handtool.html', context)

def gardenTools(request):
    products = Product.objects.filter(category__name='Garden & Outdoor')
    context = {
        'products': products
    } 
    
    return render(request, 'hardware/gardentool.html', context)

def plumbingTools(request):
    products = Product.objects.filter(category__name='Plumbing Supplies')
    context = {
        'products': products
    }
    
    return render(request, 'hardware/plumbingtool.html', context)

def electricalTools(request):
    
    products = Product.objects.filter(category__name='Electrical Supplies')
    context = {
        'products': products
    }
    
    return render(request, 'hardware/electricaltool.html', context)

def measuringTools(request):
    products = Product.objects.filter(category__name='Measuring Tools')
    context = {
        'products': products
    }
    
    return render(request, 'hardware/Measuringtool.html', context)

def agricultureTools(request):
    products = Product.objects.filter(category__name='Agricultural Tools')
    context = {
        'products': products
    }
    
    return render(request, 'hardware/agriculturaltool.html', context)

def bathroomTools(request):
    products = Product.objects.filter(category__name='Bathroom utensils')
    context = {
        'products': products
    }
    
    return render(request, 'hardware/bathroom.html', context)


#view for product details page
def productDetailpage(request, pid):
    product = Product.objects.get(pid=pid)  # get() returns a single product
    reviews = Product_Review.objects.filter(product=product)
    track_product_view(request.user, product)
    
    #similar_products = recommend_similar_to_product(product.pid)
    similar_products = []
    if request.method == "POST":
        review = request.POST.get('review')
        rating = request.POST.get('rating')
        form = ReviewForm(request.POST)  # populate with POST data
        if review and rating:
            Product_Review.objects.create(  # Correct Model, not Form here
                product=product,        
                user=request.user,     
                review=review,
                rating=rating,
            )
            return redirect('hardware:productdetail', pid=pid)
    else:
        form = ReviewForm()  # define empty form for GET requests

    context = {
        'product': product,
        'reviews': reviews,
        'form': form,  # now always defined
        #'similar_products': similar_products
    }

    return render(request, 'hardware/productdetails.html', context)


#view for add to cart page
def add_to_cart(request, pid):
    product = Product.objects.get( pid=pid)

    # Check if cartOrder exists (processing status only)
    cart_order, created = cartOrder.objects.get_or_create(
        user=request.user,
        order_status='processing',
        defaults={
            'price': 0  # Initialize price to 0
            
        },
        
    )

   # Check if item already exists in cartOrderItem
    cart_item, created_item = cartOrderItem.objects.get_or_create(
        user=request.user,
        order=cart_order,
        item=product,
        defaults={
            'invoice_no': str(uuid.uuid4()),  
            'product_status': 'processing',
            'image': product.image, 
            'quantity': 1,
            'price': product.price,
            'total': product.price
        }
    )

    if not created_item:
        cart_item.quantity += 1
        cart_item.total = cart_item.price * cart_item.quantity
        cart_item.save()

    # Update cartOrder price (grand total)
    cart_items = cartOrderItem.objects.filter(order=cart_order)
    cart_order.price = sum(item.total for item in cart_items)
    cart_order.save()
    messages.success(request, f"{product.name} has been added to your cart.")

    return redirect(request.META.get('HTTP_REFERER', 'hardware:index'))



#view for cart view 
def cart_view(request):
    cart_items = cartOrderItem.objects.filter(user=request.user, product_status='processing')

    subtotal = sum(item.total for item in cart_items)
    vat = subtotal * Decimal('0.13')   # Correct: Decimal * Decimal
    grand_total = subtotal + vat
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'vat': vat,
        'grand_total': grand_total,
    }
    return render(request, 'hardware/cart.html', context )


#view for remove item from cart
def remove_from_cart(request, pid):
    cart_item = cartOrderItem.objects.get(id=pid, user=request.user)

    cart_order = cart_item.order
    cart_item.delete()
    
    if cart_order.paid_status == True and cart_order.order_status == 'Completed':
        cart_item.delete()  # Delete the item
        
    # Recalculate order price
    remaining_items = cartOrderItem.objects.filter(order=cart_order)
    cart_order.price = sum(item.total for item in remaining_items)
    cart_order.save()

    return redirect('hardware:cart')


#view for search
def searchs(request):
    query = request.GET.get('query', '')
    category_name = request.GET.get('category')
    categories = Category.objects.all()
    products = Product.objects.all()

    if query:
        SearchHistory.objects.create(user=request.user, query=query)
        products = products.filter(name__icontains=query)

    if category_name:
        products = products.filter(category__name=category_name)

    # Recommend similar products based on category if at least one result is found
    recommended_products = []
    if products.exists():
        category = products.first().category
        recommended_products = Product.objects.filter(category=category).exclude(
            pid__in=products.values_list('pid', flat=True)
        )

    context = {
        'products': products,
        'recommended_products': recommended_products,
        'categories': categories,
    }
    return render(request, 'hardware/search.html', context)



#view for checkout page
def checkoutpage(request):
    user = request.user
    cart_order = cartOrder.objects.filter(user=user, paid_status=False, order_status='processing').first()
    
    if not cart_order:
        messages.error(request, "No active cart found!")
        return redirect('hardware:cart')

    # Filter out items whose order_status is 'Ordered' (already placed)
    cart_items = cartOrderItem.objects.filter(
        user=user, 
        order=cart_order
    ).exclude(order__order_status='ordered')  # skip 'Ordered' items in billing

    # Billing calculation
    subtotal = sum(item.total for item in cart_items)
    vat = subtotal * Decimal('0.13')
    delivery_charge = Decimal('100.00')  # default
    total_amount = subtotal + vat + delivery_charge


    last_order = Order.objects.filter(user=user).last()
    initial_data = {}
    if last_order:
        initial_data = {
            'full_name': last_order.full_name,
            'phone': last_order.phone,
            'address': last_order.address,
            'delivery_area': last_order.delivery_area,
            'notes': last_order.notes,
        }

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = user
            order.subtotal = subtotal
            order.vat = vat

            delivery_area = form.cleaned_data['delivery_area']
            delivery_charge = Decimal('100.00') if delivery_area == 'Inside Valley' else Decimal('150.00')

            order.delivery_charge = delivery_charge
            order.total_amount = subtotal + vat + delivery_charge
            order.save()

            # Save order items
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    item=item.item,
                    quantity=item.quantity,
                    price=item.price,
                    total=item.total
                )

            if order.payment_method == 'Cash on Delivery':
                cart_order.paid_status = False
                cart_order.order_status = 'ordered'
            elif order.payment_method == 'Esewa':
               cart_order.paid_status = True
               cart_order.order_status = 'ordered'
               return redirect(
                 reverse('hardware:esewa-request') + 
                 "?order_id=" + 
                 str(order.id)
                )
            
               

            cart_order.save()
            return redirect('hardware:order_confirmation', id=order.id)
    else:
        form = OrderForm(initial=initial_data)

    return render(request, 'hardware/checkout.html', {
        'form': form,
        'cart_order': cart_order,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'vat': vat,
        'delivery_charge': delivery_charge,
        'grand_total': total_amount
    })


#view for order confirmation page
def order_confirmation(request, id):
    order = get_object_or_404(Order, id=id, user=request.user)
    
    # Get all paid cartOrders of the user
    paid_cart_orders = cartOrder.objects.filter(user=request.user, paid_status=True)
    
    if not paid_cart_orders.exists():
        #messages.error(request, "No completed cart order found!")
        return redirect('hardware:cart')
    
    # Get all cart items related to those paid cartOrders
    cart_items = cartOrderItem.objects.filter(user=request.user, order__in=paid_cart_orders)

    # Delete all these cart items
    cart_items.delete()

    # Clear session order_id if exists
    if 'order_id' in request.session:
        del request.session['order_id']

    order_items = OrderItem.objects.filter(order=order)

    return render(request, 'hardware/order_confirmation.html', {
        'order': order,
        'order_items': order_items
    })







#view for eSewa payment request


def esewa_request(request):
    if request.method == 'GET':
        # Get order ID from request
        order_id = request.GET.get('order_id') or request.GET.get('id')
        if not order_id:
            return HttpResponseBadRequest("Missing order ID")
            
        order = get_object_or_404(Order, id=order_id)
        
        request.session['order_id'] = order.id
        cart_order = cartOrder.objects.filter(user=request.user, paid_status=False).first()
        if cart_order:
            request.session['cart_order_id'] = cart_order.id
            
        # Configuration - use test credentials for development
        SECRET_KEY = "8gBm/:&EnhH.1/q" # Test secret key from eSewa
        PRODUCT_CODE = "EPAYTEST"        # Test product code
        
        # Calculate amounts (must be strings with exactly 2 decimal places)
        amount = "%.2f" % float(order.subtotal)
        tax_amount = "%.2f" % float(order.vat)
        service_charge = "0.00"
        delivery_charge = "100.00"  
        total_amount = "%.2f" % (float(amount) + float(tax_amount) + 
                      float(service_charge) + float(delivery_charge))
        
        # Generate transaction UUID (alphanumeric + hyphen only)
        transaction_uuid = str(uuid.uuid4()).replace('_', '-')[:20]

        # 1. Prepare EXACTLY these 3 fields in THIS ORDER for signing
        signed_keys = ["total_amount", "transaction_uuid", "product_code"]
        signed_data = {
            "total_amount": total_amount,
            "transaction_uuid": transaction_uuid,
            "product_code": PRODUCT_CODE,
        }

        # 2. Create message string in EXACT format and order (NO SPACES)
        message = ",".join([f"{key}={signed_data[key]}" for key in signed_keys])

        # 3. Generate HMAC-SHA256 signature (MUST use this exact sequence)
        signature = base64.b64encode(
            hmac.new(
                SECRET_KEY.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256
            ).digest()
        ).decode("utf-8")

        # Prepare complete payload (all values as string, 2 decimal places)
        payload = {
            "amount": str(amount),
            "tax_amount": str(tax_amount),
            "product_service_charge": str(service_charge),
            "product_delivery_charge": str(delivery_charge),
            "total_amount": str(total_amount),
            "transaction_uuid": transaction_uuid,
            "product_code": PRODUCT_CODE,
            "success_url": request.build_absolute_uri(reverse('hardware:payment-success')),
            "failure_url": request.build_absolute_uri(reverse('hardware:payment-failure')),
            "signed_field_names": ",".join(signed_keys),  # MUST match signed_data keys and order
            "signature": signature,
        }
        
       
        return render(request, 'hardware/esewa-request.html', {'payload': payload})


def payment_success(request):
    data_encoded = request.GET.get('data')
    if not data_encoded:
        return HttpResponseBadRequest("Missing payment data")

    try:
        decoded_data = base64.b64decode(data_encoded).decode('utf-8')
        payment_data = json.loads(decoded_data)
    except Exception as e:
        return HttpResponseBadRequest("Invalid payment data")

    # Get order_id from session
    order_id = request.session.get('order_id')
    if not order_id:
        return HttpResponseBadRequest("Missing order ID from session")

    # Retrieve order
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Retrieve cart order
    cart_order = cartOrder.objects.filter(
        user=request.user,
        paid_status=False,
        order_status='processing'
    ).first()

    if not cart_order:
        return HttpResponseBadRequest("No matching cart order found")

    # Update cart order
    cart_order.paid_status = True
    cart_order.order_status = 'ordered'
    cart_order.save()

    # Update each cart item
    cart_items = cartOrderItem.objects.filter(user=request.user, order=cart_order)
    for item in cart_items:
        item.product_status = 'ordered'
        item.save()

    messages.success(request, "Payment successful!")

    return redirect('hardware:order_confirmation', id=order.id)


def payment_failure(request):
    messages.error(request, "Payment failed. Please try again.")
    
    # Clear session order_id if exists
    if 'order_id' in request.session:
        del request.session['order_id']
    
    # Clear cart order if exists
    if 'cart_order_id' in request.session:
        del request.session['cart_order_id']
    
    return redirect('hardware:cart')  # Redirect to cart or any other page













