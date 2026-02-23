import urllib.request
import xml.etree.ElementTree as ET
import schedule
import time
import requests
import os
import threading
from flask import Flask
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# --- THE DUMMY WEB SERVER ---
app_web = Flask(__name__)

@app_web.route('/')
def health_check():
    return "📡 Broadcaster is Alive and Hunting for News!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)
# ----------------------------

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1003879192312")
MONGO_URI = os.getenv("MONGO_URI")

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

def get_anime_trends(limit=7):
    """Pulls the latest English Anime news to fill the Japan quota."""
    url = "https://www.animenewsnetwork.com/news/rss.xml"
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        items = root.findall(".//item")
        
        results = []
        for item in items[:limit]:
            topic = item.find("title").text
            link_tag = item.find("link")
            link = link_tag.text if link_tag is not None else "No Link"
            
            results.append({
                "topic": topic, 
                "searches": "Anime Trending",
                "image": "No Image",
                "news_link": link
            })
        return results
    except Exception as e:
        print(f"Error fetching Anime trends: {e}")
        return []

def get_real_trends(country_code, country_name, limit=10):
    """Pulls top trends from Google RSS."""
    url = f"https://trends.google.com/trending/rss?geo={country_code}"
    headers = {'User-Agent': 'Mozilla/5.0'}
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
    """Pulls trends, checks topics individually, and uploads."""
    print("Hunting for global trends...")
    
    # 1. Connect to Database for Topic-Level Duplicate Checking
    db_collection = None
    if MONGO_URI:
        try:
            client = MongoClient(MONGO_URI)
            db = client.grandline_news
            db_collection = db.published_topics
        except Exception as e:
            print(f"⚠️ MongoDB Connection Error: {e}")

    master_content = "=== GRAND LINE NEWS: GLOBAL TRENDS ===\n\n"
    new_trends_found = 0
    
    for code, name in COUNTRIES.items():
        print(f"Fetching {name}...")
        
        # Japan gets 70% Anime, 30% Google Trends
        if code == "JP":
            trends = get_anime_trends(limit=7) + get_real_trends(code, name, limit=3)
        else:
            trends = get_real_trends(code, name, limit=10) 
        
        country_content = ""
        for t in trends:
            topic_name = t['topic'].strip()
            
            # --- TOPIC-LEVEL DUPLICATE CHECK ---
            is_new = True
            if db_collection is not None:
                if db_collection.find_one({"_id": topic_name}):
                    is_new = False
                else:
                    # Save the new topic so we never post it again
                    db_collection.insert_one({"_id": topic_name, "timestamp": time.time()})
            
            if is_new:
                country_content += f"Topic: {topic_name} ({t['searches']} searches)\n"
                country_content += f"Image: {t['image']}\n"
                country_content += f"Source: {t['news_link']}\n\n"
                new_trends_found += 1
                
        if country_content:
            master_content += f"--- NEW TRENDS IN {name.upper()} ---\n{country_content}\n"
        
        time.sleep(1) 

    # --- FINAL TEXT FILE LOGIC ---
    filename = "Global_Trends_Pro.txt"
    
    if new_trends_found == 0:
        print("🛑 No new trends detected. Sending empty notification.")
        with open(filename, "w", encoding="utf-8") as file:
            file.write("No new trends right now.")
    else:
        with open(filename, "w", encoding="utf-8") as file:
            file.write(master_content)
        
    send_telegram_document(filename)
    
    if os.path.exists(filename):
        os.remove(filename)

    print(f"Finished global scan. Found {new_trends_found} new topics.\n")

if __name__ == "__main__":
    print("🌐 Starting Dummy Web Server for Render Health Check...")
    threading.Thread(target=run_web, daemon=True).start()
    
    print("Broadcaster started. Running initial global scan...")
    hunt_for_new_trends() 
    
    schedule.every(30).minutes.do(hunt_for_new_trends)
    
    print("Scheduler active. Waiting for the next 30-minute loop...")
    while True:
        schedule.run_pending()
        time.sleep(1)
