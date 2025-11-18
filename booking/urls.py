from django.urls import path
from .views import AvailabilityAPIView, WebhookOrderPaidAPIView, AllBookingsAPIView

urlpatterns = [
    # Định nghĩa URL cho API
    # GET /api/availability/
    path('availability/', AvailabilityAPIView.as_view(), name='api-availability'),

    # POST /api/webhooks/order_paid/
    path('webhooks/order_paid/', WebhookOrderPaidAPIView.as_view(), name='api-webhook-order-paid'),

    # GET /api/all-bookings/
    path('all-bookings/', AllBookingsAPIView.as_view(), name='api-all-bookings'),
]