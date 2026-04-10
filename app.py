import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import edge_tts
import asyncio
import os
import tempfile

# 1. 앱 설정
st.set_page_config(page_title="나만의 스마트 뉴스 비서", page_icon="🗞️", layout="wide")

with st.sidebar:
    st.header("⚙️ 맞춤 설정")
    # ✅ 여기서 정한 이름과 밑에 함수에서 체크하는 이름이 같아야 합니다!
    level_mode = st.radio("요약 눈높이", ("초등학생용 🎒", "중학생용 📝", "전문가용 💼"), index=0)
    st.info("💡 실시간 뉴스 요약! (엄마뉴스)")

st.title("🗞️ 엄마가 읽어주는 뉴스 브리핑")

# 2. AI 모델 설정
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
except Exception as e:
    st.error(f"⚠️ API 키 설정 오류: {e}")
    model = None

if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

def update_query(new_query):
    st.session_state.search_query = new_query

# 3. 메뉴 구성
categories = ["오늘의 주요 뉴스", "정치", "경제", "사회"]
my_stocks = ["SGC에너지", "리플", "미국 증시", "비트코인"]

st.markdown("### 📍 빠른 선택")
cols = st.columns(4)
for i, cat in enumerate(categories):
    cols[i].button(cat, key=f"cat_{i}", on_click=update_query, args=(cat,), use_container_width=True)

cols2 = st.columns(4)
for i, stock in enumerate(my_stocks):
    cols2[i].button(stock, key=f"stock_{i}", on_click=update_query, args=(stock,), use_container_width=True)

st.divider()
user_input = st.text_input("🔍 직접 검색 (검색어를 입력하고 엔터를 치세요)", key="search_query")

async def generate_high_quality_speech(text):
    voice = "ko-KR-SunHiNeural" 
    communicate = edge_tts.Communicate(text, voice)
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
        temp_filename = fp.name
    await communicate.save(temp_filename)
    with open(temp_filename, 'rb') as f:
        audio_bytes = f.read()
    os.unlink(temp_filename) 
    return audio_bytes

# 🧠 뉴스 수집 및 요약 함수
@st.cache_data(ttl=60, show_spinner=False)
def fetch_and_summarize(query, mode):
    q = query if query != "오늘의 주요 뉴스" else "대한민국 주요 뉴스 속보 when:1d"
    url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
    res = requests.get(url)
    items = BeautifulSoup(res.content, features="xml").find_all('item')[:10]
    
    if not items: 
        return None, []
    
    all_titles = "\n".join([f"- {i.title.text}" for i in items])
    
    # 2. 모드별 페르소나 설정 (매칭 단어 수정 완료!)
    if "초등" in mode:
        role_name = "다정한 엄마"
        content_rule = """
        - 핵심 뉴스 딱 2가지만 선정.
        - [정치의 시작]: 반드시 "정치는 우리나라를 더 좋게 만들기 위해 어른들이 생각을 나누는 행복한 고민이란다"로 시작.
        - [설명 방식]: 비유를 먼저 하고 용어는 나중에 알려줄 것. (예: 묘수, 극단적 등)
        - 문장을 아주 짧고 리듬감 있게 구성.
        """
        start_msg = "엄마가 오늘 뉴스 들려줄게."
        end_msg = "오늘 하루도 친구들과 사이좋게 지내며 즐겁게 보내자!"

    elif "중학생" in mode:
        # 🧑 중학교 1학년 (14살) 모드: [정보 + 의미 + 교훈] 93점 돌파 버전
        role_name = "사춘기 아들을 둔 지적인 엄마"
        content_rule = """
        - 핵심 뉴스 3가지를 선정할 것.
        - [정보의 정확성]: 뉴스 제목의 핵심 키워드(예: 장애인 평생교육, 전세 사기, 협약 등)를 생략하지 말고 명확하게 언급할 것.
        - [비유의 절제]: 너무 어린아이 같은 비유(보물찾기, 과자 등)는 피하고, 실제 사회 현상에 빗대어 설명할 것.
        - [사회적 의미 추가]: 사건이 '왜 일어났는지', 그리고 '우리 사회에 어떤 의미가 있는지' 한 줄씩 덧붙일 것.
        - [용어 풀이]: 시사 용어(전세 사기, 보증금, 협약 등)는 문맥 속에서 자연스럽게 한 문장으로 풀이해줄 것.
        - [구조]: 사실(Fact) 전달 -> 사회적 의미(Meaning) -> 생각할 거리(Lesson) 순서로 구성할 것.
        """
        start_msg = "엄마가 오늘 뉴스 들려줄게."
        end_msg = "오늘 하루도 즐겁게 보내자!"

    else:
        role_name = "전문 뉴스 아나운서"
        content_rule = """
        - 주요 뉴스 3가지를 객관적이고 정확하게 요약.
        - 전문 용어와 수치를 활용해 신뢰감 있는 톤 유지.
        """
        start_msg = "안녕하십니까. 뉴스 브리핑입니다."
        end_msg = "이상으로 뉴스를 마치겠습니다. 감사합니다."

    prompt = f"""
    너의 역할은 [{role_name}]야. 아나운서 말투가 필요한지 엄마 말투가 필요한지 명확히 구분해.
    
    [지시 사항]
    {content_rule}
    - 시작은 반드시 "{start_msg}"로 하고, 마무리는 "{end_msg}"로 할 것.
    - 번호 사용 금지, '말이야', '있지' 같은 반복 추임새 금지.
    
    [뉴스 리스트]
    {all_titles}
    """
    
    response = model.generate_content(prompt)
    news_list = [{"title": i.title.text, "link": i.link.text} for i in items]
    return response.text, news_list

# 4. 실행 로직
if user_input and model:
    with st.spinner(f"'{user_input}' 소식을 가져오고 있어요..."):
        try:
            summary, news_data = fetch_and_summarize(user_input, level_mode)
            if summary:
                st.success(f"✅ {level_mode} 맞춤 브리핑 완료!")
                st.markdown(summary)
                st.write("---")
                if st.button("🎧 고음질 음성 듣기"):
                    with st.spinner("뉴스를 읽어줄 준비 중입니다..."):
                        audio_bytes = asyncio.run(generate_high_quality_speech(summary))
                        st.audio(audio_bytes, format='audio/mp3', autoplay=True)
                with st.expander("🔗 참고한 뉴스 원본 링크"):
                    for n in news_data:
                        st.markdown(f"- [{n['title']}]({n['link']})")
            else:
                st.warning("관련 뉴스를 찾을 수 없어요.")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
