from django.shortcuts import render, redirect
import requests
from datetime import datetime
from .models import SearchHistory, FavoriteCity
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

def get_weather_info(lat, lon, display_name):
    """Helper function to fetch weather, forecast, and AQI for a given location"""
    WMO_CODES = {
        0: 'Clear Sky', 1: 'Mainly Clear', 2: 'Partly Cloudy', 3: 'Overcast', 
        45: 'Fog', 48: 'Depositing Rime Fog', 51: 'Drizzle', 61: 'Rain', 
        71: 'Snow', 80: 'Rain Showers', 95: 'Thunderstorm'
    }
    
    try:
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=temperature_2m&daily=temperature_2m_max,weathercode&timezone=auto"
        aq_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=european_aqi"
        
        # Use timeouts so the server doesn't hang if the API is slow
        w_res = requests.get(w_url, timeout=10).json()
        aq_res = requests.get(aq_url, timeout=10).json()
        
        all_hourly_temps = w_res.get('hourly', {}).get('temperature_2m', [])
        hourly_temps = all_hourly_temps[:24] 
        hourly_labels = [f"{i}:00" for i in range(24)]

        f_list = []
        d = w_res.get('daily', {})
        if d.get('time'):
            for i in range(1, 6):
                f_list.append({
                    'day_name': datetime.strptime(d['time'][i], '%Y-%m-%d').strftime('%a'),
                    'temp_max': d['temperature_2m_max'][i],
                    'condition': WMO_CODES.get(d['weathercode'][i], 'Clear')
                })

        return {
            'city': display_name,
            'temperature': w_res['current_weather']['temperature'],
            'description': WMO_CODES.get(w_res['current_weather']['weathercode'], 'Clear'),
            'windspeed': w_res['current_weather']['windspeed'],
            'aqi_index': aq_res.get('current', {}).get('european_aqi', 'N/A'),
            'forecast': f_list,
            'hourly_temps': hourly_temps,
            'hourly_labels': hourly_labels,
        }
    except Exception as e:
        print(f"DEBUG: Weather API Error -> {e}")
        return None

def index(request):
    weather_list = []
    error_message = None
    
    # Check both buckets
    city1 = request.GET.get('city') or request.POST.get('city')
    city2 = request.GET.get('city2') or request.POST.get('city2')
    
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')

    target_cities = [c.strip() for c in [city1, city2] if c]

    if target_cities:
        print(f"DEBUG: Search Triggered for cities: {target_cities}")
        for c_name in target_cities:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={c_name}&count=1"
            try:
                response = requests.get(geo_url, timeout=10)
                geo_res = response.json()
                
                if 'results' in geo_res and len(geo_res['results']) > 0:
                    res = geo_res['results'][0]
                    print(f"DEBUG: City found: {res['name']} at {res['latitude']}, {res['longitude']}")
                    
                    data = get_weather_info(
                        res['latitude'], 
                        res['longitude'], 
                        f"{res['name']}, {res.get('country', '')}"
                    )
                    
                    if data:
                        weather_list.append(data)
                        if request.user.is_authenticated:
                            SearchHistory.objects.create(user=request.user, city_name=data['city'])
                    else:
                        error_message = f"Could not fetch weather for {c_name}."
                else:
                    print(f"DEBUG: No results found for city: {c_name}")
                    error_message = f"City '{c_name}' not found."
            except Exception as e:
                print(f"DEBUG: Geocoding API Error -> {e}")
                error_message = "Network error. Please try again later."

    elif lat and lon:
        print(f"DEBUG: Location search triggered for {lat}, {lon}")
        data = get_weather_info(lat, lon, "Your Location")
        if data:
            weather_list.append(data)

    # Sidebar data
    recent_searches = []
    user_favorites = []
    if request.user.is_authenticated:
        recent_searches = SearchHistory.objects.filter(user=request.user).order_by('-id')[:5]
        user_favorites = FavoriteCity.objects.filter(user=request.user)

    context = {
        'weather_list': weather_list,
        'recent_searches': recent_searches,
        'user_favorites': user_favorites,
        'error_message': error_message, # Pass this to show a "Not Found" alert
    }
    return render(request, 'weather_app/index.html', context)

@login_required
def add_favorite(request, city_name):
    FavoriteCity.objects.get_or_create(user=request.user, city_name=city_name)
    return redirect('index')

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Explicitly set the backend to avoid authentication issues on Render
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('index')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def clear_history(request):
    SearchHistory.objects.filter(user=request.user).delete()
    return redirect('index')