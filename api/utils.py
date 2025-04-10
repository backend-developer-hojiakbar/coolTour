# api/utils.py
from datetime import timedelta
from .models import Service, DailyPlan, RecommendedLocation
import random
import requests
from django.conf import settings

# Google Places API kaliti (settings.py dan olinadi)
GOOGLE_API_KEY = getattr(settings, 'GOOGLE_API_KEY', None)

def fetch_recommended_locations(plan):
    """
    Plan qilingan joy asosida o'z bazamizdan va internetdan tavsiya etilgan joylarni olib keladi.
    """
    # 1. O'z bazamizdan joylarni olish (Service modelidan)
    internal_locations = Service.objects.filter(place__icontains=plan.place)
    for location in internal_locations:
        RecommendedLocation.objects.create(
            plan=plan,
            name=location.name,
            place=location.place,
            description=location.description,
            image_url=str(location.image) if location.image else None,
            source='internal'
        )

    # 2. Internetdan joylarni olish (Google Places API orqali)
    if GOOGLE_API_KEY:
        try:
            url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            params = {
                'query': f"tourist attractions in {plan.place}",
                'key': GOOGLE_API_KEY,
                'type': 'tourist_attraction'
            }
            response = requests.get(url, params=params)
            data = response.json()

            if data.get('status') == 'OK':
                for place in data.get('results', [])[:5]:  # Faqat 5 ta joy olamiz
                    place_id = place.get('place_id')
                    # Place Details API orqali qo'shimcha ma'lumotlarni olish
                    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                    details_params = {
                        'place_id': place_id,
                        'key': GOOGLE_API_KEY,
                        'fields': 'name,formatted_address,editorial_summary,photos'
                    }
                    details_response = requests.get(details_url, params=details_params)
                    details_data = details_response.json().get('result', {})

                    image_url = None
                    if details_data.get('photos'):
                        photo_reference = details_data['photos'][0]['photo_reference']
                        image_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_reference}&key={GOOGLE_API_KEY}"

                    RecommendedLocation.objects.create(
                        plan=plan,
                        name=details_data.get('name', place.get('name')),
                        place=details_data.get('formatted_address', plan.place),
                        description=details_data.get('editorial_summary', {}).get('overview', ''),
                        image_url=image_url,
                        source='external'
                    )
        except Exception as e:
            print(f"Error fetching recommended locations: {e}")

def generate_daily_plans(plan):
    """
    AI yordamida DailyPlanlarni yaratish.
    """
    delta = (plan.end_date - plan.start_date).days + 1
    vibes = plan.vibes.all()
    services = Service.objects.filter(service_vibe__in=vibes, travellers__gte=plan.travellers)

    # AI yordamida xizmatlarni tanlash va moslashtirish
    # Bu yerda soddalashtirilgan versiyani ishlatamiz, chunki AI modeli ulanmagan
    time_slots = [
        "09:00 - 10:30",
        "11:00 - 13:00",
        "14:00 - 16:00",
        "16:30 - 17:30",
        "18:00 - 19:30"
    ]

    for day in range(1, delta + 1):
        daily_services = random.sample(list(services), min(len(services), len(time_slots)))
        for i, service in enumerate(daily_services):
            service.duration = time_slots[i]
            service.save()
            DailyPlan.objects.create(plan=plan, day=day, service=service)