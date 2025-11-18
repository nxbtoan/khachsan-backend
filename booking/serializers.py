from rest_framework import serializers
from .models import Room, Booking

class RoomSerializer(serializers.ModelSerializer):
    """Dịch Room model sang JSON"""
    class Meta:
        model = Room
        fields = '__all__'

class BookingSerializer(serializers.ModelSerializer):
    """Dịch Booking model sang JSON"""

    # Thêm dòng này để nó hiển thị tên phòng, thay vì chỉ ID phòng
    room_name = serializers.CharField(source='room.name', read_only=True)

    class Meta:
        model = Booking
        # Chọn các trường bạn muốn xem khi test
        fields = [
            'id', 
            'room_name', 
            'start_date', 
            'end_date', 
            'customer_email', 
            'shopify_order_id', 
            'status',
            'created_at'
        ]