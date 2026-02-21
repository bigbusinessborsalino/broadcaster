import urllib.request
import xml.etree.ElementTree as ET
import schedule
import time
import requests
import os
from keep_alive import keep_alive
# HARDCODE YOUR WORKING CREDENTIALS HERE
TELEGRAM_BOT_TOKEN="8386271961:AAEJxcI2PSmJTYtmqOuyl2MqF9mNBXbwAsc"

TELEGRAM_CHAT_ID="-1003879192312"
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
            
            # Dig deeper into the XML to find the hidden image and news article
            for child in trend:
                if 'approx_traffic' in child.tag:
                    traffic = child.text
                elif 'picture' in child.tag:
                    image_url = child.text
                elif 'news_item' in child.tag:
                    for news_child in child:
                        if 'news_item_url' in news_child.tag:
                            news_url = news_child.text
                            break # Just grab the first/top news link
                            
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
    """Pulls global trends with images, writes them to ONE text file, and uploads."""
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

    filename = "Global_Trends_Pro.txt"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(master_content)
        
    send_telegram_document(filename)
    
    if os.path.exists(filename):
        os.remove(filename)

    print("Finished global scan and sent the pro file.\n")
if __name__ == "__main__":
    print("Broadcaster started. Running initial global scan...")
    hunt_for_new_trends() 
    
    # Schedule to run every 1 minute
    schedule.every(1).minutes.do(hunt_for_new_trends)
    
    print("Scheduler active. Waiting for the next minute loop...")
    while True:
        schedule.run_pending()
        time.sleep(1800)
