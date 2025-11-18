from django.urls import path
from .views import AvailabilityAPIView, WebhookOrderPaidAPIView

urlpatterns = [
    # Định nghĩa URL cho API
    # GET /api/availability/
    path('availability/', AvailabilityAPIView.as_view(), name='api-availability'),

    # POST /api/webhooks/order_paid/
    path('webhooks/order_paid/', WebhookOrderPaidAPIView.as_view(), name='api-webhook-order-paid'),
]