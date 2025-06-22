from django.shortcuts import render, redirect
from django.http import HttpResponse
from hardware.models import Product, Category, cartOrder,cartOrderItem, Wishlist, ProductImage,Product_Review
from hardware.form import ReviewForm , OrderForm
from django.contrib.auth.models import User
import uuid
from decimal import Decimal

# Create your views here.
def index(request):
    #return HttpResponse("welcome to my shop")
    featured_products = Product.objects.filter(featured=True)
    context={
       'featured_products': featured_products
       }
    return render(request, 'hardware/index.html',context)

def landingpage(request):
    return render(request, 'hardware/landingpage.html')

def signuppage(request):
    return render(request, 'userauths/sign-up.html')

def loginpage(request):
    return render(request, 'userauths/login.html')

def profilepage(request):
    return render(request, 'hardware/profile.html')

def collectionpage(request):
    
    categories = Category.objects.all()
    context ={
        'categories': categories
    }
    
    return render(request, 'hardware/collection.html',context)

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


def productDetailpage(request, pid):
    product = Product.objects.get(pid=pid)  # get() returns a single product
    reviews = Product_Review.objects.filter(product=product)
    

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


def remove_from_cart(request, pid):
    cart_item = cartOrderItem.objects.get(id=pid, user=request.user)

    cart_order = cart_item.order
    cart_item.delete()

    # Recalculate order price
    remaining_items = cartOrderItem.objects.filter(order=cart_order)
    cart_order.price = sum(item.total for item in remaining_items)
    cart_order.save()

    return redirect('hardware:cart')

def checkoutpage(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'checkout_success.html')  # Create this template for success page
        
    else:
        form = OrderForm()
    return render(request, 'hardware/checkout.html', {'form': form})


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