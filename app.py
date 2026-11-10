import streamlit as st
import requests
from google import genai
from datetime import datetime, timedelta
import time

st.set_page_config(page_title='Штаб WB', page_icon='🏢', layout='wide')

GEMINI_KEY = st.secrets.get('GEMINI_API_KEY', '')
WB_TOKEN = st.secrets.get('WB_API_TOKEN', '')

if GEMINI_KEY:
    client = genai.Client(api_key=GEMINI_KEY)
else:
    client = None

st.title('🏢 Виртуальный офис WB')
st.markdown('---')

if not GEMINI_KEY or not WB_TOKEN:
    st.error('⚠️ Ключи API не настроены.')
    st.stop()

def ask_llm(prompt, system_prompt=''):
    models_to_try = ['gemini-1.5-flash', 'gemini-pro', 'gemini-3.8-flash']
    
    for model_name in models_to_try:
        try:
            st.info('Отправка запроса к Gemini (модель: ' + model_name + ')...')
            contents = []
            if system_prompt:
                contents.append({'role': 'user', 'parts': [{'text': '[ИНСТРУКЦИЯ]: ' + system_prompt}]})
            contents.append({'role': 'user', 'parts': [{'text': '[ЗАПРОС]: ' + prompt}]})
            response = client.models.generate_content(
                model=model_name,
                contents=contents
            )
            st.success('Ответ получен! (модель: ' + model_name + ')')
            return response.text
        except Exception as e:
            error_str = str(e)
            if '404' in error_str or 'NOT_FOUND' in error_str:
                st.warning('Модель ' + model_name + ' недоступна, пробуем следующую...')
                continue
            elif '503' in error_str:
                st.warning('Gemini перегружен, ждём 5 секунд...')
                time.sleep(5)
                continue
            else:
                return '❌ Ошибка Gemini: ' + error_str
    
    return '❌ Все модели Gemini недоступны. Проверьте ключ GEMINI_API_KEY.'

def get_wb_sales(days_back=7):
    date_from = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    url = 'https://statistics-api.wildberries.ru/api/v1/supplier/sales'
    try:
        st.info('Подключение к WB API...')
        r = requests.get(url, headers={'Authorization': WB_TOKEN}, params={'dateFrom': date_from}, timeout=30)
        r.raise_for_status()
        data = r.json()
        st.success('Данные WB получены! Записей: ' + str(len(data)))
        return data
    except requests.exceptions.Timeout:
        return {'error': 'WB API не отвечает (таймаут).'}
    except requests.exceptions.ConnectionError:
        return {'error': 'Нет соединения с WB API.'}
    except Exception as e:
        return {'error': str(e)}

def analyze_cfo():
    st.info('Загрузка данных из WB...')
    sales = get_wb_sales(7)
    
    if isinstance(sales, dict) and 'error' in sales:
        return '❌ Ошибка WB API: ' + sales['error']
    
    if not sales:
        return '📊 Нет данных о продажах за 7 дней.'
    
    st.info('Анализ данных...')
    
    rev = 0
    qty = 0
    ret = 0
    products = {}
    
    for item in sales:
        nm = item.get('nmId')
        is_realization = item.get('isRealization', False)
        is_supply = item.get('isSupply', False)
        price = item.get('totalPrice', 0) / 100
        brand = item.get('brand', '')
        subject = item.get('subject', '')
        
        if nm not in products:
            products[nm] = {'brand': brand, 'subject': subject, 'revenue': 0, 'qty': 0, 'returns': 0}
        
        if is_realization and not is_supply:
            products[nm]['revenue'] += price
            products[nm]['qty'] += 1
            rev += price
            qty += 1
        elif is_supply:
            products[nm]['returns'] += 1
            ret += 1
    
    ret_rate = (ret / max(qty, 1)) * 100
    
    st.info('Посчитано: выручка ' + str(int(rev)) + ' руб, продано ' + str(qty) + ' шт')
    
    top5 = sorted(products.items(), key=lambda x: x[1]['revenue'], reverse=True)[:5]
    top_text = ''
    for nm, d in top5:
        top_text = top_text + '• ' + str(nm) + ' (' + d['brand'][:30] + ' - ' + d['subject'][:20] + '): ' + str(int(d['revenue'])) + ' руб, ' + str(d['qty']) + ' шт, возвратов ' + str(d['returns']) + ' шт\n'
    
    prompt = 'Данные за 7 дней:\n'
    prompt = prompt + '- Выручка: ' + str(int(rev)) + ' руб\n'
    prompt = prompt + '- Продано: ' + str(qty) + ' шт\n'
    prompt = prompt + '- Возвратов: ' +
