from django.urls import path
from hardware.views import index
from hardware.views import landingpage


from . import views 

app_name = "hardware"

urlpatterns = [
   
    path("first/", index, name="index"),  # Home page
    
    path("", landingpage, name="landingpage"),  # Landing page
    
    path("sign-up/", views.signuppage, name="signuppage"),
    path("login/", views.loginpage, name="loginpage"),
    path('profile/', views.profilepage, name='profile'),  # This defines hardware:profile
    path('profile/update/', views.updateprofilepage, name='update_profile'),
    

    path("aboutus/",views.aboutpage, name="aboutpage"),
    
    path("contact/", views.contactpage, name="contactpage"),
    
    path("collection/", views.collectionpage, name="collectionpage"),
    
    path("powertool/", views.powertools, name="powertools"),
    path("handtool/", views.handTools, name="handTools"),
    path("gardentool/", views.gardenTools, name="gardenTools"),
    path("plumbingtool/", views.plumbingTools, name="plumbingTools"),
    path("electricaltool/", views.electricalTools, name="electricalTools"),
    path("measuringtool/", views.measuringTools, name="measuringTools"),
    path("agriculturaltool/", views.agricultureTools, name="agriculturalTools"),
    path("bathroom/", views.bathroomTools, name="bathroomTools"),
    
    path("productdetail/<str:pid>/", views.productDetailpage, name="productdetail"),
    
    path("cart/", views.cart_view, name="cart"),
    path("add_to_cart/<str:pid>/", views.add_to_cart, name="add_to_cart"),
    path("remove_from_cart/<str:pid>/", views.remove_from_cart, name="remove_from_cart"),
    
    path("checkout/", views.checkoutpage, name="checkoutpage"),
    
    # payment gateway URLs
    path('esewa-request/', views.esewa_request, name='esewa-request'),
    path('payment-success/', views.payment_success, name='payment-success'),
    path('payment-failure/', views.payment_failure, name='payment-failure'),
    
    
    
    
    path('orderconfirmation/<str:id>/', views.order_confirmation, name='order_confirmation'),
    
   
    
    path("search/", views.searchs, name="searchs"),
]
