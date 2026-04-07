import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime

# 1. 앱 설정
st.set_page_config(page_title="나만의 스마트 뉴스 비서", page_icon="🗞️", layout="wide")

with st.sidebar:
    st.header("⚙️ 맞춤 설정")
    level_mode = st.radio("요약 눈높이", ("초등학생용 🎒", "중학생용 📝", "전문가용 💼"), index=2)

st.title("🗞️ AI 맞춤 뉴스 브리핑")

# 2. API 설정
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("API 키를 확인해주세요.")
    st.stop()

# 3. 메뉴 구성
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

# 4. 뉴스 가져오기 함수 (실패 시 재시도 기능 추가)
def get_news(query):
    # 검색어 리스트 (첫 번째가 안 나오면 다음 것으로 시도)
    queries = [query]
    if query == "오늘의 주요 뉴스":
        queries = ["오늘의 주요 뉴스", "대한민국 주요 뉴스 속보", "실시간 헤드라인"]
    
    for q in queries:
        url = f"https://news.google.com/rss/search?q={q} when:1d&hl=ko&gl=KR&ceid=KR:ko"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, features="xml")
        items = soup.find_all('item')
        if items: return items[:10]
    return []

# 5. 실행 로직
if user_input:
    with st.spinner(f"'{user_input}' 뉴스를 불러오는 중..."):
        items = get_news(user_input)
        if items:
            news_data = []
            for item in items:
                news_data.append({"title": item.title.text, "link": item.link.text})
            
            all_titles = "\n".join([f"- {n['title']}" for n in news_data])
            
            # 모드별 프롬프트 설정
            prompts = {
                "초등학생용 🎒": "다정한 선생님처럼 비유를 들어 아주 쉽게 3줄 요약해줘.",
                "중학생용 📝": "논리적인 사회 선생님처럼 핵심 키워드 위주로 3줄 요약해줘.",
                "전문가용 💼": "베테랑 편집장처럼 팩트와 수치 위주로 날카롭게 3줄 요약해줘."
            }
            
            full_prompt = f"{prompts[level_mode]}\n\n키워드: {user_input}\n뉴스 목록:\n{all_titles}"
            result = model.generate_content(full_prompt)
            
            st.success(f"✅ {level_mode} 요약 완료")
            st.markdown(result.text)
            
            with st.expander("🔗 원본 뉴스 링크"):
                for n in news_data:
                    st.markdown(f"- [{n['title']}]({n['link']})")
        else:
            st.warning("현재 검색된 최신 뉴스가 없습니다. 잠시 후 다시 시도해 주세요.")
