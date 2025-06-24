from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from hardware.models import Product, Category, cartOrder,cartOrderItem, Wishlist, ProductImage,Product_Review,Order,OrderItem,ProductView
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

# view for index page.
def index(request):
    #return HttpResponse("welcome to my shop")
    featured_products = Product.objects.filter(featured=True)
    context={
       'featured_products': featured_products
       }
    return render(request, 'hardware/index.html',context)

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
    orders = cartOrder.objects.filter(user=request.user).order_by('-order_date')
    
    for order in orders:
        order.items = cartOrderItem.objects.filter(order=order)
    
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




#view for product details page
def productDetailpage(request, pid):
    product = Product.objects.get(pid=pid)  # get() returns a single product
    reviews = Product_Review.objects.filter(product=product)
    track_product_view(request.user, product)

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
    }

    return render(request, 'hardware/productdetails.html', context)


#view for add to cart page
def add_to_cart(request, pid):
    product = Product.objects.get( pid=pid)

    # Check if cartOrder exists (processing status only)
    cart_order, created = cartOrder.objects.get_or_create(
        user=request.user,
        order_status='processing',
        defaults={'price': 0}
    )

    # Check if item already exists in cartOrderItem
    cart_item, created_item = cartOrderItem.objects.get_or_create(
        user=request.user,
        order=cart_order,
        item=product.name,
        defaults={
            'invoice_no': str(uuid.uuid4()),  # generate unique invoice
            'product_status': 'processing',
            'image': product.image,  # assumes Product has 'image' field
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

    return redirect('hardware:cart')  # cart page url name



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
                cart_order.order_status = 'completed'

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



def cancel_order(request, id):
    cart_order = get_object_or_404(cartOrder, user=request.user, id=id)

    if cart_order.order_status == 'Ordered' and not cart_order.paid_status:
        cart_order.order_status = 'Canceled'
        cart_order.save()

        # Delete only this order's items
        cart_items = cartOrderItem.objects.filter(user=request.user, order=cart_order)
        cart_items.delete()

        messages.success(request, "Order has been canceled successfully.")
    else:
        messages.error(request, "Order cannot be canceled.")

    return redirect('hardware:cart')




#view for search
def searchs(request):
    query = request.GET.get('query', '')
    category_name = request.GET.get('category')
    categories = Category.objects.all()
    products = Product.objects.all()

    if query:
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