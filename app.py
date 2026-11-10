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
    max_retries = 3
    for attempt in range(max_retries):
        try:
            st.info('Отправка запроса к Gemini...')
            contents = []
            if system_prompt:
                contents.append({'role': 'user', 'parts': [{'text': '[ИНСТРУКЦИЯ]: ' + system_prompt}]})
            contents.append({'role': 'user', 'parts': [{'text': '[ЗАПРОС]: ' + prompt}]})
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents
            )
            st.success('Ответ получен!')
            return response.text
        except Exception as e:
            error_str = str(e)
            if '503' in error_str and attempt < max_retries - 1:
                st.warning('Gemini перегружен, повторная попытка через 5 секунд...')
                time.sleep(5)
            else:
                return '❌ Ошибка Gemini: ' + error_str
    return '❌ Gemini недоступен после 3 попыток.'

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
    prompt = prompt + '- Возвратов: ' + str(ret) + ' шт (' + str(round(ret_rate, 1)) + '%)\n\n'
    prompt = prompt + 'Топ-5 товаров:\n' + top_text + '\n'
    prompt = prompt + 'ЗАДАНИЕ:\n'
    prompt = prompt + '1. Найди товары с возвратами больше 20%\n'
    prompt = prompt + '2. Дай 5 конкретных рекомендаций по увеличению прибыли\n'
    prompt = prompt + '3. Расставь приоритеты: 🔴 СРОЧНО / 🟡 ВАЖНО / 🟢 ПЛАНОВО'
    
    system = 'Ты CFO магазина на Wildberries. Анализируй продажи, ищи точки роста. Отвечай чётко с цифрами на русском языке.'
    return ask_llm(prompt, system)

st.sidebar.title('👥 Выберите специалиста')
agent = st.sidebar.radio(
    'К кому обратиться:',
    ['🎯 CEO (Общий штаб)', '💰 CFO (Финансы)', '🔤 SEO (скоро)', '📈 Реклама (скоро)', '📦 Логистика (скоро)']
)

if 'CFO' in agent:
    st.header('💰 CFO — Финансовый директор')
    st.write('Анализ P&L, поиск убыточных товаров и точек роста.')
    if st.button('💰 Провести анализ финансов', type='primary'):
        with st.spinner('CFO загружает данные из WB...'):
            result = analyze_cfo()
        st.markdown(result)

elif 'CEO' in agent:
    st.header('🎯 CEO — Общий штаб')
    st.info('CEO будет добавлен после настройки CFO.')

else:
    st.header(agent)
    st.info('⏳ Этот агент находится в разработке.')
