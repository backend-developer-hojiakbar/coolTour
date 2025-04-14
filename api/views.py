from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Place, Budget, Vibe, Service, Guide, CarRental, Plan, Booking, RecommendedLocation, DailyPlan
from .serializers import UserSerializer, RegisterSerializer, LoginSerializer, PlaceSerializer, BudgetSerializer, \
    VibeSerializer, ServiceSerializer, GuideSerializer, CarRentalSerializer, PlanSerializer, BookingSerializer, \
    RecommendedLocationSerializer
from .utils import generate_daily_plans, fetch_recommended_locations


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']
        password = serializer.validated_data['password']
        try:
            user = User.objects.get(phone_number=phone_number)
            if user.check_password(password):
                refresh = RefreshToken.for_user(user)
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': UserSerializer(user).data
                }, status=status.HTTP_200_OK)
            return Response({'error': 'Invalid password'}, status=status.HTTP_401_UNAUTHORIZED)
        except User.DoesNotExist:
            return Response({'error': 'User with this phone number does not exist'}, status=status.HTTP_404_NOT_FOUND)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]


class PlaceViewSet(viewsets.ModelViewSet):
    queryset = Place.objects.all()
    serializer_class = PlaceSerializer
    permission_classes = [AllowAny]


class BudgetViewSet(viewsets.ModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer
    permission_classes = [AllowAny]


class VibeViewSet(viewsets.ModelViewSet):
    queryset = Vibe.objects.all()
    serializer_class = VibeSerializer
    permission_classes = [AllowAny]


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [AllowAny]


class GuideViewSet(viewsets.ModelViewSet):
    queryset = Guide.objects.all()
    serializer_class = GuideSerializer
    permission_classes = [AllowAny]


class CarRentalViewSet(viewsets.ModelViewSet):
    queryset = CarRental.objects.all()
    serializer_class = CarRentalSerializer
    permission_classes = [AllowAny]


class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def build_my_trip(self, request):
        if not request.user.is_authenticated:
            try:
                user = User.objects.get(phone_number="guest_user")
            except User.DoesNotExist:
                user = User.objects.create_user(
                    phone_number="guest_user",
                    password="guest123",
                    user_type="traveller",
                    fio="Guest User"
                )
        else:
            user = request.user

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.save(user=user)

        generate_daily_plans(plan)
        fetch_recommended_locations(plan)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [AllowAny]


class RecommendedLocationViewSet(viewsets.ModelViewSet):
    queryset = RecommendedLocation.objects.all()
    serializer_class = RecommendedLocationSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=['post'])
    def copy_from_daily_plan(self, request, pk=None):
        recommended_location = self.get_object()
        daily_plan_id = request.data.get('daily_plan_id')

        try:
            daily_plan = DailyPlan.objects.get(id=daily_plan_id)
            service = daily_plan.service

            recommended_location.name = service.name
            recommended_location.description = service.description
            recommended_location.price = service.price
            recommended_location.image_url = str(
                service.image.url) if service.image else "https://via.placeholder.com/400x300.png?text=No+Image+Available"
            recommended_location.save()

            serializer = self.get_serializer(recommended_location)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DailyPlan.DoesNotExist:
            return Response({'error': 'DailyPlan not found'}, status=status.HTTP_404_NOT_FOUND)