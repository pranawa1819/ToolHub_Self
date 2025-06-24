from .models import ProductView
from django.utils import timezone

def track_product_view(user, product):
    if user.is_authenticated:
        # Update existing view or create new one
        ProductView.objects.update_or_create(
            user=user,
            product=product,
            defaults={'viewed_at': timezone.now()}
        )