from flask import Flask, render_template, request
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# --- API URLs ---
ZEN_QUOTES_RANDOM = "https://zenquotes.io/api/random"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

DEFAULT_CITY = "Panabo"

TAROT_ALL_URL = "https://tarotapi.dev/api/v1/cards"


def get_tarot_card():
    """Fetches a random tarot card."""
    try:
        res = requests.get("https://tarotapi.dev/api/v1/cards/random?n=1", timeout=8)
        res.raise_for_status()
        data = res.json()

        # Tarot API returns {"cards": [ {...} ]}
        cards = data.get("cards", [])
        if not cards:
            return None

        card = cards[0]
        return {
            "name": card.get("name"),
            "desc": card.get("desc"),
            "meaning_up": card.get("meaning_up"),
            "meaning_rev": card.get("meaning_rev"),
        }

    except Exception as e:
        print("Tarot API error:", e)
        return None





def get_random_quote():
    """Fetches a random inspirational quote."""
    try:
        res = requests.get(ZEN_QUOTES_RANDOM, timeout=8)
        res.raise_for_status()
        data = res.json()
        return {
            "quote": data[0]["q"],
            "author": data[0]["a"]
        }
    except Exception as e:
        print("Quote API error:", e)
        return None


def get_weather(city_name):
    """Fetches current weather using Open-Meteo."""
    try:
        geo_res = requests.get(GEOCODING_URL, params={"name": city_name, "count": 1}, timeout=8)
        geo_data = geo_res.json()
        if not geo_data.get("results"):
            return None, city_name

        location = geo_data["results"][0]
        lat, lon = location["latitude"], location["longitude"]

        weather_res = requests.get(WEATHER_URL, params={
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,weathercode",
            "timezone": "auto"
        }, timeout=8)

        weather_data = weather_res.json()
        today_index = 0

        return {
            "date": weather_data["daily"]["time"][today_index],
            "temp_max": weather_data["daily"]["temperature_2m_max"][today_index],
            "temp_min": weather_data["daily"]["temperature_2m_min"][today_index],
            "weathercode": weather_data["daily"]["weathercode"][today_index],
        }, location["name"]
    except Exception as e:
        print("Weather API error:", e)
        return None, city_name


@app.route("/")
def index():
    """Main dashboard route."""
    city = request.args.get("city", DEFAULT_CITY)
    tarot = get_tarot_card()
    quote = get_random_quote()
    weather, location = get_weather(city)

    user = {"fullname": "Guest User"}

    return render_template(
        "dashboard.html",
        user=user,
        tarot=tarot,
        quote=quote,
        weather=weather,
        city=city,
        location=location
    )




@app.route("/tarot_spread")
def tarot_spread():
    """Draw 3 random tarot cards."""
    try:
        res = requests.get("https://tarotapi.dev/api/v1/cards/random?n=3", timeout=8)
        res.raise_for_status()
        data = res.json()
        cards = data.get("cards", [])
        spread = []

        for card in cards:
            spread.append({
                "name": card.get("name"),
                "desc": card.get("desc"),
                "meaning_up": card.get("meaning_up"),
                "meaning_rev": card.get("meaning_rev"),
            })


        return render_template("spread.html", cards=spread)
    except Exception as e:
        return f"Error fetching spread: {e}"

        
@app.route("/tarot_search", methods=["GET"])
def tarot_search():
    query = request.args.get("q", "").lower().strip()
    filter_type = request.args.get("filter", "").lower().strip()

    try:
        response = requests.get(TAROT_ALL_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        cards = data.get("cards", [])
    except Exception as e:
        cards = []
        print("Error fetching tarot cards:", e)

    if query:
        cards = [card for card in cards if query in card["name"].lower()]

    if filter_type == "major":
        cards = [card for card in cards if card.get("type") == "Major Arcana"]
    elif filter_type == "minor":
        cards = [card for card in cards if card.get("type") == "Minor Arcana"]
    elif filter_type in ("wands", "cups", "swords", "pentacles"):
        cards = [card for card in cards if filter_type in card.get("suit", "").lower()]

    return render_template("tarot_search.html", cards=cards, query=query, filter_type=filter_type)


if __name__ == "__main__":
    app.run(debug=True)
