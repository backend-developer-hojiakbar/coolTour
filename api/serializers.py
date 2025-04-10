# api/serializers.py
from rest_framework import serializers
from .models import User, Vibe, Service, Guide, CarRental, Plan, DailyPlan, Booking, RecommendedLocation

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'user_type', 'fio', 'address', 'company_name', 'profile_image']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['phone_number', 'password', 'user_type', 'fio', 'address', 'company_name', 'profile_image']

    def create(self, validated_data):
        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            password=validated_data['password'],
            user_type=validated_data.get('user_type', 'traveller'),
            fio=validated_data.get('fio', ''),
            address=validated_data.get('address', ''),
            company_name=validated_data.get('company_name', ''),
            profile_image=validated_data.get('profile_image', None)
        )
        return user

class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)

class VibeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vibe
        fields = ['id', 'name']

class ServiceSerializer(serializers.ModelSerializer):
    service_vibe = VibeSerializer()

    class Meta:
        model = Service
        fields = ['id', 'agency', 'name', 'place', 'description', 'duration', 'price', 'category', 'image', 'travellers', 'service_vibe', 'created_at']

class GuideSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guide
        fields = ['id', 'agency', 'name', 'bio', 'experience', 'skills', 'price', 'image', 'created_at']

class CarRentalSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarRental
        fields = ['id', 'agency', 'name', 'price_per_day', 'category', 'features', 'image', 'created_at']

class DailyPlanSerializer(serializers.ModelSerializer):
    service = ServiceSerializer()

    class Meta:
        model = DailyPlan
        fields = ['id', 'day', 'service']

class RecommendedLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendedLocation
        fields = ['id', 'name', 'place', 'description', 'image_url', 'source']

# api/serializers.py
# api/serializers.py
# api/serializers.py
class PlanSerializer(serializers.ModelSerializer):
    vibes = serializers.PrimaryKeyRelatedField(queryset=Vibe.objects.all(), many=True)
    daily_plans = DailyPlanSerializer(many=True, read_only=True)
    recommended_locations = RecommendedLocationSerializer(many=True, read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)  # user maydonini read_only qilamiz

    class Meta:
        model = Plan
        fields = ['id', 'user', 'place', 'start_date', 'end_date', 'budget', 'travellers', 'vibes', 'daily_plans', 'recommended_locations', 'created_at']

class BookingSerializer(serializers.ModelSerializer):
    plan = PlanSerializer()
    guide = GuideSerializer()
    car_rental = CarRentalSerializer()

    class Meta:
        model = Booking
        fields = ['id', 'user', 'plan', 'guide', 'car_rental', 'start_time', 'end_time', 'num_people', 'status', 'total_price', 'created_at']

    def create(self, validated_data):
        plan = validated_data.get('plan')
        guide = validated_data.get('guide')
        car_rental = validated_data.get('car_rental')
        start_time = validated_data.get('start_time')
        end_time = validated_data.get('end_time')

        daily_plans = plan.daily_plans.all()
        services_price = sum(dp.service.price for dp in daily_plans)
        guide_price = guide.price if guide else 0
        days = (end_time - start_time).days + 1
        car_rental_price = car_rental.price_per_day * days if car_rental else 0
        total_price = services_price + guide_price + car_rental_price
        validated_data['total_price'] = total_price

        return super().create(validated_data)