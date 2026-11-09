import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime, timedelta

st.set_page_config(page_title="Штаб WB", page_icon="🏢", layout="wide")

GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "")
WB_TOKEN = st.secrets.get("WB_API_TOKEN", "")

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-3.8-flash')
else:
    model = None

st.title("🏢 Виртуальный офис WB")
st.markdown("---")

if not GEMINI_KEY or not WB_TOKEN:
    st.error("⚠️ Ключи API не настроены. Добавьте GEMINI_API_KEY и WB_API_TOKEN в Secrets на Streamlit Cloud.")
    st.stop()

def ask_llm(prompt, system_prompt=""):
    try:
        full = ""
        if system_prompt:
            full = "[ИНСТРУКЦИЯ]: " + system_prompt + "\n\n"
        full = full + "[ЗАПРОС]: " + prompt
        response = model.generate_content(full)
        return response.text
    except Exception as e:
        return "❌ Ошибка ИИ: " + str(e)

def get_wb_sales(days_back=7):
    date_from = (datetime.now() - timedelta(days_back)).strftime("%Y-%m-%d")
    url = "https://statistics-api.wildberries.ru/api/v1/supplier/sales"
    try:
        r = requests.get(url, headers={"Authorization": WB_TOKEN}, params={"dateFrom": date_from}, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def analyze_cfo():
    sales = get_wb_sales(7)
    if isinstance(sales, dict) and "error" in sales:
        return "❌ Ошибка WB API: " + sales['error'] + "\n\nПроверьте токен WB_API_TOKEN."
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
    top_lines = []
    for nm, d in top5:
        line = "• " + str(nm) + " (" + d['brand'][:30] + "): " + f"{d['revenue']:,.0f}" + "₽, " + str(d['qty']) + "шт, возвратов " + str(d['returns']) + "шт"
        top_lines.append(line)
    top_text = "\n".join(top_lines)
    
    prompt = "Данные за 7 дней:\n"
    prompt = prompt + "- Выручка: " + f"{rev:,.0f}" + "₽\n"
    prompt = prompt + "- Продано: " + str(qty) + "шт\n"
    prompt = prompt + "- Возвратов:
