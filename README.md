# AetherCards — Daily Tarot System

A Flask web application featuring daily tarot card readings, a 3-card spread, tarot search, quote of the day, weather, quote encryption, and email delivery of spreads. User accounts are protected with Google OAuth and TOTP-based two-factor authentication (2FA).

---

## Features

- User registration and login (email/password or Google OAuth)
- TOTP two-factor authentication via Google Authenticator
- Daily tarot card of the day (consistent per session day)
- 3-card tarot spread with email delivery
- Tarot card search and filter (Major/Minor Arcana, suits)
- Quote of the day with Atbash, Caesar, and Vigenère cipher encryption
- Real-time weather by city (Open-Meteo)

---

## Requirements

- Python 3.11 or higher (tested on 3.14)
- A Google Cloud project with OAuth 2.0 credentials
- A Gmail account with an App Password enabled

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/TarotSystem3.git
cd TarotSystem3
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

- **Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
- **Windows (Command Prompt):**
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example below into a new file named `.env` in the project root. **Never commit this file.**

```env
# Google OAuth — https://console.cloud.google.com/ → APIs & Services → Credentials
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# Flask session key — use a long, random string (e.g. output of: python -c "import secrets; print(secrets.token_hex(32))")
FLASK_SECRET_KEY=replace-with-a-long-random-string

# Gmail SMTP — use an App Password, not your account password
# Enable at: Google Account → Security → 2-Step Verification → App Passwords
EMAIL_ADDRESS=your-gmail@gmail.com
EMAIL_PASSWORD=your-16-char-app-password
```

### 5. Set up Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or select an existing one)
3. Navigate to **APIs & Services → Credentials**
4. Click **Create Credentials → OAuth 2.0 Client ID**
5. Set application type to **Web application**
6. Add these to **Authorized redirect URIs**:
   ```
   http://localhost:5000/google_callback
   http://localhost:5000/google_register_callback
   ```
7. Copy the **Client ID** and **Client Secret** into your `.env`

### 6. Run the app

```bash
python start.py
```

Open your browser at [http://localhost:5000](http://localhost:5000).

---

## Project Structure

```
TarotSystem3/
├── start.py              # Main Flask application
├── requirements.txt      # Python dependencies
├── .env                  # Secret credentials (not committed)
├── .gitignore
├── static/
│   ├── cards/            # Tarot card images (78 cards)
│   ├── image/            # Background and logo assets
│   ├── style.css
│   ├── Login.css
│   ├── register.css
│   ├── search.css
│   └── about.css
├── templates/
│   ├── register.html
│   ├── login.html
│   ├── qr_otp.html
│   ├── dashboard.html
│   ├── spread.html
│   ├── tarot_search.html
│   ├── encrypt_quote.html
│   ├── encrypted_result.html
│   └── about.html
└── users.json            # Local user store (auto-created, not committed)
```

---

## External APIs Used

| API | Purpose | Auth required |
|-----|---------|--------------|
| [Tarot API](https://tarotapi.dev/) | Card data and random draws | No |
| [ZenQuotes](https://zenquotes.io/) | Inspirational quotes | No |
| [Open-Meteo](https://open-meteo.com/) | Weather forecasts | No |
| Google OAuth 2.0 | Social login / registration | Yes — see Setup step 5 |
| Gmail SMTP | Email delivery of tarot spreads | Yes — App Password |

---

## Security Notes

- Credentials are loaded from `.env` via `python-dotenv` — never hardcode secrets in source files
- `.env` is listed in `.gitignore` and will not be committed
- Passwords are stored in plain text in `users.json` — this is a development setup and should use hashing (e.g. `bcrypt`) before any production use
- TOTP 2FA is required for all accounts after registration

---

## Troubleshooting

**Google login returns an error**
- Confirm the redirect URIs in Google Cloud Console exactly match what the app generates (check the console output for the `DEBUG: Google login redirect URI:` line)

**Emails are not sending**
- Ensure you are using a Gmail **App Password**, not your account password
- Confirm 2-Step Verification is enabled on the Gmail account
- Visit `/test_email` while logged in to test the SMTP connection directly

**`Import "dotenv" could not be resolved` warning in VS Code**
- Select the project's `.venv` as the Python interpreter: `Ctrl+Shift+P` → *Python: Select Interpreter* → choose `.venv`
