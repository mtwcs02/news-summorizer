import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime

# 1. 앱 화면 설정
st.set_page_config(page_title="나만의 스마트 뉴스 비서", page_icon="🗞️", layout="wide")

# --- ⚙️ [새 기능] 오른쪽 사이드바 설정창 ---
with st.sidebar:
    st.header("⚙️ 맞춤 설정")
    # 눈높이 모드 선택 (기본값: 전문가용)
    level_mode = st.radio(
        "요약 눈높이를 선택하세요",
        ("초등학생용 🎒", "중학생용 📝", "전문가용 💼"),
        index=2
    )
    st.info(f"현재 **{level_mode}** 모드로 작동 중입니다.")

st.title("🗞️ AI 맞춤 뉴스 브리핑")
st.write(f"오늘의 뉴스를 **{level_mode}** 수준으로 분석해 드립니다.")

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
user_input = st.text_input("궁금한 뉴스 키워드를 입력하세요", value=selected_keyword)

# --- 5. 뉴스 요약 로직 (눈높이 맞춤형 프롬프트 적용) ---
if user_input:
    with st.spinner(f"'{user_input}' 정보를 {level_mode}에 맞춰 분석 중입니다..."):
        try:
            search_query = user_input
            if user_input == "오늘의 주요 뉴스":
                search_query = "오늘의 주요 뉴스 신문 헤드라인 1면 when:1d"
            
            url = f"https://news.google.com/rss/search?q={search_query}&hl=ko&gl=KR&ceid=KR:ko"
            response = requests.get(url)
            soup = BeautifulSoup(response.content, features="xml")
            items = soup.find_all('item')
            
            if items:
                news_data = []
                for item in items[:10]:
                    raw_date = item.pubDate.text
                    try:
                        date_obj = datetime.strptime(raw_date, '%a, %d %b %Y %H:%M:%S %Z')
                        clean_date = date_obj.strftime('%Y-%m-%d %H:%M')
                    except:
                        clean_date = raw_date
                    news_data.append({"title": item.title.text, "date": clean_date, "link": item.link.text})

                all_titles = "\n".join([f"- {n['title']}" for n in news_data])
                
                # --- [수정된 부분] 모드에 따른 AI 명령(프롬프트) 설정 ---
                if "초등학생" in level_mode:
                    system_role = "너는 다정한 초등학교 선생님이야. 어려운 경제/정치 용어는 일상적인 물건에 비유해서 아주 쉽게 설명해줘. 아이들이 흥미를 느낄 수 있게 요약해줘."
                elif "중학생" in level_mode:
                    system_role = "너는 논리적인 중학교 사회 선생님이야. 시사 상식을 쌓을 수 있게 핵심 키워드 위주로 정리해주고, 사건의 원인과 결과를 알기 쉽게 요약해줘."
                else: # 전문가용
                    system_role = "너는 베테랑 신문사 편집장이자 경제 분석가야. 투자자와 전문가를 위해 전문 용어를 정확하게 사용하고, 수치와 팩트 위주로 아주 날카롭고 깔끔하게 분석해줘."

                prompt = f"""
                {system_role}
                
                키워드: {user_input}
                뉴스 제목 목록:
                {all_titles}
                
                위 내용을 바탕으로 핵심 내용 3가지만 뽑아서 요약해줘.
                """
                
                result = model.generate_content(prompt)
                
                st.success(f"✅ {level_mode} 맞춤 요약 완료")
                st.markdown(result.text)
                
                with st.expander("🔗 참고한 뉴스 원본 보기"):
                    for n in news_data:
                        st.markdown(f"⏱️ {n['date']} | [{n['title']}]({n['link']})")
            else:
                st.warning(f"'{user_input}' 관련 최신 소식이 없습니다.")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
