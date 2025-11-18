from django.db import models

class Room(models.Model):
    shopify_product_id = models.BigIntegerField(
        unique=True, 
        help_text="ID của Product tương ứng trên Shopify"
    )
    name = models.CharField(max_length=255)
    max_guests = models.IntegerField(default=1, help_text="Số khách tối đa")
    area = models.IntegerField(default=0, help_text="Diện tích (m²)")

    def __str__(self):
        return self.name

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]

    room = models.ForeignKey(
        Room, 
        on_delete=models.PROTECT,
        related_name="bookings"
    )
    start_date = models.DateField(help_text="Ngày check-in")
    end_date = models.DateField(help_text="Ngày check-out")
    customer_email = models.EmailField(help_text="Email của khách hàng")
    shopify_order_id = models.BigIntegerField(
        unique=True, 
        null=True,
        blank=True, 
        help_text="ID của Order tương ứng trên Shopify"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"Booking {self.id} - {self.room.name} ({self.start_date} to {self.end_date})"