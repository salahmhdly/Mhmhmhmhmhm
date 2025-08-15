import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
import re # سنحتاج هذه المكتبة لإزالة التشكيل من أجل بحث أفضل

# --- 1. إعداد التطبيق وجلب البيانات عند بدء التشغيل ---
app = Flask(__name__)
CORS(app)

QURAN_DATA = []

def fetch_quran_from_api():
    """
    تجلب هذه الدالة بيانات القرآن الكريم كاملة من واجهة برمجية عامة عند بدء تشغيل الخادم.
    """
    global QURAN_DATA
    try:
        url = "http://api.alquran.cloud/v1/quran/quran-uthmani"
        print("...جاري جلب بيانات القرآن الكريم من الإنترنت...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data['code'] == 200 and 'data' in data and 'surahs' in data['data']:
            QURAN_DATA = data['data']['surahs']
            print(f"تم تحميل {len(QURAN_DATA)} سورة بنجاح من الإنترنت.")
        else:
            print("فشل تحميل البيانات: لم يتم العثور على البنية المتوقعة.")
    except requests.exceptions.RequestException as e:
        print(f"حدث خطأ فادح أثناء الاتصال بالـ API: {e}")

def remove_tashkeel(text):
    """
    دالة لإزالة علامات التشكيل من النص العربي.
    """
    return re.sub(r'[\u064B-\u0652]', '', text)

# --- 2. الواجهات البرمجية (API Endpoints) ---

@app.route("/api/suras")
def get_surahs():
    """
    واجهة برمجية لجلب قائمة السور مع معلومات أساسية.
    """
    if not QURAN_DATA:
        return jsonify({"success": False, "message": "البيانات غير متاحة حاليًا."}), 503

    surahs_list = []
    for surah in QURAN_DATA:
        # العثور على رقم صفحة بداية السورة
        start_page = surah.get("ayahs", [{}])[0].get("page", 1)
        surahs_list.append({
            "number": surah.get("number"),
            "name": surah.get("name"),
            "revelation_place": surah.get("revelationType").lower(), # mecca or medina
            "verses_count": surah.get("numberOfAyahs"),
            "page": start_page
        })
    return jsonify(surahs_list) # الواجهة الجديدة تتوقع مصفوفة مباشرة

@app.route("/api/search")
def search_quran():
    """
    واجهة برمجية للبحث في نصوص القرآن.
    """
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([]) # إرجاع قائمة فارغة إذا كان البحث قصيرًا

    if not QURAN_DATA:
        return jsonify({"success": False, "message": "البيانات غير متاحة حاليًا."}), 503

    search_results = []
    normalized_query = remove_tashkeel(query)

    for surah in QURAN_DATA:
        for verse in surah.get("ayahs", []):
            normalized_verse_text = remove_tashkeel(verse.get("text", ""))
            if normalized_query in normalized_verse_text:
                search_results.append({
                    "text": verse.get("text"),
                    "sura_name": surah.get("name"),
                    "verse_number": verse.get("numberInSurah"),
                    "page": verse.get("page")
                })
                if len(search_results) >= 20: # تحديد عدد النتائج بـ 20 كحد أقصى للأداء
                    break
        if len(search_results) >= 20:
            break

    return jsonify(search_results)

@app.route("/api/page/content/<int:page_number>")
def get_page_content(page_number):
    """
    واجهة برمجية لجلب الآيات النصية لصفحة معينة.
    """
    if not QURAN_DATA:
        return jsonify({"success": False, "message": "البيانات غير متاحة حاليًا."}), 503

    verses_on_page = []
    for surah in QURAN_DATA:
        for verse in surah.get("ayahs", []):
            if verse.get("page") == page_number:
                verses_on_page.append({
                    "text": verse.get("text"),
                    "verse_number": verse.get("numberInSurah")
                })

    return jsonify(verses_on_page)

# --- 3. تشغيل الخادم ---
if __name__ == "__main__":
    fetch_quran_from_api()
    if QURAN_DATA:
        app.run(host='0.0.0.0', port=5000)
    else:
        print("فشل تشغيل الخادم لأنه لم يتمكن من تحميل بيانات القرآن.")
