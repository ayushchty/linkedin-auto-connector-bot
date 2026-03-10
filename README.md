# LinkedIn Auto Connector Bot

A Python-based automation tool for sending personalized LinkedIn connection requests with custom notes using Selenium and JavaScript.

---

## What This Does

This bot helps you automate the process of reaching out to LinkedIn users by:
- Logging into your LinkedIn account (supports 2FA and CAPTCHA)
- Finding specific profiles through search
- Sending connection requests with personalized messages
- Respecting rate limits so you don't get banned
- Looking like a real human to avoid detection
- Saving sessions so you don't have to log in every time

**Who's this for:** Sales folks, recruiters, and networkers who want to quickly grow their LinkedIn connections with relevant prospects.

---

## Features

| Feature | What It Does |
|---------|-------------|
| **Browser Automation** | Uses Selenium with undetected-chromedriver for smooth automation |
| **Human-Like Behavior** | Random delays, mouse movements, typing patterns - acts like a real person |
| **Popup Handling** | JavaScript-based interaction with LinkedIn's modal popups |
| **Rate Limiting** | Daily/weekly limits to keep your account safe |
| **Session Saving** | Remembers your login so you don't have to enter credentials each time |
| **CLI Interface** | Easy-to-use command line with progress tracking |
| **Error Handling** | Smart retry logic when things go wrong |
| **Logging** | Detailed logs for debugging and monitoring |

---

## Project Structure

```
LinkedIn Auto Connector Bot
│
├─ config/                 # Configuration stuff
│  ├─ settings.py         # BotConfig (browser, rate limits, etc.)
│  ├─ security.py         # Credential encryption
│  └─ constants.py        # API URLs and connection limits
│
├─ modules/               # Core functionality
│  ├─ authenticator.py    # Login & session handling
│  ├─ connector.py        # Send connection requests
│  ├─ rate_limiter.py     # Keep within LinkedIn's limits
│  └─ session_manager.py   # Manage saved sessions
│
├─ utils/                 # Helper functions
│  ├─ anti_detection.py   # Stealth browser tricks
│  ├─ logger.py           # Logging setup
│  └─ exceptions.py       # Custom error types
│
├─ extension/             # Chrome extension (helper)
│  ├─ content.js         # Content script for DOM interaction
│  ├─ background.js      # Background service worker
│  └─ manifest.json      # Extension manifest
│
├─ main.py               # Main LinkedInBot class
├─ cli.py                # Command-line interface
└─ Linkedin_auto_connector_bot.py  # Legacy standalone script
```

---

## Quick Start

### What You Need
- Python 3.8+
- Chrome or Firefox browser
- A LinkedIn account
- pip (Python package manager)

### Setup Steps

1. **Get the code:**
   ```bash
   git clone <repository-url>
   cd LinkedIn_Auto_Connector_Bot
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install required packages:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your credentials:**
   Create a `.env` file in the project root:
   ```env
   LINKEDIN_USERNAME=your_email@gmail.com
   LINKEDIN_PASSWORD=your_password
   SEARCH_LINK=https://www.linkedin.com/search/results/people/?keywords=recruiter
   CONNECTION_MESSAGE=Hi, I'd like to connect with you!
   MAX_CONNECT_REQUESTS=20
   ```

### Running the Bot

**Option 1: CLI (Recommended)**
```bash
python cli.py run -u your_email@gmail.com -p your_password -s "search_url" -l 20 -m "Your message"
```

**Option 2: Using main.py**
```bash
python main.py
```

**Option 3: Legacy Script**
```bash
python Linkedin_auto_connector_bot.py
```

---

## Key Modules Explained

### 1. **authenticator.py** - Login & Authentication
- Handles the LinkedIn login process
- Waits for 2FA/CAPTCHA if they show up
- Verifies successful login
- **Main Method:** `authenticate(username, password)`

### 2. **connector.py** - Connection Manager
- Finds "Connect" buttons on profile pages
- Opens the invite popup
- Fills in your custom message
- Sends the request with retry logic
- **Main Method:** `send_connection_request(profile_url, message)`

### 3. **rate_limiter.py** - Rate Limiting
- Tracks how many connections you've sent today/this week
- Adds delays between actions
- Stops you from going over LinkedIn's limits
- **Safe Limits:**
  - Daily: 100 connections
  - Weekly: 500 connections
  - Delay: 2-5 seconds between actions

### 4. **anti_detection.py** - Stealth Features
- Rotates user agents so you look like different browsers
- Simulates mouse movements and typing
- Random delays between actions
- Hides automation flags
- **Main Classes:** `StealthBrowser`, `HumanBehaviorSimulator`

### 5. **session_manager.py** - Session Persistence
- Saves encrypted sessions
- Lets you skip logging in each time
- Stores sessions in `sessions/` folder
- **Main Methods:** `save_session()`, `load_session()`

---

## Security Notes

Important stuff to keep in mind:
- Your credentials go in `.env` - never hardcode them
- The `.env` file is in `.gitignore` so it won't get pushed to GitHub
- We encrypt your credentials using the cryptography library
- Don't share your `.env` file or session files with anyone

---

## Configuration Options

Edit `config/settings.py` to customize behavior:

```python
# Browser settings
BrowserConfig:
  - browser_type: "chrome" or "firefox"
  - headless: True/False
  - window_size: (1920, 1080)
  - proxy: Optional proxy URL

# Rate limiting
RateLimitConfig:
  - daily_connection_limit: 100
  - weekly_connection_limit: 500
  - min_delay_between_actions: 2.0

# Connection behavior
ConnectionConfig:
  - personalize_message: True
  - follow_after_connect: True
  - use_shadow_dom_js: True
```

---

## Testing

Run tests to make sure everything works:
```bash
pytest tests/

# With coverage report
pytest --cov=modules tests/
```

---

## How It Works

```
1. Start Bot
   ↓
2. Login to LinkedIn (handles CAPTCHA if needed)
   ↓
3. Go to your search URL
   ↓
4. For each profile:
   ├─ Click Connect
   ├─ Click "Add a note"
   ├─ Type your message
   ├─ Click Send
   └─ Wait a few seconds (randomized)
   ↓
5. Move to next page
   ↓
6. Stop when you hit rate limit or max connections
```

---

## Common Problems & Solutions

| Problem | Fix |
|---------|-----|
| "Chromedriver not found" | Download ChromeDriver matching your Chrome version |
| "CAPTCHA appears" | Bot pauses - solve it manually and the bot continues |
| "2FA code needed" | Bot prompts you - enter the code to proceed |
| "Elements not found" | Increase wait times in `config/settings.py` |
| "Rate limited" | LinkedIn throttled you - wait 24 hours |

---

## Metrics & Logging

The bot tracks:
- **Total connections sent:** Saved in JSON
- **Failed attempts:** Logged with error details
- **Profiles followed:** Counted separately
- **Session duration:** Timed operations

Check logs at: `logs/linkedin_bot.log`

---

## Important - Use Responsibly

LinkedIn's Terms of Service don't love automated tools like this:
- Use at your own risk - LinkedIn may suspend accounts
- Keep it reasonable: 20-50 connections per day
- Always personalize your messages
- Check your account for warnings

Best practices:
- Use realistic delays between actions
- Don't send the same message to everyone
- Don't go crazy with the limits
- Watch your account for any unusual activity warnings

---

## Need Help?

Check out:
- `docs/HIGH_LEVEL_DESIGN.md` - Architecture details
- `config/` - Configuration examples
- Test files in `tests/` - Usage examples
