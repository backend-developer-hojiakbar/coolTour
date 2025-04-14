from datetime import timedelta
from .models import Service, DailyPlan, RecommendedLocation, Place, User, Vibe
import random
import requests
from django.conf import settings
from decouple import config
from openai import OpenAI

GOOGLE_API_KEY = 'AIzaSyD4q54gfWXFEpC-dAZ4o0afBFuM9LtaPdU'
OPENAI_API_KEY = config('OPENAI_API_KEY', default=GOOGLE_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_recommended_locations(plan):
    # Ichki bazadan joylarni olish
    internal_locations = Service.objects.filter(
        place=plan.place,
        service_vibe__in=plan.vibes.all(),
        price__lte=plan.budget.amount / ((plan.end_date - plan.start_date).days + 1)
    )
    existing_names = set()
    for locates in internal_locations:
        if locates.name not in existing_names:
            recommended_location = RecommendedLocation.objects.create(
                plan=plan,
                name=locates.name,
                place=locates.place,
                address=locates.address,
                description=locates.description,
                price=locates.price,
                image_url=str(locates.image.url) if locates.image else "https://via.placeholder.com/400x300.png?text=No+Image+Available",
                source='internal'
            )
            recommended_location.vibes.set([locates.service_vibe])
            existing_names.add(locates.name)

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
                tourist_attractions.extend(data.get('results', [])[:20])
            else:
                print(f"Google Places API error: {data.get('status')} - {data.get('error_message', 'No error message')}")

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
            dining_locations.extend(data.get('results', [])[:20])
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

    # Agar Google Places API ishlamasa, statik joylar qo‘shamiz
    if not tourist_attractions and not dining_locations:
        print("Google Places API failed, adding static locations.")
        recommended_places = [
            {
                "name": "Amir Temur Square",
                "description": "A historic square in the heart of Tashkent, featuring a statue of Amir Temur.",
                "address": "Amir Temur Avenue, Tashkent, Uzbekistan",
                "price": 5.00,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/5/5d/Amir_Temur_Square_Tashkent.jpg",
                "vibes": ["Adventure"]
            },
            {
                "name": "Chorsu Bazaar",
                "description": "A traditional market in Tashkent, perfect for experiencing local culture and cuisine.",
                "address": "Old City, Tashkent, Uzbekistan",
                "price": 10.00,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/8/8f/Chorsu_Bazaar_Tashkent.jpg",
                "vibes": ["Cultural"]
            },
            {
                "name": "Tashkent Metro",
                "description": "Explore the beautifully designed metro stations of Tashkent, a unique adventure.",
                "address": "Various stations across Tashkent, Uzbekistan",
                "price": 2.00,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/2/2e/Tashkent_Metro_Station.jpg",
                "vibes": ["Adventure"]
            },
            {
                "name": "Navoi Park",
                "description": "A large park in Tashkent with monuments and green spaces, ideal for a short adventure.",
                "address": "Navoi Avenue, Tashkent, Uzbekistan",
                "price": 0.00,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/9/9a/Navoi_Park_Tashkent.jpg",
                "vibes": ["Relax"]
            },
            {
                "name": "Independence Square",
                "description": "A symbolic square in Tashkent, representing Uzbekistan's independence.",
                "address": "Mustakillik Avenue, Tashkent, Uzbekistan",
                "price": 0.00,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/3/3b/Independence_Square_Tashkent.jpg",
                "vibes": ["Cultural"]
            },
            {
                "name": "Tashkent Tower",
                "description": "The tallest tower in Central Asia, offering panoramic views of Tashkent.",
                "address": "107A Amir Temur Avenue, Tashkent, Uzbekistan",
                "price": 15.00,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/4/4a/Tashkent_Tower.jpg",
                "vibes": ["Adventure"]
            },
            {
                "name": "Hazrati Imam Complex",
                "description": "A religious and historical complex in Tashkent, featuring ancient manuscripts.",
                "address": "Karasu 6, Tashkent, Uzbekistan",
                "price": 8.00,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/1/1f/Hazrati_Imam_Complex_Tashkent.jpg",
                "vibes": ["Cultural"]
            },
            {
                "name": "Charvak Lake",
                "description": "A stunning lake near Tashkent, perfect for outdoor activities like boating.",
                "address": "Charvak Reservoir, Tashkent Region, Uzbekistan",
                "price": 20.00,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/1/1b/Charvak_Lake_Uzbekistan.jpg",
                "vibes": ["Adventure"]
            }
        ]

        for place in recommended_places:
            if place["name"] not in existing_names:
                place_obj, _ = Place.objects.get_or_create(
                    name=place["name"],
                    defaults={'description': place["description"]}
                )
                recommended_location = RecommendedLocation.objects.create(
                    plan=plan,
                    name=place["name"],
                    place=place_obj,
                    address=place["address"],
                    description=place["description"],
                    price=place["price"],
                    image_url=place["image_url"],
                    source='external'
                )
                vibes_to_add = Vibe.objects.filter(name__in=place["vibes"])
                recommended_location.vibes.set(vibes_to_add)
                existing_names.add(place["name"])
        return

    all_locations = tourist_attractions + dining_locations
    for place in all_locations[:40]:
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

            place_name = details_data.get('name', place.get('name'))
            if place_name in existing_names:
                continue

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
            address = details_data.get('formatted_address', 'Address not available')
            rating = details_data.get('rating', 'N/A')
            opening_hours = details_data.get('opening_hours', {}).get('weekday_text', ['N/A'])
            opening_hours_str = '\n'.join(opening_hours) if isinstance(opening_hours, list) else 'N/A'

            description = (
                f"{description}\n"
                f"Rating: {rating}\n"
                f"Opening Hours:\n{opening_hours_str}"
            )

            try:
                vibe_names = ' '.join(vibe.name.lower() for vibe in plan.vibes.all())
                prompt = f"Provide a detailed description of {place_name} in {plan.place.name}, focusing on why it's a great place to visit or dine, considering vibes like {vibe_names}."
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

            place_obj, _ = Place.objects.get_or_create(
                name=place_name,
                defaults={'description': details_data.get('editorial_summary', {}).get('overview', '')}
            )

            recommended_location = RecommendedLocation.objects.create(
                plan=plan,
                name=place_name,
                place=place_obj,
                address=address,
                description=description,
                price=estimated_price,
                image_url=image_url,
                source='external'
            )
            recommended_location.vibes.set(plan.vibes.all())
            existing_names.add(place_name)
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
    total_required_activities = delta * required_activities_per_day  # Tuzatildi
    available_services = list(services)

    if len(available_services) < total_required_activities:
        agency = User.objects.filter(user_type='agency').first()
        if not agency:
            agency = User.objects.create_user(
                phone_number="agency_default",
                password="default123",
                user_type="agency",
                company_name="Default Agency"
            )

        placeholder_activities = [
            {
                "name": f"Trekking in Chimgan Mountains",
                "description": f"A thrilling trek through the scenic Chimgan Mountains near Tashkent.",
                "address": "Chimgan Mountains, Tashkent Region, Uzbekistan",
                "duration": "4 hours",
                "price": 40.00,
                "category": "Outdoor",
                "image": "https://upload.wikimedia.org/wikipedia/commons/2/29/Chimgan_Mountains_Uzbekistan.jpg"
            },
            {
                "name": f"Biking in Tashkent Outskirts",
                "description": f"An adventurous bike ride through the beautiful outskirts of Tashkent.",
                "address": "Outskirts of Tashkent, Uzbekistan",
                "duration": "3 hours",
                "price": 25.00,
                "category": "Outdoor",
                "image": "https://upload.wikimedia.org/wikipedia/commons/9/9a/Biking_in_Uzbekistan.jpg"
            },
            {
                "name": f"Rock Climbing in Yangiabad",
                "description": f"Experience rock climbing in the Yangiabad area, perfect for adventure seekers.",
                "address": "Yangiabad, Tashkent Region, Uzbekistan",
                "duration": "5 hours",
                "price": 50.00,
                "category": "Outdoor",
                "image": "https://upload.wikimedia.org/wikipedia/commons/5/5e/Rock_Climbing_Uzbekistan.jpg"
            },
            {
                "name": f"Horseback Riding in Charvak Lake",
                "description": f"Ride horses around the stunning Charvak Lake with breathtaking views.",
                "address": "Charvak Reservoir, Tashkent Region, Uzbekistan",
                "duration": "2 hours",
                "price": 30.00,
                "category": "Outdoor",
                "image": "https://upload.wikimedia.org/wikipedia/commons/1/1b/Charvak_Lake_Uzbekistan.jpg"
            }
        ]

        existing_service_names = {service.name for service in available_services}
        for activity in placeholder_activities:
            if len(available_services) >= total_required_activities:
                break
            if activity["name"] not in existing_service_names:
                service = Service.objects.create(
                    agency=agency,
                    name=activity["name"],
                    place=plan.place,
                    address=activity["address"],
                    description=activity["description"],
                    duration=activity["duration"],
                    price=activity["price"],
                    category=activity["category"],
                    travellers=plan.travellers,
                    service_vibe=plan.vibes.first(),
                    image=activity["image"]
                )
                available_services.append(service)
                existing_service_names.add(activity["name"])

        if len(available_services) < total_required_activities:
            vibe_names_str = ', '.join(vibe.name for vibe in vibes)
            prompt = (
                f"Generate a detailed {delta}-day travel itinerary for {plan.place.name} "
                f"for {plan.travellers} travellers with vibes: {vibe_names_str}. "
                f"The total budget is {plan.budget.amount} {plan.budget.currency}. "
                f"Suggest {required_activities_per_day} activities per day (e.g., outdoor adventures, thrilling experiences). "
                f"Each activity should include a name, description, address, estimated duration (e.g., 2 hours), "
                f"estimated price (within budget), and category (e.g., Outdoor, Adventure). "
                f"Ensure the activities fit within the budget and match the specified vibes."
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

            for suggestion in ai_suggestions:
                if not suggestion.strip():
                    continue
                try:
                    parts = suggestion.split('-')
                    if len(parts) < 6:
                        continue
                    name = parts[0].strip().replace("Day ", "").split(":")[1].strip()
                    description = parts[1].strip()
                    address = parts[2].strip().replace("Address:", "").strip()
                    duration = parts[3].strip().replace("Duration:", "").strip()
                    price = float(parts[4].strip().replace("Price:", "").replace("$", "").strip())
                    category = parts[5].strip().replace("Category:", "").strip()

                    if name not in existing_service_names:
                        service = Service.objects.create(
                            agency=agency,
                            name=name,
                            place=plan.place,
                            address=address,
                            description=description,
                            duration=duration,
                            price=price,
                            category=category,
                            travellers=plan.travellers,
                            service_vibe=plan.vibes.first(),
                            image="https://via.placeholder.com/400x300.png?text=Service+Image"
                        )
                        available_services.append(service)
                        existing_service_names.add(name)
                except Exception as e:
                    print(f"Error parsing AI suggestion: {e}")

    time_slots = [
        "09:00 - 10:30",
        "11:00 - 13:00",
        "14:00 - 16:00",
        "16:30 - 17:30",
        "18:00 - 19:30"
    ]

    used_services = set()
    for day in range(1, delta + 1):
        daily_available_services = [s for s in available_services if s.name not in used_services]
        if len(daily_available_services) < required_activities_per_day:
            daily_available_services = available_services
            used_services.clear()

        daily_services = random.sample(daily_available_services, min(len(daily_available_services), required_activities_per_day))
        for i, service in enumerate(daily_services):
            service.duration = time_slots[i % len(time_slots)]
            service.save()
            DailyPlan.objects.create(plan=plan, day=day, service=service)
            used_services.add(service.name)