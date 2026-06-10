from flask import Flask, render_template, request, redirect, url_for, session, flash
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import pyotp, qrcode, io, base64, json, re, os, requests

load_dotenv()
from datetime import datetime
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")

# Initialize OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    access_token_url='https://oauth2.googleapis.com/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',  
    client_kwargs={'scope': 'openid email profile'},
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',  
)

USERS_FILE = 'users.json'

# --- API URLs ---
ZEN_QUOTES_RANDOM = "https://zenquotes.io/api/random"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_CITY = "Panabo"
TAROT_ALL_URL = "https://tarotapi.dev/api/v1/cards"

# --- Email Configuration ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# --- Helper functions ---
def is_strong_password(password):
    # At least 8 characters, one uppercase, one lowercase, one number, and one special char
    pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!#%*?&])[A-Za-z\d@$!#%*?&]{8,}$'
    return bool(re.match(pattern, password))

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

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


def filter_cards_by_type(cards, filter_type):
    """Filter cards by type (major arcana, minor arcana, or specific suits)."""
    if not filter_type:
        return cards
    
    filtered_cards = []
    
    for card in cards:
        card_name = card.get("name", "").lower()
        
        if filter_type == "major":
            # Major Arcana cards (The Fool, The Magician, etc.)
            if any(major in card_name for major in [
                "the fool", "the magician", "the high priestess", "the empress", "the emperor",
                "the hierophant", "the lovers", "the chariot", "strength", "the hermit",
                "wheel of fortune", "justice", "the hanged man", "death", "temperance",
                "the devil", "the tower", "the star", "the moon", "the sun", "judgement",
                "the world"
            ]):
                filtered_cards.append(card)
        
        elif filter_type == "minor":
            # Minor Arcana cards (numbered cards and court cards)
            if not any(major in card_name for major in [
                "the fool", "the magician", "the high priestess", "the empress", "the emperor",
                "the hierophant", "the lovers", "the chariot", "strength", "the hermit",
                "wheel of fortune", "justice", "the hanged man", "death", "temperance",
                "the devil", "the tower", "the star", "the moon", "the sun", "judgement",
                "the world"
            ]):
                filtered_cards.append(card)
        
        elif filter_type == "wands":
            if "wands" in card_name:
                filtered_cards.append(card)
        
        elif filter_type == "cups":
            if "cups" in card_name:
                filtered_cards.append(card)
        
        elif filter_type == "swords":
            if "swords" in card_name:
                filtered_cards.append(card)
        
        elif filter_type == "pentacles":
            if "pentacles" in card_name:
                filtered_cards.append(card)
    
    return filtered_cards

def get_local_card_image(card_name):
    """Maps tarot card names to local image filenames."""
    if not card_name:
        return None
    
    # Convert card name to lowercase and replace spaces/special chars
    name_lower = card_name.lower().replace(" ", "").replace("'", "").replace("-", "")
    
    # Map common variations to local filenames
    name_mapping = {
        # Major Arcana
        "thefool": "thefool.jpeg",
        "themagician": "themagician.jpeg", 
        "thehighpriestess": "thehighpriestess.jpeg",
        "theempress": "theempress.jpeg",
        "theemperor": "theemperor.jpeg",
        "thehierophant": "thehierophant.jpeg",
        "thelovers": "TheLovers.jpg",
        "thechariot": "thechariot.jpeg",
        "thestrength": "thestrength.jpeg",
        "thehermit": "thehermit.jpeg",
        "wheeloffortune": "wheeloffortune.jpeg",
        "justice": "justice.jpeg",
        "thehangedman": "thehangedman.jpeg",
        "death": "death.jpeg",
        "temperance": "temperance.jpeg",
        "thedevil": "thedevil.jpeg",
        "thetower": "thetower.jpeg",
        "thestar": "thestar.jpeg",
        "themoon": "themoon.jpeg",
        "thesun": "thesun.jpeg",
        "judgement": "judgement.jpeg",
        "theworld": "theworld.jpeg",
        
        # Cups
        "aceofcups": "aceofcups.jpeg",
        "twoofcups": "twoofcups.jpeg",
        "threeofcups": "threeofcups.jpeg",
        "fourofcups": "fourofcups.jpeg",
        "fiveofcups": "fiveofcups.jpeg",
        "sixofcups": "sixofcups.jpeg",
        "sevenofcups": "sevenofcups.jpeg",
        "eightofcups": "eightofcups.jpeg",
        "nineofcups": "nineofcups.jpeg",
        "tenofcups": "tenofcups.jpeg",
        "pageofcups": "pageofcups.jpeg",
        "knightofcups": "knightofcups.jpeg",
        "queenofcups": "queenofcups.jpeg",
        "kingofcups": "kingofcups.jpeg",
        
        # Pentacles
        "aceofpentacles": "aceofpentacles.jpeg",
        "twoofpentacles": "twoofpentacles.jpeg",
        "threeofpentacles": "threeofpentacles.jpeg",
        "fourofpentacles": "fourofpentacles.jpeg",
        "fiveofpentacles": "fiveofpentacles.jpeg",
        "sixofpentacles": "sixofpentacles.jpeg",
        "sevenofpentacles": "sevenofpentacles.jpeg",
        "eightofpentacles": "eightofpentacles.jpeg",
        "nineofpentacles": "nineofpentacles.jpeg",
        "tenofpentacles": "tenofpentacles.jpeg",
        "pageofpentacles": "pageofpentacles.jpeg",
        "knightofpentacles": "knightofpentacles.jpeg",
        "queenofpentacles": "queenofpentacles.jpeg",
        "kingofpentacles": "kingofpentacles.jpeg",
        
        # Swords
        "aceofswords": "aceofswords.jpeg",
        "twoofswords": "twoofswords.jpeg",
        "threeofswords": "threeofswords.jpeg",
        "fourofswords": "fourofswords.jpeg",
        "fiveofswords": "fiveofswords.jpeg",
        "sixofswords": "sixofswords.jpeg",
        "sevenofswords": "sevenofswords.jpeg",
        "eightofswords": "eightofswords.jpeg",
        "nineofswords": "nineofswords.jpeg",
        "tenofswords": "tenofswords.jpeg",
        "pageofswords": "pageofswords.jpeg",
        "knightofswords": "knightofswords.jpeg",
        "queenofswords": "queenofswords.jpeg",
        "kingofswords": "kingofswords.jpeg",
        
        # Wands
        "aceofwands": "aceofwands.jpeg",
        "twoofwands": "twoofwands.jpeg",
        "threeofwands": "threeofwands.jpeg",
        "fourofwands": "fourofwands.jpeg",
        "fiveofwands": "fiveofwands.jpeg",
        "sixofwands": "sixofwands.jpeg",
        "sevenofwands": "sevenofwands.jpeg",
        "eightofwands": "eightofwands.jpeg",
        "nineofwands": "nineofwands.jpeg",
        "tenofwands": "tenofwands.jpeg",
        "pageofwands": "pageofwands.jpeg",
        "knightofwands": "knightofwands.jpeg",
        "queenofwands": "queenofwands.jpeg",
        "kingofwands": "kingofwands.jpeg",
    }
    
    # Try exact match first
    if name_lower in name_mapping:
        return name_mapping[name_lower]
    
    # Try partial matches for variations
    for key, filename in name_mapping.items():
        if key in name_lower or name_lower in key:
            return filename
    
    # Default fallback
    return "thefool.jpeg"

def get_tarot_card_of_the_day():
    """Gets the tarot card of the day - same card for entire day."""
    from datetime import datetime
    
    # Get today's date as string (YYYY-MM-DD)
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Check if we already have a tarot card for today
    if 'tarot_card_date' in session and session['tarot_card_date'] == today:
        if 'tarot_card_of_day' in session:
            print(f"Using cached tarot card for {today}: {session['tarot_card_of_day']['name']}")
            return session['tarot_card_of_day']
    
    # Generate new tarot card for today
    print(f"Generating new tarot card for {today}")
    tarot = get_tarot_card()
    
    if tarot:
        # Store in session with today's date
        session['tarot_card_of_day'] = tarot
        session['tarot_card_date'] = today
        print(f"New tarot card stored: {tarot['name']}")
    
    return tarot

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

def get_quote_of_the_day():
    """Gets the inspirational quote of the day - same quote for entire day."""
    from datetime import datetime
    
    # Get today's date as string (YYYY-MM-DD)
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Check if we already have a quote for today
    if 'quote_date' in session and session['quote_date'] == today:
        if 'quote_of_day' in session:
            print(f"Using cached quote for {today}: {session['quote_of_day']['quote'][:50]}...")
            return session['quote_of_day']
    
    # Generate new quote for today
    print(f"Generating new quote for {today}")
    quote = get_random_quote()
    
    if quote:
        # Store in session with today's date
        session['quote_of_day'] = quote
        session['quote_date'] = today
        print(f"New quote stored: {quote['quote'][:50]}...")
    
    return quote

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

# --- Encryption Functions ---
def atbash_cipher(text):
    """Atbash cipher: A=Z, B=Y, C=X, etc."""
    result = ""
    for char in text:
        if char.isalpha():
            if char.isupper():
                result += chr(90 - (ord(char) - 65))
            else:
                result += chr(122 - (ord(char) - 97))
        else:
            result += char
    return result

def caesar_cipher(text, shift):
    """Caesar cipher with given shift value."""
    result = ""
    for char in text:
        if char.isalpha():
            if char.isupper():
                result += chr((ord(char) - 65 + shift) % 26 + 65)
            else:
                result += chr((ord(char) - 97 + shift) % 26 + 97)
        else:
            result += char
    return result

def vigenere_cipher(text, key):
    """Vigenère cipher with given key."""
    result = ""
    key_index = 0
    key = key.upper()
    
    for char in text:
        if char.isalpha():
            if char.isupper():
                result += chr((ord(char) - 65 + ord(key[key_index % len(key)]) - 65) % 26 + 65)
            else:
                result += chr((ord(char) - 97 + ord(key[key_index % len(key)]) - 65) % 26 + 97)
            key_index += 1
        else:
            result += char
    return result

def generate_qr_code(text):
    """Generate QR code for given text."""
    qr = qrcode.make(text)
    buffer = io.BytesIO()
    qr.save(buffer, format='PNG')
    qr_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return qr_data

def test_email_connection():
    """Test basic email connection."""
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.quit()
        return True, "Connection successful"
    except Exception as e:
        return False, f"Connection failed: {e}"

def send_tarot_email(recipient_email, cards, user_name):
    """Send tarot spread via email."""
    try:
        print(f"DEBUG: Starting email send to {recipient_email}")
        print(f"DEBUG: User: {user_name}")
        print(f"DEBUG: Cards count: {len(cards)}")
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = recipient_email
        msg['Subject'] = f"Your Tarot Spread - {datetime.now().strftime('%B %d, %Y')}"
        
        # Create simple HTML content first
        current_time = datetime.now()
        
        # Build cards HTML
        cards_html = ""
        for i, card in enumerate(cards, 1):
            cards_html += f"""
            <div style="background-color: #f9f5ff; padding: 20px; margin-bottom: 20px; border-radius: 8px; border-left: 4px solid #7b1fa2;">
                <h3 style="color: #7b1fa2; margin-top: 0;">Card {i}: {card['name']}</h3>
                <p style="color: #333; margin-bottom: 10px;"><strong>Meaning (Upright):</strong> {card['meaning_up']}</p>
                <p style="color: #333; margin-bottom: 10px;"><strong>Meaning (Reversed):</strong> {card['meaning_rev']}</p>
                <p style="color: #666; font-style: italic;">{card['desc']}</p>
            </div>
            """
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <h2 style="color: #7b1fa2; text-align: center; margin-bottom: 30px;">
                    Your Personal Tarot Reading
                </h2>
                
                <p style="color: #666; font-size: 16px; margin-bottom: 30px;">
                    Hello {user_name},<br><br>
                    Here are your tarot cards drawn for you today:
                </p>
                
                <div style="margin-bottom: 30px;">
                    {cards_html}
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                    <p style="color: #999; font-size: 14px;">
                        This reading was generated by Daily Tarot System<br>
                        Sent on {current_time.strftime('%B %d, %Y at %I:%M %p')}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        print("DEBUG: HTML content created successfully")
        
        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        print("DEBUG: HTML part attached to message")
        
        # Send email
        print("DEBUG: Connecting to SMTP server...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        print("DEBUG: Starting TLS...")
        server.starttls()
        print("DEBUG: Logging in...")
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        print("DEBUG: Converting message to string...")
        text = msg.as_string()
        print("DEBUG: Sending email...")
        server.sendmail(EMAIL_ADDRESS, recipient_email, text)
        print("DEBUG: Closing connection...")
        server.quit()
        print("DEBUG: Email sent successfully!")
        
        # Alternative SSL method if above fails:
        # import ssl
        # context = ssl.create_default_context()
        # server = smtplib.SMTP_SSL(SMTP_SERVER, 465, context=context)
        # server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        # server.sendmail(EMAIL_ADDRESS, recipient_email, text)
        # server.quit()
        
        return True
    except Exception as e:
        print(f"Email error: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

# --- Routes ---
@app.route('/')
def home():
   return redirect(url_for('register'))
   #return redirect(url_for('dashboard')) #delete

@app.route('/register', methods=['GET', 'POST'])
def register():
    users = load_users()
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Check if passwords match
        if password != confirm_password:
            flash("❌ Passwords do not match!", "error")
            return redirect(url_for('register'))

        # Check if password is strong
        if not is_strong_password(password):
            flash("❌ Password must be 8+ characters with uppercase, lowercase, number, and special character.", "error")
            return redirect(url_for('register'))

        # Check if email already exists
        if email in users:
            flash("❌ Email already registered!", "error")
            return redirect(url_for('register'))

        # Create a new user
        totp_secret = pyotp.random_base32()
        users[email] = {
            'fullname': fullname,
            'email': email,
            'password': password,
            'totp_secret': totp_secret,
            'verified': False
        }
        save_users(users)

        session['email'] = email
        return redirect(url_for('show_qr'))

    return render_template('register.html')


# --- Google Register/Login ---
@app.route('/google_login')
def google_login():
    try:
        redirect_uri = url_for('google_callback', _external=True)
        print(f"DEBUG: Google login redirect URI: {redirect_uri}")
        return google.authorize_redirect(redirect_uri)
    except Exception as e:
        print(f"ERROR: Google login failed: {e}")
        flash("❌ Google login failed. Please try again.", "error")
        return redirect(url_for('login'))

@app.route('/google_register')
def google_register():
    try:
        redirect_uri = url_for('google_register_callback', _external=True)
        print(f"DEBUG: Google register redirect URI: {redirect_uri}")
        return google.authorize_redirect(redirect_uri)
    except Exception as e:
        print(f"ERROR: Google register failed: {e}")
        flash("❌ Google registration failed. Please try again.", "error")
        return redirect(url_for('register'))

@app.route('/google_callback')
def google_callback():
    try:
        print("DEBUG: Google callback received")
        token = google.authorize_access_token()
        print(f"DEBUG: Token received: {token is not None}")
        
        resp = google.get('userinfo')
        print(f"DEBUG: Userinfo response status: {resp.status_code}")
        
        user_info = resp.json()
        print(f"DEBUG: User info: {user_info}")
        
        email = user_info.get('email')
        name = user_info.get('name')
        
        if not email:
            flash("❌ Could not retrieve email from Google. Please try again.", "error")
            return redirect(url_for('login'))

        users = load_users()

        # Check if user exists in our system
        if email not in users:
            flash("❌ Account not found. Please register first before logging in with Google.", "error")
            return redirect(url_for('register'))

        # User exists, proceed with login
        session['email'] = email
        flash("✅ Google login successful! Please complete 2FA setup.", "success")
        return redirect(url_for('show_qr'))
        
    except Exception as e:
        print(f"ERROR: Google callback failed: {e}")
        import traceback
        traceback.print_exc()
        flash("❌ Google login failed. Please try again.", "error")
        return redirect(url_for('login'))

@app.route('/google_register_callback')
def google_register_callback():
    try:
        print("DEBUG: Google register callback received")
        token = google.authorize_access_token()
        print(f"DEBUG: Token received: {token is not None}")
        
        resp = google.get('userinfo')
        print(f"DEBUG: Userinfo response status: {resp.status_code}")
        
        user_info = resp.json()
        print(f"DEBUG: User info: {user_info}")
        
        email = user_info.get('email')
        name = user_info.get('name')
        
        if not email:
            flash("❌ Could not retrieve email from Google. Please try again.", "error")
            return redirect(url_for('register'))

        users = load_users()

        # Check if user already exists
        if email in users:
            flash("❌ Email already registered! Please use login instead.", "error")
            return redirect(url_for('register'))

        # Create new user account
        totp_secret = pyotp.random_base32()
        users[email] = {
            'fullname': name or email.split('@')[0],  # Use email prefix if name is None
            'email': email,
            'password': None,  # No password for Google OAuth users
            'totp_secret': totp_secret,
            'verified': False
        }
        save_users(users)

        session['email'] = email
        flash("✅ Google account registered successfully! Please set up 2FA.", "success")
        return redirect(url_for('show_qr'))
        
    except Exception as e:
        print(f"ERROR: Google register callback failed: {e}")
        import traceback
        traceback.print_exc()
        flash("❌ Google registration failed. Please try again.", "error")
        return redirect(url_for('register'))


# --- Show QR Code for 2FA setup ---
@app.route('/show_qr')
def show_qr():
    email = session.get('email')
    if not email:
        return redirect(url_for('register'))

    users = load_users()
    totp_secret = users[email]['totp_secret']

    # Generate QR code for Google Authenticator
    totp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(
        name=email, issuer_name="AetherCards"
    )
    qr = qrcode.make(totp_uri)
    buffer = io.BytesIO()
    qr.save(buffer, format='PNG')
    qr_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return render_template('qr_otp.html', qr_data=qr_data)


# --- Verify OTP ---
@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    email = session.get('email')
    if not email:
        return redirect(url_for('register'))

    users = load_users()
    totp_secret = users[email]['totp_secret']
    otp = request.form['otp']

    totp = pyotp.TOTP(totp_secret)
    if totp.verify(otp):
        users[email]['verified'] = True
        save_users(users)
        flash("✅ OTP verified successfully! Welcome to your dashboard.", "success")
        return redirect(url_for('dashboard'))
    else:
        flash("❌ Invalid OTP. Please try again.", "error")
        return redirect(url_for('show_qr'))



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Example: get form data
        email = request.form.get('email')
        password = request.form.get('password')

        users = load_users()

        # Check if email exists and password is correct
        if email in users and users[email]['password'] == password:
            user = users[email]

            # If user has not completed 2FA setup yet, send them to QR setup
            if not user.get('verified'):
                session['email'] = email
                flash("ℹ️ Please complete 2FA setup to continue.", "info")
                return redirect(url_for('show_qr'))

            # User is verified → require OTP for login
            otp = request.form.get('otp')
            if not otp:
                flash("❌ OTP is required to login.", "error")
                return redirect(url_for('login'))

            totp = pyotp.TOTP(user['totp_secret'])
            if not totp.verify(otp):
                flash("❌ Invalid OTP. Please try again.", "error")
                return redirect(url_for('login'))

            # Successful OTP → login
            session['email'] = email
            flash("✅ Login successful! Welcome back.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("❌ Invalid email or password. Please try again.", "error")
            return redirect(url_for('login'))

    # If GET request, just show the login page
    return render_template('login.html')


@app.route('/about')
def about():
    
    #hide
    email = session.get('email')
    if not email:
        return redirect(url_for('register'))
    
    users = load_users()
    if not users[email].get('verified'):
        return redirect(url_for('show_qr'))
    #
    
    return render_template('about.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))  # redirects to your login page



@app.route('/dashboard')
def dashboard():
    
    
    email = session.get('email')
    if not email:
        return redirect(url_for('register'))

    users = load_users()
    if not users[email].get('verified'):
        return redirect(url_for('show_qr'))
    

    #delete
    '''
    user = {
        "fullname": "Guest User",
        "email": "guest@example.com",
        "verified": True
    }
    '''
    #

    # Fetch data for dashboard
    city = request.args.get("city", DEFAULT_CITY)
    
    # Get or generate tarot card of the day (same card for entire day)
    tarot = get_tarot_card_of_the_day()

     # Add image path
    tarot["image"] = url_for("static", filename="cards/" + get_local_card_image(tarot["name"]))
    
    # Get or generate quote of the day (same quote for entire day)
    quote = get_quote_of_the_day()
    weather, location = get_weather(city)

    # Store quote in session for encryption feature
    if quote:
        session['current_quote'] = quote

    return render_template('dashboard.html', 
                         user=users[email],
                       # user=user, #delete
                         tarot=tarot,
                         quote=quote,
                         weather=weather,
                         city=city,
                         location=location)

@app.route("/tarot_spread")
def tarot_spread():
    
    
    #hide
    email = session.get('email')
    if not email:
        return redirect(url_for('register'))

    users = load_users()
    if not users[email].get('verified'):
        return redirect(url_for('show_qr'))
    

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
                "image": url_for("static", filename="cards/" + get_local_card_image(card.get("name"))),
            })

        # Store spread in session for email feature
        session['current_spread'] = spread

        return render_template("spread.html", cards=spread)
    except Exception as e:
        flash(f"Error fetching spread: {e}", "error")
        return redirect(url_for('dashboard'))


@app.route("/test_email")
def test_email_route():
    """Test email configuration."""
    email = session.get('email')
    if not email:
        return redirect(url_for('register'))

    users = load_users()
    if not users[email].get('verified'):
        return redirect(url_for('show_qr'))

    success, message = test_email_connection()
    if success:
        flash(f"✅ Email test successful: {message}", "success")
    else:
        flash(f"❌ Email test failed: {message}", "error")
    
    return redirect(url_for('dashboard'))

@app.route("/test_api")
def test_api_route():
    """Test tarot API response."""
    try:
        response = requests.get(TAROT_ALL_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        cards = data.get("cards", [])
        
        if cards:
            first_card = cards[0]
            return f"""
            <h3>API Test Results</h3>
            <p><strong>Total cards:</strong> {len(cards)}</p>
            <p><strong>First card keys:</strong> {list(first_card.keys())}</p>
            <p><strong>First card data:</strong></p>
            <pre>{first_card}</pre>
            <p><a href="/dashboard">Back to Dashboard</a></p>
            """
        else:
            return "<p>No cards found in API response</p>"
    except Exception as e:
        return f"<p>Error: {e}</p>"

@app.route("/test_send_email")
def test_send_email_route():
    """Test sending a simple email."""
    email = session.get('email')
    if not email:
        return redirect(url_for('register'))

    users = load_users()
    if not users[email].get('verified'):
        return redirect(url_for('show_qr'))

    # Test with a simple email
    test_cards = [
        {
            'name': 'Test Card 1',
            'desc': 'This is a test card description',
            'meaning_up': 'Test upright meaning',
            'meaning_rev': 'Test reversed meaning'
        }
    ]
    
    user_name = users[email]['fullname']
    recipient = email  # Send to yourself for testing
    
    if send_tarot_email(recipient, test_cards, user_name):
        flash(f"✅ Test email sent successfully to {recipient}!", "success")
    else:
        flash("❌ Test email failed. Check console for error details.", "error")
    
    return redirect(url_for('dashboard'))

@app.route("/send_tarot_email", methods=['POST'])
def send_tarot_email_route():
    """Send tarot spread via email."""
    email = session.get('email')
    if not email:
        return redirect(url_for('register'))

    users = load_users()
    if not users[email].get('verified'):
        return redirect(url_for('show_qr'))

    recipient_email = request.form.get('recipient_email', '').strip()
    
    if not recipient_email:
        flash("❌ Please enter a valid email address.", "error")
        return redirect(url_for('tarot_spread'))

    # Get stored spread from session
    spread = session.get('current_spread')
    if not spread:
        flash("❌ No tarot spread available. Please draw cards first.", "error")
        return redirect(url_for('tarot_spread'))

    # Debug information
    print(f"DEBUG: Sending email to {recipient_email}")
    print(f"DEBUG: User name: {users[email]['fullname']}")
    print(f"DEBUG: Spread cards: {len(spread) if spread else 0}")
    
    # Send email
    user_name = users[email]['fullname']
    if send_tarot_email(recipient_email, spread, user_name):
        flash(f"✅ Tarot spread sent successfully to {recipient_email}!", "success")
    else:
        flash("❌ Failed to send email. Please check your email configuration.", "error")

    return redirect(url_for('show_spread'))

@app.route("/show_spread")
def show_spread():
    """Show the current spread without regenerating cards."""

    #hide
    
    email = session.get('email')
    if not email:
        return redirect(url_for('register'))

    users = load_users()
    if not users[email].get('verified'):
        return redirect(url_for('show_qr'))
        
    #
    

    # Get stored spread from session
    spread = session.get('current_spread')
    if not spread:
        flash("❌ No tarot spread available. Please draw cards first.", "error")
        return redirect(url_for('tarot_spread'))

    return render_template("spread.html", cards=spread)

@app.route("/tarot_search")
def tarot_search():
    """Search for tarot cards."""

    #hide
    
    email = session.get('email')
    if not email:
        return redirect(url_for('register'))

    users = load_users()
    if not users[email].get('verified'):
        return redirect(url_for('show_qr'))
    
    #

    query = request.args.get("q", "").lower().strip()
    filter_type = request.args.get("filter", "").lower().strip()

    # Fetch all tarot cards
    try:
        response = requests.get(TAROT_ALL_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        cards = data.get("cards", [])
        
        # Debug: Print first card structure
        if cards:
            print("DEBUG: First card structure:", cards[0])
            print("DEBUG: Available fields:", list(cards[0].keys()))
    except Exception as e:
        cards = []
        print("Error fetching tarot cards:", e)

    # Apply filters
    if filter_type:
        cards = filter_cards_by_type(cards, filter_type)
    elif query:
        cards = [card for card in cards if query in card["name"].lower()]

    # Add image paths to each card
    for card in cards:
        card["image"] = url_for("static", filename="cards/" + get_local_card_image(card.get("name")))

    return render_template("tarot_search.html", cards=cards, query=query, filter_type=filter_type)

@app.route("/encrypt_quote")
def encrypt_quote():
    """Show encryption page with current quote."""
    
    #hide
    
    email = session.get('email')
    if not email:
        return redirect(url_for('register'))

    users = load_users()
    if not users[email].get('verified'):
        return redirect(url_for('show_qr'))
    
    #    

    # Get stored quote from session
    quote = session.get('current_quote')
    if not quote:
        flash("❌ No quote available. Please refresh the dashboard first.", "error")
        return redirect(url_for('dashboard'))

    return render_template("encrypt_quote.html", quote=quote)

@app.route("/encrypt_message", methods=['POST'])
def encrypt_message():
    """Encrypt the message using selected cipher."""
    email = session.get('email')
    if not email:
        return redirect(url_for('register'))

    users = load_users()
    if not users[email].get('verified'):
        return redirect(url_for('show_qr'))

    message = request.form.get('message', '')
    cipher_type = request.form.get('cipher_type', '')
    
    if not message or not cipher_type:
        flash("❌ Missing message or cipher type.", "error")
        return redirect(url_for('encrypt_quote'))

    encrypted_message = ""
    cipher_name = ""
    
    if cipher_type == 'atbash':
        encrypted_message = atbash_cipher(message)
        cipher_name = "Atbash"
    elif cipher_type == 'caesar':
        shift = int(request.form.get('caesar_shift', 3))
        encrypted_message = caesar_cipher(message, shift)
        cipher_name = f"Caesar (shift {shift})"
    elif cipher_type == 'vigenere':
        key = request.form.get('vigenere_key', 'KEY')
        encrypted_message = vigenere_cipher(message, key)
        cipher_name = f"Vigenère (key: {key})"
    else:
        flash("❌ Invalid cipher type.", "error")
        return redirect(url_for('encrypt_quote'))

    # Generate QR code for encrypted message
    qr_data = generate_qr_code(encrypted_message)

    return render_template("encrypted_result.html", 
                         original_message=message,
                         encrypted_message=encrypted_message,
                         cipher_name=cipher_name,
                         qr_data=qr_data)


if __name__ == "__main__":
    app.run(debug=True)




