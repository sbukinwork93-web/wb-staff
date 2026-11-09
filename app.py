import streamlit as st
import requests
from google import genai
from datetime import datetime, timedelta

st.set_page_config(page_title='\u0428\u0442\u0430\u0431 WB', page_icon='\U0001f3e2', layout='wide')

GEMINI_KEY = st.secrets.get('GEMINI_API_KEY', '')
WB_TOKEN = st.secrets.get('WB_API_TOKEN', '')

if GEMINI_KEY:
    client = genai.Client(api_key=GEMINI_KEY)
else:
    client = None

st.title('\U0001f3e2 \u0412\u0438\u0440\u0442\u0443\u0430\u043b\u044c\u043d\u044b\u0439 \u043e\u0444\u0438\u0441 WB')
st.markdown('---')

if not GEMINI_KEY or not WB_TOKEN:
    st.error('\u26a0\ufe0f \u041a\u043b\u044e\u0447\u0438 API \u043d\u0435 \u043d\u0430\u0441\u0442\u0440\u043e\u0435\u043d\u044b. \u0414\u043e\u0431\u0430\u0432\u044c\u0442\u0435 GEMINI_API_KEY \u0438 WB_API_TOKEN \u0432 Secrets \u043d\u0430 Streamlit Cloud.')
    st.stop()

def ask_llm(prompt, system_prompt=''):
    try:
        st.info('\u041e\u0442\u043f\u0440\u0430\u0432\u043a\u0430 \u0437\u0430\u043f\u0440\u043e\u0441\u0430 \u043a Gemini...')
        contents = []
        if system_prompt:
            contents.append({'role': 'user', 'parts': [{'text': '[\u0418\u041d\u0421\u0422\u0420\u0423\u041a\u0426\u0418\u042f]: ' + system_prompt}]})
        contents.append({'role': 'user', 'parts': [{'text': '[\u0417\u0410\u041f\u0420\u041e\u0421]: ' + prompt}]})
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=contents
        )
        st.success('\u041e\u0442\u0432\u0435\u0442 \u043f\u043e\u043b\u0443\u0447\u0435\u043d!')
        return response.text
    except Exception as e:
        return '\u274c \u041e\u0448\u0438\u0431\u043a\u0430 Gemini: ' + str(e)

def get_wb_sales(days_back=7):
    date_from = (datetime.now() - timedelta(days_back)).strftime('%Y-%m-%d')
    url = 'https://statistics-api.wildberries.ru/api/v1/supplier/sales'
    try:
        st.info('\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435 \u043a WB API...')
        r = requests.get(url, headers={'Authorization': WB_TOKEN}, params={'dateFrom': date_from}, timeout=30)
        r.raise_for_status()
        st.success('\u0414\u0430\u043d\u043d\u044b\u0435 WB \u043f\u043e\u043b\u0443\u0447\u0435\u043d\u044b!')
        return r.json()
    except requests.exceptions.Timeout:
        return {'error': 'WB API \u043d\u0435 \u043e\u0442\u0432\u0435\u0447\u0430\u0435\u0442 (\u0442\u0430\u0439\u043c\u0430\u0443\u0442).'}
    except requests.exceptions.ConnectionError:
        return {'error': '\u041d\u0435\u0442 \u0441\u043e\u0435\u0434\u0438\u043d\u0435\u043d\u0438\u044f \u0441 WB API.'}
    except Exception as e:
        return {'error': str(e)}

def analyze_cfo():
    st.info('\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u0434\u0430\u043d\u043d\u044b\u0445 \u0438\u0437 WB...')
    sales = get_wb_sales(7)
    
    if isinstance(sales, dict) and 'error' in sales:
        return '\u274c \u041e\u0448\u0438\u0431\u043a\u0430 WB API: ' + sales['error']
    if not sales:
        return '\U0001f4ca \u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445 \u043e \u043f\u0440\u043e\u0434\u0430\u0436\u0430\u0445 \u0437\u0430 7 \u0434\u043d\u0435\u0439.'
    
    st.info('\u0410\u043d\u0430\u043b\u0438\u0437 \u0434\u0430\u043d\u043d\u044b\u0445...')
    
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
    for nm, d in top5:
        top_text = top_text + '\u2022 ' + str(nm) + ' (' + d['brand'][:30] + '): ' + str(int(d['revenue'])) + ' \u0440\u0443\u0431, ' + str(d['qty']) + ' \u0448\u0442, \u0432\u043e\u0437\u0432\u0440\u0430\u0442\u043e\u0432 ' + str(d['returns']) + ' \u0448\u0442\n'
    
    prompt = '\u0414\u0430\u043d\u043d\u044b\u0435 \u0437\u0430 7 \u0434\u043d\u0435\u0439:\n'
    prompt = prompt + '- \u0412\u044b\u0440\u0443\u0447\u043a\u0430: ' + str(int(rev)) + ' \u0440\u0443\u0431\n'
    prompt = prompt + '- \u041f\u0440\u043e\u0434\u0430\u043d\u043e: ' + str(qty) + ' \u0448\u0442\n'
    prompt = prompt + '- \u0412\u043e\u0437\u0432\u0440\u0430\u0442\u043e\u0432: ' + str(ret) + ' \u0448\u0442 (' + str(round(ret_rate, 1)) + '%)\n\n'
    prompt = prompt + '\u0422\u043e\u043f-5 \u0442\u043e\u0432\u0430\u0440\u043e\u0432:\n' + top_text + '\n'
    prompt = prompt + '\u0417\u0410\u0414\u0410\u041d\u0418\u0415:\n'
    prompt = prompt + '1. \u041d\u0430\u0439\u0434\u0438 \u0442\u043e\u0432\u0430\u0440\u044b \u0441 \u0432\u043e\u0437\u0432\u0440\u0430\u0442\u0430\u043c\u0438 \u0431\u043e\u043b\u044c\u0448\u0435 20%\n'
    prompt = prompt + '2. \u0414\u0430\u0439 5 \u043a\u043e\u043d\u043a\u0440\u0435\u0442\u043d\u044b\u0445 \u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0430\u0446\u0438\u0439 \u043f\u043e \u0443\u0432\u0435\u043b\u0438\u0447\u0435\u043d\u0438\u044e \u043f\u0440\u0438\u0431\u044b\u043b\u0438\n'
    prompt = prompt + '
