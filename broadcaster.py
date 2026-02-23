import urllib.request
import xml.etree.ElementTree as ET
import schedule
import time
import requests
import os
import hashlib
import threading
from flask import Flask
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# --- THE DUMMY WEB SERVER ---
# This opens the door so Render doesn't kill the app!
app_web = Flask(__name__)

@app_web.route('/')
def health_check():
    return "📡 Broadcaster is Alive and Hunting for News!"

def run_web():
    # Render assigns a dynamic port, so we MUST grab it from the OS
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)
# ----------------------------

# Pulling credentials from Render Environment Variables safely
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1003879192312")
MONGO_URI = os.getenv("MONGO_URI")

# All 10 regular news countries + Japan for Anime
COUNTRIES = {
    "IN": "India", "US": "USA", "JP": "Japan", "GB": "UK", 
    "CA": "Canada", "AU": "Australia", "DE": "Germany", 
    "FR": "France", "BR": "Brazil", "KR": "South Korea", 
    "SG": "Singapore"
}

def send_telegram_document(file_path):
    """Sends the master document to your Telegram channel."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument?chat_id={TELEGRAM_CHAT_ID}"
    data = {"caption": "🚨 GRAND LINE NEWS: GLOBAL TRENDS 🚨"}
    
    with open(file_path, 'rb') as f:
        files = {"document": (file_path, f)} 
        try:
            response = requests.post(url, data=data, files=files)
            if response.status_code == 200:
                print(f"✅ Successfully sent {file_path} to Telegram!")
            else:
                print(f"❌ TELEGRAM REJECTED IT: {response.text}")
        except Exception as e:
            print(f"Network error: {e}")

def get_real_trends(country_code, country_name, limit=10):
    """Pulls top trends, images, and news links from Google RSS."""
    url = f"https://trends.google.com/trending/rss?geo={country_code}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        items = root.findall(".//item")
        
        results = []
        for trend in items[:limit]:
            topic = trend.find("title").text
            traffic = "N/A"
            image_url = "No Image"
            news_url = "No Link"
            
            for child in trend:
                if 'approx_traffic' in child.tag:
                    traffic = child.text
                elif 'picture' in child.tag:
                    image_url = child.text
                elif 'news_item' in child.tag:
                    for news_child in child:
                        if 'news_item_url' in news_child.tag:
                            news_url = news_child.text
                            break 
                            
            results.append({
                "topic": topic, 
                "searches": traffic,
                "image": image_url,
                "news_link": news_url
            })
            
        return results
    except Exception as e:
        print(f"Error fetching trends for {country_name}: {e}")
        return []

def hunt_for_new_trends():
    """Pulls global trends, checks MongoDB for duplicates, and uploads."""
    print("Hunting for global trends with Images & Links...")
    master_content = "=== GRAND LINE NEWS: GLOBAL TRENDS ===\n\n"
    
    for code, name in COUNTRIES.items():
        print(f"Fetching {name}...")
        trends = get_real_trends(code, name, limit=10) 
        
        if trends:
            master_content += f"--- TOP 10 IN {name.upper()} ---\n"
            for t in trends:
                master_content += f"Topic: {t['topic']} ({t['searches']} searches)\n"
                master_content += f"Image: {t['image']}\n"
                master_content += f"Source: {t['news_link']}\n\n"
            master_content += "\n"
        
        time.sleep(1) 

    # --- MONGODB DUPLICATE CHECK ---
    # Create a unique 'fingerprint' of the text
    content_hash = hashlib.md5(master_content.encode('utf-8')).hexdigest()
    
    if MONGO_URI:
        try:
            client = MongoClient(MONGO_URI)
            db = client.grandline_news
            collection = db.trends_history
            
            last_record = collection.find_one({"_id": "latest_trends"})
            
            if last_record and last_record['hash'] == content_hash:
                print("🛑 No new trends detected. Skipping Telegram upload to avoid spam.")
                return  # Exit the function early!
            
            # If it's new, update the database with the new fingerprint
            collection.update_one(
                {"_id": "latest_trends"},
                {"$set": {"hash": content_hash}},
                upsert=True
            )
        except Exception as e:
            print(f"⚠️ MongoDB Error (sending anyway): {e}")

    # --- SEND TO TELEGRAM ---
    filename = "Global_Trends_Pro.txt"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(master_content)
        
    send_telegram_document(filename)
    
    if os.path.exists(filename):
        os.remove(filename)

    print("Finished global scan.\n")

if __name__ == "__main__":
    # 1. Start the anti-sleep dummy server natively in the background
    print("🌐 Starting Dummy Web Server for Render Health Check...")
    threading.Thread(target=run_web, daemon=True).start()
    
    # 2. Run the main bot logic
    print("Broadcaster started. Running initial global scan...")
    hunt_for_new_trends() 
    
    # Schedule to run every 30 minutes
    schedule.every(30).minutes.do(hunt_for_new_trends)
    
    print("Scheduler active. Waiting for the next 30-minute loop...")
    while True:
        schedule.run_pending()
        time.sleep(1) # Rests for 1 second so it doesn't max out your CPU
