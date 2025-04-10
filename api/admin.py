# api/admin.py
from django.contrib import admin
from .models import User, Vibe, Service, Guide, CarRental, Plan, DailyPlan, Booking, RecommendedLocation

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'user_type', 'fio']

@admin.register(Vibe)
class VibeAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'agency', 'place', 'price', 'service_vibe']

@admin.register(Guide)
class GuideAdmin(admin.ModelAdmin):
    list_display = ['name', 'agency', 'price']

@admin.register(CarRental)
class CarRentalAdmin(admin.ModelAdmin):
    list_display = ['name', 'agency', 'price_per_day']

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['user', 'place', 'start_date', 'end_date']

@admin.register(DailyPlan)
class DailyPlanAdmin(admin.ModelAdmin):
    list_display = ['plan', 'day', 'service']

@admin.register(RecommendedLocation)
class RecommendedLocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'place', 'source']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'total_price']