import requests

CITY_COORDS = {
    "Mumbai": (19.0760, 72.8777), "Delhi": (28.61, 77.21), "Bangalore": (12.97, 77.59),
    "Chennai": (13.0827, 80.2707), "Hyderabad": (17.39, 78.49), "Pune": (18.52, 73.86),
    "Ahmedabad": (23.03, 72.57), "Jaipur": (26.91, 75.79), "Kolkata": (22.5726, 88.3639), "Surat": (21.1702, 72.8311)
}

def get_weather_report(city):
    try:
        lat, lon = CITY_COORDS.get(city, (19.08, 72.88))
        r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true", timeout=5)
        if r.status_code == 200:
            cw = r.json().get("current_weather", {})
            return {"temp": cw.get("temperature", 28), "wind": cw.get("windspeed", 10), "city": city}
    except: pass
    return {"temp": 28, "wind": 10, "city": city}

def get_city_weather(city):
    return get_weather_report(city)

def get_route_weather_multiplier(origin, dest):
    try:
        w1 = get_weather_report(origin)
        w2 = get_weather_report(dest)
        avg_wind = (w1["wind"] + w2["wind"]) / 2
        return 1.0 + (avg_wind / 100)
    except:
        return 1.0
