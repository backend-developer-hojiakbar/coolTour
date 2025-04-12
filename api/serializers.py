# api/serializers.py
from rest_framework import serializers
from .models import User, Place, Budget, Vibe, Service, Guide, CarRental, Plan, DailyPlan, Booking, RecommendedLocation

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

class PlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = ['id', 'name', 'description', 'country', 'created_at']

class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = ['id', 'amount', 'currency', 'description', 'created_at']

class VibeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vibe
        fields = ['id', 'name']

class ServiceSerializer(serializers.ModelSerializer):
    service_vibe = VibeSerializer()
    place = PlaceSerializer()

    class Meta:
        model = Service
        fields = ['id', 'agency', 'name', 'place', 'description', 'duration', 'price', 'category', 'image', 'travellers', 'service_vibe', 'created_at']

class GuideSerializer(serializers.ModelSerializer):
    agency = UserSerializer()

    class Meta:
        model = Guide
        fields = ['id', 'agency', 'name', 'bio', 'experience', 'skills', 'price', 'image', 'created_at']

class CarRentalSerializer(serializers.ModelSerializer):
    agency = UserSerializer()

    class Meta:
        model = CarRental
        fields = ['id', 'agency', 'name', 'price_per_day', 'category', 'features', 'max_capacity', 'image', 'created_at']

class DailyPlanSerializer(serializers.ModelSerializer):
    service = ServiceSerializer()

    class Meta:
        model = DailyPlan
        fields = ['id', 'day', 'service']

class RecommendedLocationSerializer(serializers.ModelSerializer):
    place = PlaceSerializer()

    class Meta:
        model = RecommendedLocation
        fields = ['id', 'name', 'place', 'description', 'price', 'image_url', 'source']

class PlanSerializer(serializers.ModelSerializer):
    vibes = serializers.PrimaryKeyRelatedField(queryset=Vibe.objects.all(), many=True)
    place = serializers.PrimaryKeyRelatedField(queryset=Place.objects.all())
    budget = serializers.PrimaryKeyRelatedField(queryset=Budget.objects.all())
    daily_plans = DailyPlanSerializer(many=True, read_only=True)
    recommended_locations = RecommendedLocationSerializer(many=True, read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Plan
        fields = ['id', 'user', 'place', 'budget', 'start_date', 'end_date', 'travellers', 'vibes', 'daily_plans', 'recommended_locations', 'created_at']

class BookingSerializer(serializers.ModelSerializer):
    plan = PlanSerializer()
    guide = GuideSerializer()
    car_rentals = CarRentalSerializer(many=True)
    recommended_locations = RecommendedLocationSerializer(many=True)

    class Meta:
        model = Booking
        fields = ['id', 'user', 'plan', 'guide', 'car_rentals', 'recommended_locations', 'start_time', 'end_time', 'num_people', 'status', 'total_price', 'created_at']

    def create(self, validated_data):
        car_rentals_data = validated_data.pop('car_rentals', [])
        recommended_locations_data = validated_data.pop('recommended_locations', [])
        plan = validated_data.get('plan')
        guide = validated_data.get('guide')
        start_time = validated_data.get('start_time')
        end_time = validated_data.get('end_time')
        num_people = validated_data.get('num_people')

        # Narxni hisoblash
        daily_plans = plan.daily_plans.all()
        services_price = sum(dp.service.price for dp in daily_plans)
        guide_price = guide.price if guide else 0
        days = (end_time - start_time).days + 1

        # CarRental narxini hisoblash
        car_rental_price = 0
        for car_rental in car_rentals_data:
            car_rental_price += car_rental.price_per_day * days

        # RecommendedLocation narxini hisoblash
        recommended_locations_price = sum(loc.price for loc in recommended_locations_data)

        total_price = services_price + guide_price + car_rental_price + recommended_locations_price
        validated_data['total_price'] = total_price

        # Booking obyektini yaratish
        booking = Booking.objects.create(**validated_data)

        # CarRental va RecommendedLocation'larni qo'shish
        booking.car_rentals.set(car_rentals_data)
        booking.recommended_locations.set(recommended_locations_data)

        return booking