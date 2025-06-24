from django.contrib import admin
from userauths.models import User

# Register your models here.
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'avatar')
    
admin.site.register(User,UserAdmin)