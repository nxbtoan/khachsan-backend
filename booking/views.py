import datetime
import hmac
import hashlib
import base64
import json
from calendar import monthrange

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Room, Booking

class AvailabilityAPIView(APIView):
    """
    API endpoint để kiểm tra lịch trống (availability).
    Nhận input: room_id (của Shopify), month, year
    Trả về: {"booked_dates": ["YYYY-MM-DD", ...]}
    """
    
    def get(self, request, *args, **kwargs):
        # 1. Lấy query params từ URL
        try:
            # Lấy room_id từ shopify_product_id
            shopify_id = request.query_params.get('room_id')
            month = int(request.query_params.get('month'))
            year = int(request.query_params.get('year'))
            
            if not all([shopify_id, month, year]):
                raise ValueError("Thiếu tham số room_id, month, hoặc year")

        except (TypeError, ValueError) as e:
            return Response(
                {"error": f"Tham số không hợp lệ: {e}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Tìm phòng trong CSDL
        try:
            room = Room.objects.get(shopify_product_id=shopify_id)
        except Room.DoesNotExist:
            return Response(
                {"error": f"Không tìm thấy phòng với shopify_product_id={shopify_id}"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. Tính toán ngày đầu và ngày cuối tháng
        try:
            first_day_of_month = datetime.date(year, month, 1)
            days_in_month = monthrange(year, month)[1]
            last_day_of_month = datetime.date(year, month, days_in_month)
        except ValueError:
            return Response(
                {"error": "Tháng hoặc năm không hợp lệ"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Truy vấn các booking "Confirmed" có-liên-quan-đến-tháng-này
        # Logic:
        # - start_date <= ngày cuối tháng
        # - end_date > ngày đầu tháng (vì end_date là ngày check-out, không tính)
        bookings = Booking.objects.filter(
            room=room,
            status='confirmed', # Chỉ lấy booking đã xác nhận
            start_date__lte=last_day_of_month,
            end_date__gt=first_day_of_month
        )

        # 5. Tạo danh sách các ngày đã bị đặt
        # Dùng set để tránh trùng lặp
        booked_dates_set = set()
        
        # Dùng timedelta để lặp qua các ngày
        one_day = datetime.timedelta(days=1)

        for booking in bookings:
            current_date = booking.start_date
            
            # Lặp từ start_date cho đến *trước* end_date
            while current_date < booking.end_date:
                # Chỉ thêm vào nếu ngày đó nằm trong tháng đang xét
                if first_day_of_month <= current_date <= last_day_of_month:
                    booked_dates_set.add(current_date.strftime("%Y-%m-%d"))
                
                current_date += one_day

        # 6. Trả về kết quả
        # Sắp xếp lại list trước khi trả về
        return Response(
            {"booked_dates": sorted(list(booked_dates_set))}, 
            status=status.HTTP_200_OK
        )
    
@method_decorator(csrf_exempt, name='dispatch')
class WebhookOrderPaidAPIView(APIView):
    """
    API endpoint để nhận tín hiệu (Webhook) "orders/paid" từ Shopify.
    [POST /api/webhooks/order_paid/]
    """
    
    def verify_webhook(self, request):
        """
        Xác thực chữ ký HMAC từ Shopify.
        """
        # Lấy header chữ ký từ Shopify
        shopify_hmac = request.headers.get('X-Shopify-Hmac-Sha256')
        
        # Lấy body của request
        request_body = request.body
        
        if not shopify_hmac:
            return False, "Thiếu header X-Shopify-Hmac-Sha256"

        try:
            # Lấy secret key từ settings
            secret = settings.SHOPIFY_WEBHOOK_SECRET
            
            # Tính toán hash
            digest = hmac.new(secret, request_body, hashlib.sha256).digest()
            
            # Mã hóa base64
            computed_hmac = base64.b64encode(digest)

            # So sánh an toàn (timing-safe comparison)
            return hmac.compare_digest(
                computed_hmac, 
                shopify_hmac.encode('utf-8')
            ), "Xác thực thành công"
            
        except Exception as e:
            return False, f"Lỗi xác thực HMAC: {e}"

    def post(self, request, *args, **kwargs):
        # 1. Xác thực HMAC (BẮT BUỘC) 
        is_valid, message = self.verify_webhook(request)
        
        if not is_valid:
            return Response(
                {"error": "Xác thực HMAC thất bại", "details": message}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 2. Đọc dữ liệu JSON từ Shopify [cite: 46]
        try:
            # Shopify gửi dữ liệu dưới dạng JSON
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return Response(
                {"error": "Không thể parse JSON từ body"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Xử lý Logic tạo Booking
        try:
            # Lấy thông tin chính
            shopify_order_id = data.get('id')
            customer_email = data.get('customer', {}).get('email')
            line_items = data.get('line_items', []) [cite: 47]

            if not all([shopify_order_id, customer_email, line_items]):
                return Response(
                    {"error": "Thiếu thông tin order_id, customer_email hoặc line_items"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 4. Lặp qua từng sản phẩm trong đơn hàng
            bookings_created = []
            for item in line_items:
                shopify_product_id = item.get('product_id')
                
                # Tìm 'properties' (check-in/check-out) mà ta đã gửi
                # từ Giai đoạn 3 [cite: 48]
                properties = {prop['name']: prop['value'] for prop in item.get('properties', [])}
                start_date_str = properties.get('Check-in')
                end_date_str = properties.get('Check-out')

                if not all([shopify_product_id, start_date_str, end_date_str]):
                    # Nếu item này không có properties (ví dụ: bán áo thun)
                    # thì bỏ qua
                    continue

                # Tìm phòng tương ứng trong CSDL
                try:
                    room = Room.objects.get(shopify_product_id=shopify_product_id)
                except Room.DoesNotExist:
                    # Ghi log lỗi (quan trọng) và bỏ qua item này
                    print(f"Lỗi Webhook: Không tìm thấy Room với product_id={shopify_product_id}")
                    continue

                # Parse ngày tháng
                start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()

                # 5. Tạo bản ghi Booking 
                booking = Booking.objects.create(
                    room=room,
                    start_date=start_date,
                    end_date=end_date,
                    customer_email=customer_email,
                    shopify_order_id=shopify_order_id,
                    status='confirmed' # Đánh dấu đã xác nhận 
                )
                bookings_created.append(booking.id)

            return Response(
                {"status": "Webhook xử lý thành công", "bookings_created": bookings_created}, 
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            # Bắt các lỗi chung (ví dụ: parse ngày tháng, lỗi CSDL)
            return Response(
                {"error": f"Lỗi xử lý logic webhook: {e}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )