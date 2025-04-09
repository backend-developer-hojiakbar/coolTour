# api/utils.py
from datetime import timedelta
from .models import Service, DailyPlan
import random

def generate_daily_plans(plan):
    delta = (plan.end_date - plan.start_date).days + 1
    vibes = plan.vibes.all()
    services = Service.objects.filter(service_vibe__in=vibes, travellers__gte=plan.travellers)

    for day in range(1, delta + 1):
        time_slots = [
            "09:00 - 10:30",
            "11:00 - 13:00",
            "14:00 - 16:00",
            "16:30 - 17:30",
            "18:00 - 19:30"
        ]
        daily_services = random.sample(list(services), min(len(services), len(time_slots)))
        for i, service in enumerate(daily_services):
            service.duration = time_slots[i]
            service.save()
            DailyPlan.objects.create(plan=plan, day=day, service=service)