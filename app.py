import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime, timedelta

st.set_page_config(page_title='Shtab WB', page_icon='🏢', layout='wide')

GEMINI_KEY = st.secrets.get('GEMINI_API_KEY', '')
WB_TOKEN = st.secrets.get('WB_API_TOKEN', '')

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

st.title('\U0001f3e2 Virtualny ofis WB')
st.markdown('---')

if not GEMINI_KEY or not WB_TOKEN:
    st.error('\u26a0\ufe0f Klyuchi API ne nastroeny')
    st.stop()

def ask_llm(prompt, system_prompt=''):
    try:
        st.info('Otpravka zaprosa k Gemini...')
        full = ''
        if system_prompt:
            full = '[INSTRUKCIYA]: ' + system_prompt + '\n\n'
        full = full + '[ZAPROS]: ' + prompt
        response = model.generate_content(full)
        st.success('Otvet poluchen!')
        return response.text
    except Exception as e:
        return '\u274c Oshibka Gemini: ' + str(e) + '\n\nProverte kluch GEMINI_API_KEY ili smenite model.'

def get_wb_sales(days_back=7):
    date_from = (datetime.now() - timedelta(days_back)).strftime('%Y-%m-%d')
    url = 'https://statistics-api.wildberries.ru/api/v1/supplier/sales'
    try:
        st.info('Podklyuchenie k WB API...')
        r = requests.get(url, headers={'Authorization': WB_TOKEN}, params={'dateFrom': date_from}, timeout=15)
        r.raise_for_status()
        st.success('Dannye WB polucheny!')
        return r.json()
    except requests.exceptions.Timeout:
        return {'error': 'WB API ne otvechaet (timeout).'}
    except requests.exceptions.ConnectionError:
        return {'error': 'Net soedineniya s WB API.'}
    except Exception as e:
        return {'error': str(e)}

def analyze_cfo():
    st.info('Zagruzka dannyh iz WB...')
    sales = get_wb_sales(7)
    
    if isinstance(sales, dict) and 'error' in sales:
        return '\u274c Oshibka WB API: ' + sales['error']
    if not sales:
        return '\U0001f4ca Net dannyh o prodazhah za 7 dney.'
    
    st.info('Analiz dannyh...')
    
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
        top_text = top_text + '\u2022 ' + str(nm) + ' (' + d['brand'][:30] + '): ' + str(int(d['revenue'])) + ' rub, ' + str(d['qty']) + ' sht, vozvratov ' + str(d['returns']) + ' sht\n'
    
    prompt = 'Dannye za 7 dney:\n'
    prompt = prompt + '- Vyruchka: ' + str(int(rev)) + ' rub\n'
    prompt = prompt + '- Prodano: ' + str(qty) + ' sht\n'
    prompt = prompt + '- Vozvratov: ' + str(ret) + ' sht (' + str(round(ret_rate, 1)) + '%)\n\n'
    prompt = prompt + 'Top-5 tovarov:\n' + top_text + '\n'
    prompt = prompt + 'ZADANIE:\n'
    prompt = prompt + '1. Naydi tovary s vozvratami bolshe 20%\n'
    prompt = prompt + '2. Day 5 konkretnyh rekomendaciy po uvelicheniyu pribyli\n'
    prompt = prompt + '3. Rasstav prioriteti: SROCHNO / VAZHNO / PLANOVO'
    
    system = 'Ty CFO magazina na Wildberries. Analiziruy prodazhi, ischi tochki rosta. Otvechay chetko s ciframi na russkom yazyke.'
    return ask_llm(prompt, system)

def analyze_ceo():
    cfo_report = analyze_cfo()
    prompt = 'Otchet CFO:\n' + cfo_report + '\n\nSformiruy plan deystviy na den s prioritetami.'
    system = 'Ty CEO virtualnogo ofisa WB. Sinteziruy informaciyu, rasstavlyay prioriteti, davay chetkiy plan na russkom yazyke.'
    return ask_llm(prompt, system)

st.sidebar.title('\U0001f465 Vyberite specialista')
agent = st.sidebar.radio(
    'K komu obratitsya:',
    ['\U0001f3af CEO (Obschiy shtab)', '\U0001f4b0 CFO (Finansy)', '\U0001f524 SEO (skoro)', '\U0001f4c8 Reklama (skoro)', '\U0001f4e6 Logistika (skoro)']
)

if 'CEO' in agent:
    st.header('\U0001f3af CEO \u2014 Obschiy shtab')
    st.write('Svodka ot vseh specialistov i plan deystviy na den.')
    if st.button('\U0001f4cb Poluchit plan na den', type='primary'):
        with st.spinner('CEO sobiraet otchety...'):
            result = analyze_ceo()
        st.markdown(result)

elif 'CFO' in agent:
    st.header('\U0001f4b0 CFO \u2014 Finansovyy direktor')
    st.write('Analiz P&L, poisk ubytochnyh tovarov i tochek rosta.')
    if st.button('\U0001f4b0 Provesti analiz finansov', type='primary'):
        with st.spinner('CFO zagruzhaet dannye iz WB...'):
            result = analyze_cfo()
        st.markdown(result)

else:
    st.header(agent)
    st.info('\u23f3 Etot agent nahoditsya v razrabotke.')
