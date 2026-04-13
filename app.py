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
    model = genai.GenerativeModel('gemini-2.0-flash-lite') # 최신 모델명 확인 필요
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
my_stocks = ["과학", "한국 증시", "미국 증시", "비트코인"]

st.markdown("### 📍 빠른 선택")

cols = st.columns(4)
for i, cat in enumerate(categories):
    cols[i].button(cat, key=f"cat_{i}", on_click=update_query, args=(cat,), use_container_width=True)

cols2 = st.columns(4)
for i, stock in enumerate(my_stocks):
    cols2[i].button(stock, key=f"stock_{i}", on_click=update_query, args=(stock,), use_container_width=True)

st.divider()
user_input = st.text_input("🔍 직접 검색 (검색어를 입력하고 엔터를 치세요)", key="search_query_input", value=st.session_state.search_query)

# 4. 음성 생성 함수
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
    try:
        audio_bytes = loop.run_until_complete(generate_high_quality_speech(text))
    finally:
        loop.close()
    return audio_bytes

# 5. 뉴스 수집 및 요약 함수
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_and_summarize(query, mode):
    try:
        # --- [1단계: 뉴스 수집] ---
        q = query if query != "오늘의 주요 뉴스" else "대한민국 주요 뉴스 속보 when:1d"
        search_q = f"{q} 대한민국 뉴스 when:1d"

        url = f"https://news.google.com/rss/search?q={search_q}&hl=ko&gl=KR&ceid=KR:ko"
        res = requests.get(url, timeout=5)
        res.raise_for_status()

        soup = BeautifulSoup(res.content, features="xml")
        items = soup.find_all('item')[:5]

        if not items:
            return None, []

        titles = list(dict.fromkeys([i.title.text for i in items]))
        all_titles = "\n".join([f"- {t}" for t in titles])

        # --- [2단계: 모드 설정 - 안정성 최적화 버전] ---
        if "초등" in mode:
            role_name = "다정한 엄마"
            content_rule = """
            [출력 구조 템플릿 - 반드시 그대로 따를 것]
            1. 시작 인사: "엄마가 오늘 뉴스 들려줄게."
            2. 공감 문장: (조금 낯설 수 있지만 엄마가 쉽게 이야기해줄게.)
            3. 뉴스 요약 (반드시 2개만):
               - 사실: (누가/무엇을 했는지 1문장)
               - 비유: (장난감, 놀이터, 양치질 등 9살 일상 비유 1문장)
               - 중요성: (왜 중요한지 1문장)
            4. 오늘의 생각 질문: (아이 스스로 생각할 수 있는 질문 1개)
            5. 마무리 인사: "오늘 하루도 즐겁게 지내! 사랑해."

            [작성 규칙]
            - 각 뉴스는 "사실-비유-중요성" 3문장 구조 고정.
            - 전체 분량은 공백 포함 400~450자 엄수.
            - 어려운 용어는 아이 일상의 경험으로 완전히 변환할 것.
            """
            start_msg = "엄마가 오늘 뉴스 들려줄게."
            end_msg = "오늘 하루도 즐겁게 지내! 사랑해."

        elif "중학생" in mode:
            role_name = "사춘기 아들을 둔 지적인 엄마"
            content_rule = """
            [출력 구조 템플릿]
            1. 시작 인사: "오늘 뉴스를 들려줄게."
            2. 뉴스 요약 (반드시 3개):
               - 사실 / 의미 / 생각할 거리 구조로 작성.
            3. 오늘의 생각 질문: (논리적 질문 1개)
            4. 마무리 인사: "오늘 하루도 네가 가진 멋진 생각들을 펼치며 즐겁게 보내렴! 사랑해!"

            [작성 규칙]
            - 지적인 구어체 사용 (~란다, ~했대).
            - 어려운 용어(환율, 금리 등)는 반드시 1문장으로 친절하게 풀이.
            - 전체 분량 650~750자 사이로 작성.
            """
            start_msg = "오늘 뉴스를 들려줄게."
            end_msg = "오늘 하루도 네가 가진 멋진 생각들을 펼치며 즐겁게 보내렴! 사랑해!"

        else:
            role_name = "전문 뉴스 아나운서"
            content_rule = """
            - 주요 뉴스 3개 선정. 객관적 정보 전달.
            - 전문 용어와 수치 활용. 신뢰감 있는 톤.
            - 분량: 전체 1000자 내외.
            """
            start_msg = "안녕하십니까. 뉴스 브리핑입니다."
            end_msg = "이상으로 뉴스를 마치겠습니다. 감사합니다."

        # --- [3단계: AI에게 보내는 최종 명령] ---
        prompt = f"""
        너의 역할은 지금부터 [{role_name}]야. 아래 지침을 완벽히 지켜줘.
        {content_rule}
        - 번호(첫째, 둘째) 사용 금지. 문장을 자연스럽게 이어줘.
        - 뉴스 사이사이에 자연스러운 '징검다리 문장'을 넣어서 흐름을 부드럽게 할 것.

        [뉴스 리스트]
        {all_titles}
        """

        response = model.generate_content(prompt)
        summary = response.text
        news_list = [{"title": i.title.text, "link": i.link.text} for i in items]

        return summary, news_list

    except Exception as e:
        return f"뉴스를 불러오는 중 오류 발생: {e}", []

# 6. 실행 로직
final_query = st.session_state.search_query if st.session_state.search_query else user_input

if final_query:
    with st.spinner(f"'{final_query}' 뉴스 가져오는 중..."):
        summary, news_data = fetch_and_summarize(final_query, level_mode)

        if summary:
            st.success(f"✅ {level_mode} 브리핑 완료!")
            st.markdown(f"### 🎙️ {level_mode} 맞춤 요약")
            st.write(summary)
            st.write("---")

            if st.button("🎧 음성으로 듣기"):
                with st.spinner("다정한 엄마 목소리 생성 중..."):
                    audio_bytes = run_async_tts(summary)
                    st.audio(audio_bytes, format='audio/mp3', autoplay=True)

            with st.expander("🔗 원본 뉴스 링크 보기"):
                for n in news_data:
                    st.markdown(f"- [{n['title']}]({n['link']})")
        else:
            st.warning("관련 뉴스를 찾지 못했어요.")
