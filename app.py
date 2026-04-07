import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime

# 1. 앱 화면 설정
st.set_page_config(page_title="나만의 스마트 뉴스 비서", page_icon="📈")
st.title("📈 AI 맞춤 뉴스 브리핑")
st.write("카테고리를 누르거나 키워드를 직접 입력해 보세요.")

# 2. 🔐 비밀 금고(Secrets) 설정
try:
    GOOGLE_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
except:
    st.error("스트림릿 Secrets에 API 키를 등록해 주세요!")
    st.stop()

# 3. AI 모델 로드
@st.cache_resource
def get_working_model():
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
    return genai.GenerativeModel(model_name)

model = get_working_model()

# --- 4. 메뉴 구성 ---
st.markdown("### 📍 빠른 카테고리")
categories = ["오늘의 주요 뉴스", "정치", "경제", "사회"]
cols1 = st.columns(len(categories))
selected_keyword = ""

for i, category in enumerate(categories):
    if cols1[i].button(category, use_container_width=True):
        selected_keyword = category

st.markdown("### 💎 나의 관심 종목")
my_stocks = ["SGC에너지", "리플", "미국 증시", "비트코인"]
cols2 = st.columns(len(my_stocks))

for i, stock in enumerate(my_stocks):
    if cols2[i].button(stock, use_container_width=True):
        selected_keyword = stock

st.divider()
st.markdown("### 🔍 직접 검색")
user_input = st.text_input("궁금한 뉴스 키워드를 입력하세요", value=selected_keyword, placeholder="예: 삼성전자, 부동산 대책 등")

# --- 5. 뉴스 요약 로직 (날짜 추출 기능 추가) ---
if user_input:
    with st.spinner(f"'{user_input}' 뉴스를 AI가 분석 중입니다..."):
        try:
            url = f"https://news.google.com/rss/search?q={user_input}&hl=ko&gl=KR&ceid=KR:ko"
            response = requests.get(url)
            soup = BeautifulSoup(response.content, features="xml")
            items = soup.find_all('item')
            
            if items:
                news_data = []
                for item in items[:5]:
                    title = item.title.text
                    # 구글 뉴스의 날짜 형식(RFC 822)을 읽기 쉬운 한글 형식으로 변환
                    raw_date = item.pubDate.text
                    try:
                        # 예: "Tue, 07 Apr 2026 10:30:00 GMT" -> "2026-04-07"
                        date_obj = datetime.strptime(raw_date, '%a, %d %b %Y %H:%M:%S %Z')
                        clean_date = date_obj.strftime('%Y-%m-%d %H:%M')
                    except:
                        clean_date = raw_date # 변환 실패 시 원본 표시
                    
                    news_data.append({"title": title, "date": clean_date})

                # AI 요약용 텍스트 생성
                all_titles = "\n".join([f"- {n['title']}" for n in news_data])
                
                prompt = f"다음 뉴스 제목들을 읽고 '{user_input}'의 핵심 내용을 한글로 3줄 요약해줘:\n{all_titles}"
                result = model.generate_content(prompt)
                
                # 결과 출력
                st.success(f"✅ '{user_input}' 요약 리포트")
                st.info(result.text)
                
                # 📅 날짜 정보 표시 섹션 추가
                with st.expander("📌 참고한 뉴스 소스 및 날짜 확인"):
                    for n in news_data:
                        st.write(f"⏱️ **{n['date']}** | {n['title']}")
            else:
                st.warning(f"'{user_input}' 관련 최신 소식이 없습니다.")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
