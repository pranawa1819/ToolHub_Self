from django.contrib import admin
from hardware.models import Product, Category, cartOrder,cartOrderItem, Wishlist, Order, ProductImage,Product_Review
# Register your models here.

class ProductImageAdmin(admin.TabularInline):
    model = ProductImage
    extra = 1

class productAdmin(admin.ModelAdmin):
    inlines = [ProductImageAdmin]
    list_display = ['pid','user', 'name','product_image','price','featured','product_status']
    
class CatogeryAdmin(admin.ModelAdmin):
    list_display =['cid','name', 'category_image','description']
    readonly_fields = ['category_image']
    
class cartOrderAdmin(admin.ModelAdmin):
    list_display =['user','price','paid_status','order_date','order_status']

class cartOrderItemAdmin(admin.ModelAdmin):
    list_display =['order','invoice_no','item','image','quantity','price','total']
    
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['user','product','review','rating']
    
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user','product','created_at']
    
class OrderAdmin(admin.ModelAdmin):
    list_display = ['full_name','phone','address','delivery_area','payment_method','created_at','total_amount']

  
admin.site.register(Product, productAdmin)
admin.site.register(Category,CatogeryAdmin)
admin.site.register(cartOrder,cartOrderAdmin)
admin.site.register(cartOrderItem,cartOrderItemAdmin)
admin.site.register(Product_Review,ProductReviewAdmin)
admin.site.register(Wishlist,WishlistAdmin)
admin.site.register(Order,OrderAdmin)