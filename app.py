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
    level_mode = st.radio("요약 눈높이", ("초등학생용 🎒", "중학생용 📝", "전문가용 💼"), index=0)
    st.info("💡 실시간 뉴스 요약! (엄마뉴스)")

st.title("🗞️ 엄마가 읽어주는 뉴스 브리핑")

# 2. AI 모델 설정
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    if not api_key:
        st.error("API 키가 설정되지 않았습니다.")
        st.stop()
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
except Exception as e:
    st.error(f"⚠️ API 키 설정 오류: {e}")
    st.stop()

# 상태 초기화
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

# 4. 음성 생성 함수 (안정화)
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

def run_async_tts(text):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    audio_bytes = loop.run_until_complete(generate_high_quality_speech(text))
    loop.close()
    return audio_bytes

# 5. 뉴스 수집 및 요약 함수 (안정화)
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_and_summarize(query, mode):
    try:
        q = query if query != "오늘의 주요 뉴스" else "대한민국 주요 뉴스 속보 when:1d"
        q = f"{q} 대한민국 뉴스 when:1d"

        url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
        res = requests.get(url, timeout=5)
        res.raise_for_status()

        soup = BeautifulSoup(res.content, features="xml")
        items = soup.find_all('item')[:5]

        if not items:
            return None, []

        # 중복 제거
        titles = list(dict.fromkeys([i.title.text for i in items]))
        all_titles = "\n".join([f"- {t}" for t in titles])

        # 모드 설정
        if "초등" in mode:
            role_name = "다정한 엄마"
            content_rule = """
            - 핵심 뉴스 2개
            - 문장 짧게
            - 비유 1개만 사용
            - 설명 먼저, 용어 나중
            """
            start_msg = "엄마가 오늘 뉴스 들려줄게."
            end_msg = "오늘 하루도 친구들과 사이좋게 지내며 즐겁게 보내자!"

        elif "중학생" in mode:
            role_name = "지적인 엄마"
            content_rule = """
            - 뉴스 3개
            - 사실 -> 의미 -> 교훈 구조
            - 어려운 용어 1줄 설명
            - 엄마 말투 유지 (~란다, ~했대)
            """
            start_msg = "엄마가 오늘 뉴스 들려줄게."
            end_msg = "오늘 하루도 즐겁게 보내자!"

        else:
            role_name = "전문 뉴스 아나운서"
            content_rule = """
            - 뉴스 3개
            - 객관적 요약
            - 전문 용어 사용
            """
            start_msg = "안녕하십니까. 뉴스 브리핑입니다."
            end_msg = "이상으로 뉴스를 마치겠습니다. 감사합니다."

        prompt = f"""
        너의 역할은 [{role_name}]야.

        [지시사항]
        {content_rule}
        - 시작은 "{start_msg}"
        - 끝은 "{end_msg}"
        - 문장은 짧게

        [뉴스]
        {all_titles}
        """

        try:
            response = model.generate_content(prompt)
            summary = response.text
        except Exception as e:
            summary = f"요약 중 오류가 발생했어: {e}"

        news_list = [{"title": i.title.text, "link": i.link.text} for i in items]

        return summary, news_list

    except Exception as e:
        return f"뉴스를 불러오는 중 오류 발생: {e}", []

# 6. 실행
if user_input:
    with st.spinner(f"'{user_input}' 뉴스 가져오는 중..."):
        summary, news_data = fetch_and_summarize(user_input, level_mode)

        if summary:
            st.success(f"✅ {level_mode} 브리핑 완료!")
            st.markdown(summary)
            st.write("---")

            if st.button("🎧 음성 듣기"):
                with st.spinner("음성 생성 중..."):
                    audio_bytes = run_async_tts(summary)
                    st.audio(audio_bytes, format='audio/mp3', autoplay=True)

            with st.expander("🔗 원본 뉴스 보기"):
                for n in news_data:
                    st.markdown(f"- [{n['title']}]({n['link']})")

        else:
            st.warning("뉴스를 찾을 수 없습니다.")
