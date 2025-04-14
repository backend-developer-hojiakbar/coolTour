from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
import random

# Custom User Manager
class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('The Phone Number field must be set')
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(phone_number, password, **extra_fields)

# User Model
class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('traveller', 'Traveller'),
        ('agency', 'Tour Agency'),
        ('admin', 'Admin'),
    )
    username = None
    phone_number = models.CharField(max_length=15, unique=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='traveller')
    fio = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.phone_number

# Place Model
class Place(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    main_image = models.ImageField(upload_to='places/main/', blank=True, null=True)  # Katta rasm
    thumbnail_image = models.ImageField(upload_to='places/thumbnails/', blank=True, null=True)  # Kichik rasm
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# Budget Model
class Budget(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} {self.currency}"

# Vibe Model
class Vibe(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

# Service Model
class Service(models.Model):
    agency = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services', limit_choices_to={'user_type': 'agency'})
    name = models.CharField(max_length=100)
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='services')
    description = models.TextField()
    duration = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50)
    image = models.ImageField(upload_to='services/', blank=False, null=False)  # Majburiy qilindi
    travellers = models.IntegerField(default=1)
    service_vibe = models.ForeignKey(Vibe, on_delete=models.CASCADE, related_name='vibe')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# Guide Model
class Guide(models.Model):
    agency = models.ForeignKey(User, on_delete=models.CASCADE, related_name='guides', limit_choices_to={'user_type': 'agency'})
    name = models.CharField(max_length=100)
    bio = models.TextField()
    experience = models.TextField()
    skills = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    image = models.ImageField(upload_to='guides/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# CarRental Model
class CarRental(models.Model):
    agency = models.ForeignKey(User, on_delete=models.CASCADE, related_name='car_rentals', limit_choices_to={'user_type': 'agency'})
    name = models.CharField(max_length=100, default="Chevrolet Spark")
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=300000)
    category = models.CharField(max_length=50, default="Rental Car")
    features = models.TextField(default="Automatic transmission, Fuel-efficient, Compact size, Air conditioning, Bluetooth connectivity")
    max_capacity = models.IntegerField(default=4)  # Maksimal odam sig'ish soni
    image = models.ImageField(upload_to='car_rentals/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# Plan Model
class Plan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='plans')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='plans')
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='plans')
    start_date = models.DateField()
    end_date = models.DateField()
    travellers = models.IntegerField(default=1)
    vibes = models.ManyToManyField(Vibe, related_name='plans')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Plan for {self.user.phone_number} to {self.place.name}"

# DailyPlan Model
class DailyPlan(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='daily_plans')
    day = models.IntegerField()
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='daily_plans')

    def __str__(self):
        return f"Day {self.day} of {self.plan}"

# RecommendedLocation Model
class RecommendedLocation(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='recommended_locations')
    name = models.CharField(max_length=100)
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='recommended_locations')
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    image_url = models.URLField(blank=False, null=False)  # Majburiy qilindi
    source = models.CharField(max_length=50, default='internal')

    def __str__(self):
        return f"{self.name} in {self.place.name}"

# Booking Model
class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('declined', 'Declined'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='bookings')
    guide = models.ForeignKey(Guide, on_delete=models.SET_NULL, blank=True, null=True, related_name='bookings')
    car_rentals = models.ManyToManyField(CarRental, related_name='bookings', blank=True)
    recommended_locations = models.ManyToManyField(RecommendedLocation, related_name='bookings', blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    num_people = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking by {self.user.phone_number} for {self.plan}"