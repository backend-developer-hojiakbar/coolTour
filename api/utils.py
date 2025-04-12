# api/utils.py
from datetime import timedelta
from .models import Service, DailyPlan, RecommendedLocation, Place
import random
import requests
from django.conf import settings
import google.generativeai as genai

# Google Places API kaliti
GOOGLE_API_KEY = 'AIzaSyD4q54gfWXFEpC-dAZ4o0afBFuM9LtaPdU'

# Gemini API kaliti
GEMINI_API_KEY = getattr(settings, 'GEMINI_API_KEY', None)
genai.configure(api_key=GEMINI_API_KEY)


def fetch_recommended_locations(plan):
    """
    Plan qilingan joy asosida o'z bazamizdan va internetdan tavsiya etilgan joylarni olib keladi.
    Budget va vibes asosida moslashtirishga harakat qilamiz.
    """
    # 1. O'z bazamizdan joylarni olish (Service modelidan)
    internal_locations = Service.objects.filter(
        place=plan.place,
        service_vibe__in=plan.vibes.all(),
        price__lte=plan.budget.amount / ((plan.end_date - plan.start_date).days + 1)
    )
    for locates in internal_locations:
        RecommendedLocation.objects.create(
            plan=plan,
            name=locates.name,
            place=locates.place,
            description=locates.description,
            price=locates.price,
            image_url=str(locates.image) if locates.image else None,
            source='internal'
        )

    # 2. Internetdan joylarni olish (Google Places API orqali)
    if GOOGLE_API_KEY:
        try:
            vibe_names = ' '.join(vibe.name.lower() for vibe in plan.vibes.all())
            query = f"{vibe_names} tourist attractions in {plan.place.name}"
            url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            params = {
                'query': query,
                'key': GOOGLE_API_KEY,
                'type': 'tourist_attraction'
            }
            response = requests.get(url, params=params)
            data = response.json()

            if data.get('status') == 'OK':
                for place in data.get('results', [])[:5]:
                    place_id = place.get('place_id')
                    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                    details_params = {
                        'place_id': place_id,
                        'key': GOOGLE_API_KEY,
                        'fields': 'name,formatted_address,editorial_summary,photos,price_level'
                    }
                    details_response = requests.get(details_url, params=details_params)
                    details_data = details_response.json().get('result', {})

                    # Price levelni taxminiy narxga aylantiramiz
                    price_level = details_data.get('price_level', 1)
                    avg_daily_budget = plan.budget.amount / ((plan.end_date - plan.start_date).days + 1)
                    if price_level * 50 > avg_daily_budget:
                        continue
                    estimated_price = price_level * 50  # Taxminiy narx

                    # Rasm olish
                    image_url = None
                    if details_data.get('photos'):
                        photo_reference = details_data['photos'][0]['photo_reference']
                        image_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_reference}&key={GOOGLE_API_KEY}"
                    else:
                        # Agar rasm topilmasa, Gemini API yordamida tasvir generatsiya qilishga harakat qilamiz
                        try:
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            prompt = f"Generate a description of a tourist attraction image for {details_data.get('name', place.get('name'))} in {plan.place.name}."
                            response = model.generate_content(prompt)
                            # Eslatma: Gemini API hozircha to'g'ridan-to'g'ri rasm generatsiya qila olmaydi,
                            # lekin kelajakda bu funksiya qo'shilishi mumkin. Hozircha description olish bilan cheklanamiz.
                            print(f"AI-generated description for image: {response.text}")
                        except Exception as e:
                            print(f"Error generating image description with Gemini API: {e}")

                    place_obj, _ = Place.objects.get_or_create(
                        name=details_data.get('name', place.get('name')),
                        defaults={'description': details_data.get('editorial_summary', {}).get('overview', '')}
                    )

                    RecommendedLocation.objects.create(
                        plan=plan,
                        name=details_data.get('name', place.get('name')),
                        place=place_obj,
                        description=details_data.get('editorial_summary', {}).get('overview', ''),
                        price=estimated_price,
                        image_url=image_url,
                        source='external'
                    )
        except Exception as e:
            print(f"Error fetching recommended locations: {e}")


def generate_daily_plans(plan):
    """
    Gemini API yordamida DailyPlanlarni yaratish.
    Place, budget, vibes va travellers asosida mos rejalarni generatsiya qilamiz.
    """
    delta = (plan.end_date - plan.start_date).days + 1
    vibes = plan.vibes.all()
    services = Service.objects.filter(
        place=plan.place,
        service_vibe__in=vibes,
        travellers__gte=plan.travellers,
        price__lte=plan.budget.amount / delta
    )

    model = genai.GenerativeModel('gemini-1.5-flash')
    vibe_names = ', '.join(vibe.name for vibe in vibes)
    prompt = (
        f"Plan a {delta}-day trip to {plan.place.name} for {plan.travellers} travellers "
        f"with vibes: {vibe_names}. The total budget is {plan.budget.amount} {plan.budget.currency}. "
        f"Suggest activities for each day based on the location, vibes, and budget. "
        f"Ensure the activities fit within the budget and match the specified vibes."
    )

    try:
        response = model.generate_content(prompt)
        ai_suggestions = response.text.split('\n')
    except Exception as e:
        print(f"Error with Gemini API: {e}")
        ai_suggestions = []

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