import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime, timedelta

# Настройка страницы
st.set_page_config(page_title="🏢 Штаб WB", page_icon="🏢", layout="wide")

# Получаем ключи из Streamlit Secrets
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")
WB_TOKEN = st.secrets.get("WB_API_TOKEN", "")

# Настройка Gemini (актуальная модель)
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-3.8-flash')
else:
    model = None

# Заголовок
st.title("🏢 Виртуальный офис WB")
st.markdown("---")

# Проверка ключей
if not GEMINI_KEY or not WB_TOKEN:
    st.error("⚠️ Ключи API не настроены. Добавьте GEMINI_API_KEY и WB_API_TOKEN в Secrets на Streamlit Cloud.")
    st.stop()

# Функция запроса к ИИ
def ask_llm(prompt, system_prompt=""):
    try:
        full = (f"[ИНСТРУКЦИЯ]: {system_prompt}\n\n" if system_prompt else "") + f"[ЗАПРОС]: {prompt}"
        response = model.generate_content(full)
        return response.text
    except Exception as e:
        return f"❌ Ошибка ИИ: {e}"

# Функция получения данных с WB
def get_wb_sales(days_back=7):
    date_from = (datetime.now() - timedelta(days_back)).strftime("%Y-%m-%d")
    url = "https://statistics-api.wildberries.ru/api/v1/supplier/sales"
    try:
        r = requests.get(url, headers={"Authorization": WB_TOKEN}, params={"dateFrom": date_from}, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# CFO - анализ финансов
def analyze_cfo():
    sales = get_wb_sales(7)
    if isinstance(sales, dict) and "error" in sales:
        return f"❌ Ошибка WB API: {sales['error']}\n\nПроверьте токен WB_API_TOKEN."
    if not sales:
        return "📊 Нет данных о продажах за последние 7 дней."
    
    rev = sum(i.get("totalPrice", 0) / 100 for i in sales if i.get("saleStatus") == 1)
    qty = sum(1 for i in sales if i.get("saleStatus") == 1)
    ret = sum(1 for i in sales if i.get("saleStatus") == 2)
    ret_rate = (ret / max(qty, 1)) * 100
    
    products = {}
    for item in sales:
        nm = item.get("nmId")
        if nm not in products:
            products[nm] = {"brand": item.get("brandName", ""), "revenue": 0, "qty": 0, "returns": 0}
        if item.get("saleStatus") == 1:
            products[nm]["revenue"] += item.get("totalPrice", 0) / 100
            products[nm]["qty"] += 1
        elif item.get("saleStatus") == 2:
            products[nm]["returns"] += 1
    
    top5 = sorted(products.items(), key=lambda x: x[1]["revenue"], reverse=True)[:5]
    top_text = "\n".join([f"• {nm} ({d['brand'][:30]}): {d['revenue']:,.0f}₽, {d['qty']}шт, возвратов {d['returns']}шт" for nm, d in top5])
    
    prompt = f"""Данные за 7 дней:
- Выручка: {rev:,.0f}₽
- Продано: {qty}шт
- Возвратов: {ret}шт ({ret_rate:.1f}%)

Топ-5 товаров:
{top_text}

ЗАДАНИЕ:
