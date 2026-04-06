import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 앱 화면 설정
st.set_page_config(page_title="나만의 뉴스 비서", page_icon="🤖")
st.title("🤖 나만의 AI 뉴스 비서")
st.write("오늘의 주요 소식을 AI가 깔끔하게 3줄 요약해 드립니다.")

# 2. 🔐 비밀 금고(Secrets)에서 API 키 가져오기
try:
    GOOGLE_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
except:
    st.error("스트림릿 Secrets에 API 키를 등록해 주세요!")
    st.stop()

# 3. 🛠️ [중요] 최신 모델을 자동으로 찾아내는 기능
@st.cache_resource
def get_working_model():
    # 사용 가능한 모델 목록을 가져옵니다.
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    # 1순위: gemini-1.5-flash / 2순위: gemini-pro / 3순위: 목록의 첫 번째 모델
    if 'models/gemini-1.5-flash' in available_models:
        model_name = 'models/gemini-1.5-flash'
    elif 'models/gemini-pro' in available_models:
        model_name = 'models/gemini-pro'
    else:
        model_name = available_models[0]
    
    return genai.GenerativeModel(model_name)

try:
    model = get_working_model()
except Exception as e:
    st.error(f"AI 모델을 불러오는 데 실패했습니다: {e}")
    st.stop()

# 4. 검색어 입력창
keyword = st.text_input("궁금한 종목이나 키워드를 입력하세요", value="SGC에너지")

# 5. 실행 버튼 클릭 시 작동
if st.button("뉴스 요약 시작! 🔥"):
    with st.spinner('뉴스를 분석 중입니다...'):
        try:
            # 구글 뉴스 가져오기
            url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
            response = requests.get(url)
            soup = BeautifulSoup(response.content, features="xml")
            items = soup.find_all('item')
            
            if items:
                all_titles = "\n".join([f"- {item.title.text}" for item in items[:5]])
                prompt = f"다음 뉴스 제목들을 읽고 핵심 소식을 한글로 3줄 요약해줘:\n{all_titles}"
                
                # AI 실행
                result = model.generate_content(prompt)
                
                st.success(f"✨ '{keyword}' 뉴스 요약 완료!")
                st.info(result.text)
            else:
                st.warning("관련 뉴스를 찾지 못했습니다.")
        except Exception as e:
            st.error(f"작동 중 오류가 발생했습니다: {e}")
