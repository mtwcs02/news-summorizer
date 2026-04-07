import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime

# 1. 앱 설정
st.set_page_config(page_title="나만의 스마트 뉴스 비서", page_icon="🗞️", layout="wide")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 맞춤 설정")
    level_mode = st.radio("요약 눈높이", ("초등학생용 🎒", "중학생용 📝", "전문가용 💼"), index=2)

st.title("🗞️ AI 맞춤 뉴스 브리핑")

# 2. 🔐 AI 모델 설정 (에러 방지 로직 추가)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # [수정] 가장 안전하게 모델 이름을 찾는 방식입니다.
    # gemini-1.5-flash가 안되면 gemini-pro라도 가져오게 합니다.
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    if 'models/gemini-1.5-flash' in available_models:
        model_name = 'models/gemini-1.5-flash'
    elif 'models/gemini-pro' in available_models:
        model_name = 'models/gemini-pro'
    else:
        model_name = available_models[0]
        
    model = genai.GenerativeModel(model_name)
except Exception as e:
    st.error(f"AI 연결에 문제가 생겼어요: {e}")
    st.stop()

# 3. 메뉴 및 버튼 구성
categories = ["오늘의 주요 뉴스", "정치", "경제", "사회"]
my_stocks = ["SGC에너지", "리플", "미국 증시", "비트코인"]

st.markdown("### 📍 빠른 선택")
cols = st.columns(4)
selected_keyword = ""
for i, cat in enumerate(categories):
    if cols[i].button(cat, use_container_width=True): selected_keyword = cat

cols2 = st.columns(4)
for i, stock in enumerate(my_stocks):
    if cols2[i].button(stock, use_container_width=True): selected_keyword = stock

st.divider()
user_input = st.text_input("🔍 직접 검색", value=selected_keyword)

# 4. 뉴스 수집 함수 (재시도 로직)
def get_news(query):
    # '오늘의 주요 뉴스'일 때 검색이 안 되면 다른 키워드로 재시도합니다.
    queries = [query]
    if query == "오늘의 주요 뉴스":
        queries = ["오늘의 주요 뉴스", "대한민국 주요 뉴스 1면", "오늘의 속보"]
    
    for q in queries:
        url = f"https://news.google.com/rss/search?q={q} when:1d&hl=ko&gl=KR&ceid=KR:ko"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, features="xml")
        items = soup.find_all('item')
        if items: return items[:10]
    return []

# 5. 실행 로직
if user_input:
    with st.spinner(f"'{user_input}' 뉴스를 {level_mode} 수준으로 분석 중..."):
        try:
            items = get_news(user_input)
            if items:
                news_data = []
                for item in items:
                    news_data.append({"title": item.title.text, "link": item.link.text})
                
                all_titles = "\n".join([f"- {n['title']}" for n in news_data])
                
                # 모드별 프롬프트
                prompts = {
                    "초등학생용 🎒": "다정한 선생님처럼 비유를 들어 아주 쉽게 3줄 요약해줘.",
                    "중학생용 📝": "논리적인 사회 선생님처럼 핵심 키워드 위주로 3줄 요약해줘.",
                    "전문가용 💼": "베테랑 편집장처럼 팩트와 수치 위주로 날카롭게 3줄 요약해줘."
                }
                
                full_prompt = f"{prompts[level_mode]}\n\n키워드: {user_input}\n뉴스 목록:\n{all_titles}"
                
                # [여기가 에러 났던 지점!] 이제 정상 작동할 거예요.
                result = model.generate_content(full_prompt)
                
                st.success(f"✅ {level_mode} 요약 완료")
                st.markdown(result.text)
                
                with st.expander("🔗 원본 뉴스 링크 (클릭하면 이동)"):
                    for n in news_data:
                        st.markdown(f"- [{n['title']}]({n['link']})")
            else:
                st.warning("앗, 최근 검색된 뉴스가 없네요. 다른 키워드를 입력해 보세요!")
        except Exception as e:
            st.error(f"작동 중 오류가 발생했습니다: {e}")
