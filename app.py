import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime, timedelta

# Настройка страницы
st.set_page_config(page_title="🏢 Штаб WB", page_icon="🏢", layout="wide")

# Настройка Gemini
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash')

# Заголовок
st.title("🏢 Виртуальный офис WB")
st.markdown("---")

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
    date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    url = "https://statistics-api.wildberries.ru/api/v1/supplier/sales"
    try:
        r = requests.get(url, headers={"Authorization": st.secrets["WB_API_TOKEN"]}, params={"dateFrom": date_from}, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# CFO - анализ финансов
def analyze_cfo():
    sales = get_wb_sales(7)
    if isinstance(sales, dict) and "error" in sales:
        return f"❌ Ошибка WB API: {sales['error']}\n\nПроверьте токен в настройках Streamlit Secrets."
    if not sales:
        return "📊 Нет данных о продажах за последние 7 дней."
    
    rev = sum(i.get("totalPrice", 0) / 100 for i in sales if i.get("saleStatus") == 1)
    qty = sum(1 for i in sales if i.get("saleStatus") == 1)
    ret = sum(1 for i in sales if i.get("saleStatus") == 2)
    ret_rate = (ret / max(qty, 1)) * 100
    
    # Топ товаров
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
1. Найди товары с возвратами >20%
2. Дай 5 конкретных рекомендаций по увеличению прибыли
3. Расставь приоритеты: 🔴 СРОЧНО / 🟡 ВАЖНО / 🟢 ПЛАНОВО"""
    
    return ask_llm(prompt, "Ты CFO магазина на Wildberries. Анализируй продажи, ищи точки роста. Отвечай чётко с цифрами.")

# CEO - общий план
def analyze_ceo():
    cfo_report = analyze_cfo()
    prompt = f"Отчёт CFO:\n{cfo_report}\n\nСформируй план действий на день с приоритетами и ожидаемым эффектом."
    return ask_llm(prompt, "Ты CEO виртуального офиса WB. Синтезируй информацию, расставляй приоритеты 🔴🟡🟢, давай чёткий план.")

# Боковая панель
st.sidebar.title("👥 Выберите специалиста")
agent = st.sidebar.radio(
    "К кому обратиться:",
    ["🎯 CEO (Общий штаб)", "💰 CFO (Финансы)", "🔤 SEO (скоро)", "📈 Реклама (скоро)", "📦 Логистика (скоро)"]
)

# Главная область
if "CEO" in agent:
    st.header("🎯 CEO — Общий штаб")
    st.write("Сводка от всех специалистов и план действий на день.")
    if st.button("📋 Получить план на день", type="primary"):
        with st.spinner("CEO собирает отчёты и думает..."):
            result = analyze_ceo()
        st.markdown(result)

elif "CFO" in agent:
    st.header("💰 CFO — Финансовый директор")
    st.write("Анализ P&L, поиск убыточных товаров и точек роста.")
    if st.button("💰 Провести анализ финансов", type="primary"):
        with st.spinner("CFO загружает данные из WB и анализирует..."):
            result = analyze_cfo()
        st.markdown(result)

else:
    st.header(agent)
    st.info("⏳ Этот агент находится в разработке и будет добавлен на следующем этапе.")
