import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime, timedelta

st.set_page_config(page_title='Shtab WB', page_icon='🏢', layout='wide')

GEMINI_KEY = st.secrets.get('GEMINI_API_KEY', '')
WB_TOKEN = st.secrets.get('WB_API_TOKEN', '')

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-3.8-flash')
else:
    model = None

st.title('🏢 Virtualny ofis WB')
st.markdown('---')

if not GEMINI_KEY or not WB_TOKEN:
    st.error('Klyuchi API ne nastroeny')
    st.stop()

def ask_llm(prompt, system_prompt=''):
    try:
        full = ''
        if system_prompt:
            full = '[INSTRUKCIYA]: ' + system_prompt + '\n\n'
        full = full + '[ZAPROS]: ' + prompt
        response = model.generate_content(full)
        return response.text
    except Exception as e:
        return 'Oshibka II: ' + str(e)

def get_wb_sales(days_back=7):
    date_from = (datetime.now() - timedelta(days_back)).strftime('%Y-%m-%d')
    url = 'https://statistics-api.wildberries.ru/api/v1/supplier/sales'
    try:
        r = requests.get(url, headers={'Authorization': WB_TOKEN}, params={'dateFrom': date_from}, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {'error': str(e)}

def analyze_cfo():
    sales = get_wb_sales(7)
    if isinstance(sales, dict) and 'error' in sales:
        return 'Oshibka WB API: ' + sales['error']
    if not sales:
        return 'Net dannyh o prodazhah za 7 dney.'
    
    rev = 0
    qty = 0
    ret = 0
    products = {}
    
    for item in sales:
        nm = item.get('nmId')
        status = item.get('saleStatus')
        price = item.get('totalPrice', 0) / 100
        brand = item.get('brandName', '')
        
        if nm not in products:
            products[nm] = {'brand': brand, 'revenue': 0, 'qty': 0, 'returns': 0}
        
        if status == 1:
            products[nm]['revenue'] += price
            products[nm]['qty'] += 1
            rev += price
            qty += 1
        elif status == 2:
            products[nm]['returns'] += 1
            ret += 1
    
    ret_rate = (ret / max(qty, 1)) * 100
    
    top5 = sorted(products.items(), key=lambda x: x[1]['revenue'], reverse=True)[:5]
    top_text = ''
    for nm, d
