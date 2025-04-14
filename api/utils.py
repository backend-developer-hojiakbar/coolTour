from datetime import timedelta
from .models import Service, DailyPlan, RecommendedLocation, Place, User, Vibe
import random
import requests
from django.conf import settings
from decouple import config
from openai import OpenAI

GOOGLE_API_KEY = 'AIzaSyD4q54gfWXFEpC-dAZ4o0afBFuM9LtaPdU'
OPENAI_API_KEY = GOOGLE_API_KEY
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_recommended_locations(plan):
    # Ichki bazadan joylarni olish
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
            image_url=str(locates.image.url) if locates.image else "https://via.placeholder.com/400x300.png?text=No+Image+Available",
            source='internal'
        )

    # Google Places API’dan joylarni olish
    tourist_attractions = []
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
                tourist_attractions.extend(data.get('results', [])[:20])  # Ko‘proq joy olish
            else:
                print(f"Google Places API error: {data.get('status')} - {data.get('error_message', 'No error message')}")

            # Pagination
            next_page_token = data.get('next_page_token')
            while next_page_token and len(tourist_attractions) < 20:
                params['pagetoken'] = next_page_token
                response = requests.get(url, params=params)
                data = response.json()
                tourist_attractions.extend(data.get('results', [])[:20])
                next_page_token = data.get('next_page_token')

        except Exception as e:
            print(f"Error fetching tourist attractions: {e}")

    # Ovqatlanish joylari
    dining_locations = []
    try:
        query = f"restaurants in {plan.place.name}"
        params = {
            'query': query,
            'key': GOOGLE_API_KEY,
            'type': 'restaurant'
        }
        response = requests.get(url, params=params)
        data = response.json()

        if data.get('status') == 'OK':
            dining_locations.extend(data.get('results', [])[:20])  # Ko‘proq joy olish
        else:
            print(f"Google Places API error (dining): {data.get('status')} - {data.get('error_message', 'No error message')}")

        next_page_token = data.get('next_page_token')
        while next_page_token and len(dining_locations) < 20:
            params['pagetoken'] = next_page_token
            response = requests.get(url, params=params)
            data = response.json()
            dining_locations.extend(data.get('results', [])[:20])
            next_page_token = data.get('next_page_token')

    except Exception as e:
        print(f"Error fetching dining locations: {e}")

    # Agar Google Places API ishlamasa, ichki bazadan qo‘shimcha ma'lumotlar qo‘shamiz
    if not tourist_attractions and not dining_locations:
        print("Google Places API failed, using only internal locations.")
        # Ichki bazadan qo‘shimcha joylar qo‘shish
        for i in range(10):  # 10 ta placeholder joy qo‘shamiz
            RecommendedLocation.objects.create(
                plan=plan,
                name=f"Local Attraction {i+1} in {plan.place.name}",
                place=plan.place,
                description=f"A local attraction in {plan.place.name} to explore.",
                price=15.00,
                image_url="https://via.placeholder.com/400x300.png?text=Local+Attraction",
                source='internal'
            )
        return

    all_locations = tourist_attractions + dining_locations
    for place in all_locations[:40]:  # Ko‘proq joy qaytarish uchun limitni oshirdik
        try:
            place_id = place.get('place_id')
            details_url = "https://maps.googleapis.com/maps/api/place/details/json"
            details_params = {
                'place_id': place_id,
                'key': GOOGLE_API_KEY,
                'fields': 'name,formatted_address,editorial_summary,photos,price_level,rating,opening_hours'
            }
            details_response = requests.get(details_url, params=details_params)
            details_data = details_response.json().get('result', {})

            price_level = details_data.get('price_level', 1)
            avg_daily_budget = plan.budget.amount / ((plan.end_date - plan.start_date).days + 1)
            if price_level * 50 > avg_daily_budget:
                continue
            estimated_price = price_level * 50

            image_url = None
            if details_data.get('photos'):
                photo_reference = details_data['photos'][0]['photo_reference']
                image_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_reference}&key={GOOGLE_API_KEY}"
            else:
                image_url = "https://via.placeholder.com/400x300.png?text=No+Image+Available"

            description = details_data.get('editorial_summary', {}).get('overview', '')
            rating = details_data.get('rating', 'N/A')
            opening_hours = details_data.get('opening_hours', {}).get('weekday_text', ['N/A'])
            opening_hours_str = '\n'.join(opening_hours) if isinstance(opening_hours, list) else 'N/A'

            # Qo‘shimcha ma'lumotlarni description’ga qo‘shish
            description = (
                f"{description}\n"
                f"Rating: {rating}\n"
                f"Opening Hours:\n{opening_hours_str}"
            )

            try:
                vibe_names = ' '.join(vibe.name.lower() for vibe in plan.vibes.all())
                prompt = f"Provide a detailed description of {details_data.get('name', place.get('name'))} in {plan.place.name}, focusing on why it's a great place to visit or dine, considering vibes like {vibe_names}."
                response = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a travel guide expert."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=150
                )
                ai_description = response.choices[0].message.content
                description = f"{description}\nAI Suggestion: {ai_description}"
            except Exception as e:
                print(f"Error generating description with OpenAI: {e}")
                description = description or "No description available."

            place_obj, _ = Place.objects.get_or_create(
                name=details_data.get('name', place.get('name')),
                defaults={'description': details_data.get('editorial_summary', {}).get('overview', '')}
            )

            RecommendedLocation.objects.create(
                plan=plan,
                name=details_data.get('name', place.get('name')),
                place=place_obj,
                description=description,
                price=estimated_price,
                image_url=image_url,
                source='external'
            )
        except Exception as e:
            print(f"Error processing location {place.get('name')}: {e}")

def generate_daily_plans(plan):
    delta = (plan.end_date - plan.start_date).days + 1
    vibes = plan.vibes.all()
    services = Service.objects.filter(
        place=plan.place,
        service_vibe__in=vibes,
        travellers__gte=plan.travellers,
        price__lte=plan.budget.amount / delta
    )

    required_activities_per_day = 3
    total_required_activities = delta * required_activities_per_day
    available_services = list(services)

    # Agar Service yetarli bo‘lmasa, OpenAI’dan foydalanamiz
    if len(available_services) < total_required_activities:
        vibe_names = ', '.join(vibe.name for vibe in vibes)
        prompt = (
            f"Generate a detailed {delta}-day travel itinerary for {plan.place.name} "
            f"for {plan.travellers} travellers with vibes: {vibe_names}. "
            f"The total budget is {plan.budget.amount} {plan.budget.currency}. "
            f"Suggest {required_activities_per_day} activities per day (e.g., sightseeing, dining, outdoor activities). "
            f"Each activity should include a name, description, estimated duration (e.g., 2 hours), "
            f"estimated price (within budget), and category (e.g., Outdoor, Cultural, Dining). "
            f"Ensure the activities fit within the budget and match the specified vibes."
        )

        agency = User.objects.filter(user_type='agency').first()
        if not agency:
            agency = User.objects.create_user(
                phone_number="agency_default",
                password="default123",
                user_type="agency",
                company_name="Default Agency"
            )

        try:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a travel planner."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000
            )
            ai_suggestions = response.choices[0].message.content.split('\n')
        except Exception as e:
            print(f"Error with OpenAI API: {e}")
            ai_suggestions = []

        # OpenAI’dan ma'lumot olinsa, yangi Service’lar yaratamiz
        for suggestion in ai_suggestions:
            if not suggestion.strip():
                continue
            try:
                parts = suggestion.split('-')
                if len(parts) < 5:
                    continue
                name = parts[0].strip().replace("Day ", "").split(":")[1].strip()
                description = parts[1].strip()
                duration = parts[2].strip().replace("Duration:", "").strip()
                price = float(parts[3].strip().replace("Price:", "").replace("$", "").strip())
                category = parts[4].strip().replace("Category:", "").strip()

                service = Service.objects.create(
                    agency=agency,
                    name=name,
                    place=plan.place,
                    description=description,
                    duration=duration,
                    price=price,
                    category=category,
                    travellers=plan.travellers,
                    service_vibe=plan.vibes.first(),
                    image="services/placeholder.jpg"
                )
                available_services.append(service)
            except Exception as e:
                print(f"Error parsing AI suggestion: {e}")

        # Agar OpenAI ishlamasa yoki yetarli Service topilmasa, placeholder faoliyatlar qo‘shamiz
        if len(available_services) < total_required_activities:
            placeholder_activities = [
                {
                    "name": f"Explore {plan.place.name} City Center",
                    "description": f"Take a walk around the city center of {plan.place.name} and enjoy local sights.",
                    "duration": "2 hours",
                    "price": 10.00,
                    "category": "Sightseeing"
                },
                {
                    "name": f"Local Dining Experience in {plan.place.name}",
                    "description": f"Enjoy a meal at a local restaurant in {plan.place.name}.",
                    "duration": "1.5 hours",
                    "price": 20.00,
                    "category": "Dining"
                },
                {
                    "name": f"Relax at a Park in {plan.place.name}",
                    "description": f"Spend some time relaxing at a local park in {plan.place.name}.",
                    "duration": "1 hour",
                    "price": 0.00,
                    "category": "Relax"
                }
            ]

            # Placeholder faoliyatlardan yetarli miqdorda qo‘shamiz
            for i in range(total_required_activities - len(available_services)):
                activity = placeholder_activities[i % len(placeholder_activities)]
                service = Service.objects.create(
                    agency=agency,
                    name=activity["name"],
                    place=plan.place,
                    description=activity["description"],
                    duration=activity["duration"],
                    price=activity["price"],
                    category=activity["category"],
                    travellers=plan.travellers,
                    service_vibe=plan.vibes.first(),
                    image="services/placeholder.jpg"
                )
                available_services.append(service)

    # DailyPlan’larni yaratish
    time_slots = [
        "09:00 - 10:30",
        "11:00 - 13:00",
        "14:00 - 16:00",
        "16:30 - 17:30",
        "18:00 - 19:30"
    ]

    for day in range(1, delta + 1):
        daily_services = random.sample(available_services, min(len(available_services), required_activities_per_day))
        for i, service in enumerate(daily_services):
            service.duration = time_slots[i % len(time_slots)]
            service.save()
            DailyPlan.objects.create(plan=plan, day=day, service=service)