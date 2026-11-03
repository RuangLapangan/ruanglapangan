import os
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from google import genai

# Inisialisasi Gemini Client
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

RSS_URL = "https://www.cnnindonesia.com/olahraga/sepak-bola/rss"
ARTICLES_FILE = "articles.json"

def get_latest_news():
    req = urllib.request.Request(RSS_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        xml_data = response.read()
    
    root = ET.fromstring(xml_data)
    items = root.findall('.//item')
    
    news_list = []
    for item in items[:3]:  # Ambil 3 berita teratas
        title = item.find('title').text if item.find('title') is not None else ""
        link = item.find('link').text if item.find('link') is not None else ""
        desc = item.find('description').text if item.find('description') is not None else ""
        
        # Ekstrak thumbnail
        enclosure = item.find('enclosure')
        img_url = enclosure.get('url') if enclosure is not None else "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=700&auto=format&fit=crop&q=80"
        
        news_list.append({"title": title, "link": link, "desc": desc, "img": img_url})
    return news_list

def rewrite_with_gemini(news_item):
    prompt = f"""
Kamu adalah jurnalis dan analis sepak bola profesional untuk portal media 'RuangLapangan'.
Tulis ulang berita berikut menjadi artikel baru yang orisinal, menarik, dan informatif (2-3 paragraf).
Gunakan bahasa Indonesia santai namun analitis. 
Jangan plagiat kalimat aslinya. Buat judul baru yang menarik (click-worthy tapi bukan hoax).

Data Berita:
Judul Asli: {news_item['title']}
Cuplikan Isi: {news_item['desc']}

Format Jawaban WAJIB JSON persis seperti ini:
{{
  "judul_baru": "Judul artikel baru di sini",
  "isi_artikel": "Paragraf 1...\\n\\nParagraf 2...\\n\\nParagraf 3..."
}}
Kembalikan HANYA format JSON valid tanpa format markdown ```json.
"""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        text_resp = response.text.strip()
        if text_resp.startswith("```json"):
            text_resp = text_resp[7:-3].strip()
        elif text_resp.startswith("```"):
            text_resp = text_resp[3:-3].strip()
            
        data = json.loads(text_resp)
        return data["judul_baru"], data["isi_artikel"]
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

    latest_news = get_latest_news()
    new_entries = []

    for item in latest_news:
        # Cek apakah berita sudah pernah dibuat (berdasarkan sumber aslinya)
        if any(a.get("source_url") == item['link'] for a in existing_articles):
            continue
        
        print(f"Sedang menulis ulang: {item['title']}...")
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
        # Gabungkan artikel baru di urutan paling atas, simpan maksimal 20 artikel terakhir
        updated_list = (new_entries + existing_articles)[:20]
        with open(ARTICLES_FILE, "w", encoding="utf-8") as f:
            json.dump(updated_list, f, ensure_ascii=False, indent=2)
        print(f"Berhasil menambahkan {len(new_entries)} artikel baru!")
    else:
        print("Tidak ada berita baru yang perlu ditulis.")

if __name__ == "__main__":
    main()
