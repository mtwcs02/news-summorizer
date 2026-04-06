import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 앱 화면 꾸미기
st.set_page_config(page_title="나만의 뉴스 비서", page_icon="🤖")
st.title("🤖 나만의 AI 뉴스 비서")
st.write("오늘의 주요 소식을 AI가 깔끔하게 3줄 요약해 드립니다.")

# 2. 🔐 비밀 금고(Secrets)에서 API 키 가져오기
try:
    # 아까 Secrets에 저장한 'GEMINI_API_KEY'라는 이름을 사용합니다.
    GOOGLE_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    st.error("앗! 스트림릿 Secrets 설정에 API 키가 없거나 이름이 틀렸어요. 확인해 주세요!")
    st.stop()

# 3. 최신 AI 모델 자동 연결
@st.cache_resource
def load_model():
    # 사용 가능한 모델 중 가장 최신 모델을 자동으로 선택합니다.
    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    return genai.GenerativeModel(model_name=models[0])

model = load_model()

# 4. 사용자 입력창 (기본값은 SGC에너지로 설정해둘게요!)
keyword = st.text_input("궁금한 종목이나 키워드를 입력하세요", value="SGC에너지")

# 5. 실행 버튼 클릭 시 작동
if st.button("뉴스 요약 시작! 🔥"):
    with st.spinner('뉴스를 읽고 분석하는 중입니다... 잠시만 기다려 주세요!'):
        # 구글 뉴스에서 정보 가져오기
        url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
        response = requests.get(url)
        # lxml 도구를 사용하여 뉴스 데이터를 해석합니다.
        soup = BeautifulSoup(response.content, features="xml")
        items = soup.find_all('item')
        
        if items:
            # 상위 5개 뉴스 제목 합치기
            all_titles = "\n".join([f"- {item.title.text}" for item in items[:5]])
            
            # AI에게 요약 부탁하기
            prompt = f"다음 뉴스 제목들을 읽고 핵심 소식을 한글로 3줄 요약해줘:\n{all_titles}"
            result = model.generate_content(prompt)
            
            # 결과 화면에 뿌려주기
            st.success(f"✨ '{keyword}' 관련 주요 소식 요약 완료!")
            st.info(result.text)
            
            # 원문 뉴스 링크도 살짝 보여주기 (옵션)
            with st.expander("원본 뉴스 제목 보기"):
                st.write(all_titles)
        else:
            st.warning(f"'{keyword}'와 관련된 최신 뉴스를 찾을 수 없습니다. 단어를 확인해 보세요!")
