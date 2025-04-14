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
        fields = ['id', 'name', 'description', 'country', 'main_image', 'thumbnail_image', 'created_at']


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
        fields = ['id', 'agency', 'name', 'place', 'address', 'description', 'duration', 'price', 'category', 'image',
                  'travellers', 'service_vibe', 'created_at']


class GuideSerializer(serializers.ModelSerializer):
    agency = UserSerializer()

    class Meta:
        model = Guide
        fields = ['id', 'agency', 'name', 'bio', 'experience', 'skills', 'price', 'image', 'created_at']


class CarRentalSerializer(serializers.ModelSerializer):
    agency = UserSerializer()

    class Meta:
        model = CarRental
        fields = ['id', 'agency', 'name', 'price_per_day', 'category', 'features', 'max_capacity', 'image',
                  'created_at']


class DailyPlanSerializer(serializers.ModelSerializer):
    service = ServiceSerializer()

    class Meta:
        model = DailyPlan
        fields = ['id', 'day', 'service']


class RecommendedLocationSerializer(serializers.ModelSerializer):
    place = PlaceSerializer()
    vibes = VibeSerializer(many=True)

    class Meta:
        model = RecommendedLocation
        fields = ['id', 'name', 'place', 'address', 'description', 'price', 'image_url', 'source', 'vibes']


class PlanSerializer(serializers.ModelSerializer):
    place = serializers.PrimaryKeyRelatedField(queryset=Place.objects.all())
    budget = serializers.PrimaryKeyRelatedField(queryset=Budget.objects.all())
    vibes = serializers.PrimaryKeyRelatedField(queryset=Vibe.objects.all(), many=True)
    daily_plans = serializers.SerializerMethodField()
    recommended_locations = RecommendedLocationSerializer(many=True, read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    total_price = serializers.SerializerMethodField()  # Umumiy narx

    class Meta:
        model = Plan
        fields = ['id', 'user', 'place', 'address', 'budget', 'start_date', 'end_date', 'travellers', 'vibes',
                  'daily_plans', 'recommended_locations', 'total_price', 'created_at']

    def get_daily_plans(self, obj):
        daily_plans = DailyPlan.objects.filter(plan=obj).order_by('day')
        grouped_plans = {}

        for plan in daily_plans:
            day = plan.day
            if day not in grouped_plans:
                grouped_plans[day] = []
            grouped_plans[day].append(plan)

        result = []
        for day, plans in grouped_plans.items():
            day_total_price = sum(plan.service.price for plan in plans)  # Kunlik umumiy narx
            result.append({
                'day': day,
                'services': DailyPlanSerializer(plans, many=True).data,
                'day_total_price': float(day_total_price)  # Kunlik narx
            })

        return result

    def get_total_price(self, obj):
        daily_plans = DailyPlan.objects.filter(plan=obj)
        total_price = sum(plan.service.price for plan in daily_plans)  # Butun plan bo‘yicha narx
        return float(total_price)


class BookingSerializer(serializers.ModelSerializer):
    plan = PlanSerializer()
    guide = GuideSerializer()
    car_rentals = CarRentalSerializer(many=True)
    recommended_locations = RecommendedLocationSerializer(many=True)

    class Meta:
        model = Booking
        fields = ['id', 'user', 'plan', 'guide', 'car_rentals', 'recommended_locations', 'start_time', 'end_time',
                  'num_people', 'status', 'total_price', 'created_at']

    def create(self, validated_data):
        car_rentals_data = validated_data.pop('car_rentals', [])
        recommended_locations_data = validated_data.pop('recommended_locations', [])
        plan = validated_data.get('plan')
        guide = validated_data.get('guide')
        start_time = validated_data.get('start_time')
        end_time = validated_data.get('end_time')
        num_people = validated_data.get('num_people')

        daily_plans = plan.daily_plans.all()
        services_price = sum(dp.service.price for dp in daily_plans)
        guide_price = guide.price if guide else 0
        days = (end_time - start_time).days + 1

        car_rental_price = 0
        for car_rental in car_rentals_data:
            car_rental_price += car_rental.price_per_day * days

        recommended_locations_price = sum(loc.price for loc in recommended_locations_data)

        total_price = services_price + guide_price + car_rental_price + recommended_locations_price
        validated_data['total_price'] = total_price

        booking = Booking.objects.create(**validated_data)
        booking.car_rentals.set(car_rentals_data)
        booking.recommended_locations.set(recommended_locations_data)

        return booking