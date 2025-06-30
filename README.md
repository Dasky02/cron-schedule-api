k# Cron Schedule API 🕒

REST API, které:
- ✅ **/validate** — zkontroluje syntaxi CRON výrazu  
- ✅ **/next** — vrátí příští termíny spuštění  
- ✅ **/previous** — vrátí minulé termíny spuštění  

👉 **Živé demo:**  https://cron-schedule-api.onrender.com/docs

---

## Rychlý lokální start

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
