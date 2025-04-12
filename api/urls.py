# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, PlaceViewSet, BudgetViewSet, VibeViewSet, ServiceViewSet, GuideViewSet, CarRentalViewSet, PlanViewSet, BookingViewSet, register_view, login_view

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'places', PlaceViewSet)
router.register(r'budgets', BudgetViewSet)
router.register(r'vibes', VibeViewSet)
router.register(r'services', ServiceViewSet)
router.register(r'guides', GuideViewSet)
router.register(r'car_rentals', CarRentalViewSet)
router.register(r'plans', PlanViewSet)
router.register(r'bookings', BookingViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
]