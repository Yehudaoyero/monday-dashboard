# Customer Support Dashboard — Monday CRM

דשבורד בזמן אמת לניהול תקלות, מחובר ישירות ל-Monday CRM.

---

## הוראות התקנה והפעלה

### שלב 1 — GitHub

1. היכנס ל-[github.com](https://github.com) וצור חשבון חינמי
2. לחץ **New repository**
3. שם: `monday-dashboard` — בחר **Private**
4. העלה את 3 הקבצים:
   - `app.py`
   - `requirements.txt`
   - תיקיית `.streamlit/secrets.toml`

### שלב 2 — הוסף את ה-API Token

פתח את הקובץ `.streamlit/secrets.toml` והחלף:
```
MONDAY_API_TOKEN = "הכנס כאן את ה-API Token שלך"
```
בטוקן האמיתי שלך.

> ⚠️ ודא שה-repository הוא **Private** כדי שה-Token לא יהיה חשוף

### שלב 3 — Streamlit Cloud

1. היכנס ל-[share.streamlit.io](https://share.streamlit.io)
2. התחבר עם חשבון GitHub שלך
3. לחץ **New app**
4. בחר את ה-repository `monday-dashboard`
5. Main file: `app.py`
6. לחץ **Deploy**

### שלב 4 — שיתוף עם המנהל

אחרי ה-Deploy תקבל קישור בצורה:
```
https://your-name-monday-dashboard.streamlit.app
```
שלח את הקישור למנהל — זהו! 🎉

---

## עדכון אוטומטי

הדשבורד מתרענן אוטומטית **כל 60 שניות** ישירות מ-Monday.
אין צורך לייצא קבצים.

## מבנה הפרויקט

```
monday_dashboard/
├── app.py                  ← הקוד הראשי
├── requirements.txt        ← ספריות Python
└── .streamlit/
    └── secrets.toml        ← API Token (לא לשתף!)
```
