import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime

# 1. 앱 화면 설정
st.set_page_config(page_title="나만의 스마트 뉴스 비서", page_icon="🗞️")
st.title("🗞️ AI 맞춤 뉴스 브리핑")
st.write("제목을 클릭하면 원본 기사로 이동합니다.")

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

# --- 5. 뉴스 요약 로직 (링크 추출 기능 추가) ---
if user_input:
    with st.spinner(f"'{user_input}' 정보를 분석 중입니다..."):
        try:
            # 검색어 최적화 (오늘의 주요 뉴스일 때)
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
                    # 뉴스 날짜 보기 좋게 변환
                    raw_date = item.pubDate.text
                    try:
                        date_obj = datetime.strptime(raw_date, '%a, %d %b %Y %H:%M:%S %Z')
                        clean_date = date_obj.strftime('%Y-%m-%d %H:%M')
                    except:
                        clean_date = raw_date
                    
                    # 제목, 날짜, 그리고 [중요] 링크 주소를 가져옵니다.
                    news_data.append({
                        "title": item.title.text,
                        "date": clean_date,
                        "link": item.link.text
                    })

                all_titles = "\n".join([f"- {n['title']}" for n in news_data])
                
                # AI 편집장 모드 명령
                prompt = f"""
                너는 베테랑 신문사 편집장이야. 다음 뉴스 제목들을 읽고 핵심을 정리해줘.
                
                키워드: {user_input}
                뉴스 목록:
                {all_titles}
                
                요구사항:
                1. '오늘의 주요 뉴스'라면 각 신문사 1면의 핵심 헤드라인 위주로 정리해줘.
                2. 중복되는 내용은 하나로 합쳐서 가장 중요한 소식 3가지만 뽑아줘.
                3. 각 소식마다 '[분야]' 말머리를 달고, 친절한 어조로 요약해줘.
                """
                
                result = model.generate_content(prompt)
                
                st.success(f"✅ '{user_input}' 브리핑 완료")
                st.markdown(result.text)
                
                # --- [수정된 부분] 날짜와 클릭 가능한 제목 표시 ---
                with st.expander("🔗 참고한 뉴스 원본 보기 (클릭하면 기사로 이동)"):
                    for n in news_data:
                        # [제목](링크) 형식으로 마크다운 링크를 만듭니다.
                        st.markdown(f"⏱️ {n['date']} | [{n['title']}]({n['link']})")
            else:
                st.warning(f"'{user_input}' 관련 최신 소식이 없습니다.")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
