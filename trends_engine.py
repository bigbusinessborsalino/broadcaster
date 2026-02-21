import urllib.request
import xml.etree.ElementTree as ET

def get_real_trends(country_code="IN", country_name="India", limit=25):
    # Using the official RSS feed so Google doesn't block us with 404 errors
    url = f"https://trends.google.com/trending/rss?geo={country_code}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        items = root.findall(".//item")
        
        results = []
        for trend in items[:limit]:
            topic = trend.find("title").text
            
            # Smart search for the traffic tag to bypass broken XML namespaces
            traffic = "N/A"
            for child in trend:
                if 'approx_traffic' in child.tag:
                    traffic = child.text
                    break
                    
            results.append({
                "topic": topic,
                "searches": traffic,
                "country": country_name
            })
            
        return results

    except Exception as e:
        print(f"Error fetching trends for {country_name}: {e}")
        return []

if __name__ == "__main__":
    # Your 10 selected countries + Japan
    countries = {
        "IN": "India", "JP": "Japan", "US": "USA", "GB": "UK", 
        "CA": "Canada", "AU": "Australia", "DE": "Germany", 
        "FR": "France", "BR": "Brazil", "KR": "South Korea", 
        "SG": "Singapore"
    }
    
    # Testing just India and Japan first so we don't flood your terminal
    for code in ["IN", "JP"]:
        name = countries[code]
        trends = get_real_trends(code, name, limit=25)
        
        print(f"\n=== TOP TRENDS IN {name.upper()} ===")
        for i, t in enumerate(trends, 1):
            print(f"{i}. {t['topic']} | Searches: {t['searches']} | Country: {t['country']}")
