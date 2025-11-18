from django.contrib import admin
from .models import Room, Booking

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'shopify_product_id', 'max_guests', 'area')
    search_fields = ('name', 'shopify_product_id')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('room', 'start_date', 'end_date', 'customer_email', 'status', 'shopify_order_id')
    list_filter = ('status', 'room')
    search_fields = ('customer_email', 'shopify_order_id')