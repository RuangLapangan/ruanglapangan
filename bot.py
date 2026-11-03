import os
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import google.generativeai as genai

# Setup Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

RSS_URL = "https://www.cnnindonesia.com/olahraga/sepak-bola/rss"
ARTICLES_FILE = "articles.json"

def get_latest_news():
    req = urllib.request.Request(RSS_URL, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')
        
        news_list = []
        for item in items[:3]:
            title = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            desc = item.find('description').text if item.find('description') is not None else ""
            
            enclosure = item.find('enclosure')
            img_url = enclosure.get('url') if enclosure is not None else "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=700&auto=format&fit=crop&q=80"
            
            news_list.append({"title": title, "link": link, "desc": desc, "img": img_url})
        return news_list
    except Exception as e:
        print(f"Gagal mengambil RSS: {e}")
        return []

def rewrite_with_gemini(news_item):
    prompt = f"""
Kamu adalah jurnalis dan analis sepak bola profesional untuk situs 'RuangLapangan'.
Tulis ulang berita berikut menjadi artikel baru yang orisinal, menarik, dan berbobot (2-3 paragraf).
Hindari kalimat yang sama persis dengan aslinya. Gunakan gaya bahasa ulasan sepak bola yang lugas.

Data Berita:
Judul Asli: {news_item['title']}
Ringkasan: {news_item['desc']}

Format respon WAJIB berupa JSON valid saja tanpa kutip markdown atau blok kode:
{{
  "judul_baru": "Judul baru di sini",
  "isi_artikel": "Paragraf pertama ulasan...\\n\\nParagraf kedua ulasan..."
}}
"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
        data = json.loads(text)
        return data.get("judul_baru", news_item['title']), data.get("isi_artikel", news_item['desc'])
    except Exception as e:
        print(f"Error AI: {e}")
        return news_item['title'], news_item['desc']

def main():
    existing_articles = []
    if os.path.exists(ARTICLES_FILE):
        try:
            with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
                existing_articles = json.load(f)
        except Exception:
            existing_articles = []

    latest = get_latest_news()
    new_entries = []

    for item in latest:
        if any(a.get("source_url") == item['link'] for a in existing_articles):
            continue
        
        print(f"Memproses: {item['title']}")
        new_title, full_content = rewrite_with_gemini(item)
        new_entries.append({
            "id": int(datetime.now().timestamp() * 1000),
            "title": new_title,
            "content": full_content,
            "img": item['img'],
            "date": datetime.now().strftime("%d %b %Y, %H:%M WIB"),
            "source_url": item['link']
        })

    if new_entries:
        merged = (new_entries + existing_articles)[:20]
        with open(ARTICLES_FILE, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print("Selesai menyimpan artikel baru!")
    else:
        print("Tidak ada artikel baru.")

if __name__ == "__main__":
    main()
