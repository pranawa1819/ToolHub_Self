from unicodedata import decimal
from email.policy import default
from pyexpat import model
from django.db import models
from shortuuid.django_fields import ShortUUIDField
from django.utils.html import mark_safe
from userauths.models import User

STATUS_CHOICE =(
    ("processing", "Processing"),
    ("shipped", "Shipped"),
    ("delivered", "Delivered"),
    ("ordered", "Ordered"),
    ("cancelled", "Cancelled"),
    ("returned", "Returned"),
    ("refunded", "Refunded"),
    ("completed", "Completed"),
    ("pending", "Pending"),
    ("failed", "Failed"),
    ('', 'None'),
)

STATUS = (
    ("published", "Published"),
    ("Available", "Available"),
    ("draft", "Draft"),
    ("soldout", "SoldOut"),
    ('', 'None'),
)

Rating = (
    (1, " ★ ☆ ☆ ☆ ☆"),
    (2, " ★ ★ ☆ ☆ ☆"),
    (3, " ★ ★ ★ ☆ ☆"),
    (4, " ★ ★ ★ ★ ☆"),
    (5, " ★ ★ ★ ★ ★ "),
   
)

LABEL_CHOICES = (
    ('Hot', 'Hot'),
    ('Sale', 'Sale'),
    ('New', 'New'),
    ('', 'None'),
)
# Create your models here.

class Category(models.Model):
    cid = ShortUUIDField(unique=True, length = 10, max_length=20, prefix="cat", alphabet="abcdefgh12345") 
    name = models.CharField(max_length=100)
    image= models.ImageField(upload_to='categories/', null=True, blank=True)
    description = models.TextField(max_length=500, null=True, blank=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        
    def category_image(self):
        if self.image and hasattr(self.image, 'url'):
         return mark_safe(f'<img src="{self.image.url}" width="50" height="50" />')
        return "(No Image)" 
    
    def __str__(self):
        return self.name


#class Tag(models.Model):
   # pass


class Product(models.Model):
    pid = ShortUUIDField(primary_key=True,unique=True, length = 10, max_length=20, prefix="prod", alphabet="abcdefgh12345") 
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="user_directory_path") # used to store product image
    description = models.TextField(max_length=500, null=True, blank=True)
    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True,blank=True)
    label = models.CharField(choices=LABEL_CHOICES, max_length=10, blank=True)  # 'Hot', 'Sale', or empty
    specification = models.TextField(max_length=500, null=True, blank=True) 
    #tags =models.ForeignKey(Tag, on_delete=models.SET_NULL, null=True, blank=True) # used to tag products with specific keywords
    product_status = models.CharField(choices = STATUS, max_length=20) # used to check if product is new, used or refurbished
    status = models.CharField(max_length=50, default='Active')  # or any default value you want

    in_stock = models.BooleanField(default=True) #used to check if product is in stock
    featured = models.BooleanField(default=False) #used to check if product is featured
    created_at = models.DateTimeField(auto_now_add=True) # used to check when product was created
    updated_at = models.DateTimeField(auto_now=True) # used to check when product was updated
    
    class Meta:
        verbose_name_plural = "Products"
        
    def product_image(self):
        return mark_safe(f'<img src="{self.image.url}" width="50" height="50" />') 
    
    def __str__(self):
        return self.name
    
class ProductImage(models.Model):
    image = models.ImageField(upload_to='product-images/', null=True, blank=True)
    product= models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "ProductImages"
        
  
class cartOrder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null = True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    paid_status = models.BooleanField(default=False)
    order_date = models.DateTimeField(auto_now_add=True)
    order_status = models.CharField(choices=STATUS_CHOICE, max_length=20, default="processing")
    
    class Meta:
        verbose_name_plural = "Cart Orders"
  
    
class cartOrderItem(models.Model):
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null = True)
    order = models.ForeignKey(cartOrder, on_delete=models.CASCADE , null = True)
    invoice_no = models.CharField(max_length=200)
    product_status = models.CharField(max_length=200,choices=STATUS_CHOICE,default="null")
    item = models.CharField(max_length=200)
    image = models.ImageField(upload_to='cart_items/', null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    class Meta:
        verbose_name_plural = "Cart Order Items"
        
    def order_image(self):
        return mark_safe(f'<img src="{self.image.url}" width="50" height="50" />') 
    

class Product_Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null =True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null = True)
    review = models.TextField()
    rating = models.IntegerField(choices=Rating, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Product Reviews"
        
    def __str__(self):
        return self.product.name
    
    def get_rating(self):
        return self.rating
    

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null =True )
    product = models.ForeignKey(Product, to_field='pid', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Wishlists"
        
    def __str__(self):
        return self.product.title
    



class Order(models.Model):
    DELIVERY_CHOICES = (
        ('Inside Valley', 'Inside Valley'),
        ('Outside Valley', 'Outside Valley'),
    )

    PAYMENT_CHOICES = (
        ('Cash on Delivery', 'Cash on Delivery'),
        ('Esewa', 'Esewa'),
        ('Khalti', 'Khalti'),
    )
    id =  ShortUUIDField(primary_key=True,unique=True, length = 10, max_length=20, prefix="ord", alphabet="abcdefgh12345")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    delivery_area = models.CharField(max_length=20, choices=DELIVERY_CHOICES)
    notes = models.TextField(blank=True, null=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    vat = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name_plural = "Orders"
    def __str__(self):
        return f"{self.full_name} - {self.payment_method}"
    
class OrderItem(models.Model):
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    
    item = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.item
