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
my_stocks = ["미국 증시", "한국 증시", "비트코인", "리플"]

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
    try:
        audio_bytes = loop.run_until_complete(generate_high_quality_speech(text))
    finally:
        loop.close()  # 에러가 나더라도 루프를 안전하게 닫음
    return audio_bytes

# 5. 뉴스 수집 및 요약 함수 (시작점 및 따옴표 완전 교정본)
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

       # --- [2단계: 모드 설정 (글자 수 및 생각 질문 추가 버전)] ---
        if "초등" in mode:
            role_name = "다정한 엄마"
            content_rule = """
            - 뉴스 딱 2개만 선정해서 요약할 것.
            - [분량 제한]: 각 뉴스당 공백 포함 **250자 내외**, 전체 합쳐서 **500자 내외**로 아주 짧고 명확하게 작성할 것.
            - [정치 정의]: "정치는 우리나라를 더 좋게 만들기 위해 어른들이 생각을 나누는 행복한 고민"으로 시작할 것.
            - [설명 방식]: 비유를 먼저 하고 용어(묘수, 극단적 등)는 나중에 쉽게 풀어서 알려줄 것.
            - [부드러운 표현]: '나라 망한다' 대신 '시험 걱정하느라 다른 걸 못 보는 마음'처럼 순화할 것.
            - [마무리]: 뉴스 브리핑이 끝난 후 반드시 아이의 경험과 연결된 **'오늘의 생각 질문'**을 1개 던질 것.
            """
            start_msg = "엄마가 오늘 뉴스 들려줄게."
            end_msg = "오늘 하루도 즐겁게 지내! 사랑해."

        elif "중학생" in mode:
            role_name = "사춘기 아들을 둔 지적인 엄마"
            content_rule = """
            - 핵심 뉴스 3개 선정해서 요약할 것.
            - [분량 제한]: 전체 공백 포함 **700자 내외**를 반드시 지킬 것.
            - [말투]: 절대 딱딱한 앵커 말투 금지. '~란다', '~했대', '~인 것 같아' 같은 다정하고 지적인 구어체를 유지할 것.
            - [구성]: 사실 전달 -> 사회적 의미(왜 중요한지) -> 생각할 거리(교훈) 순서로 논리적으로 구성할 것.
            - [지식]: 어려운 시사 용어(보증금, 안보, 환율 등)는 반드시 한 문장으로 친절하게 풀이할 것.
            - [마무리]: 브리핑 끝에 뉴스 내용과 관련된 논리적인 **'오늘의 생각 질문'**을 1개 포함할 것.
            """
            start_msg = "오늘 뉴스를 들려줄게"
            end_msg = "오늘 하루도 네가 가진 멋진 생각들을 펼치며 즐겁게 보내렴!사랑해!"

        else:
            role_name = "전문 뉴스 아나운서"
            content_rule = """
            - 주요 뉴스 3개 선정.
            - 객관적이고 정확한 정보 전달 (수치와 통계 활용).
            - 전문 용어를 사용하여 신뢰감 있는 뉴스 브리핑 톤 유지.
            - [분량]: 전체 1000자 내외로 상세히 전달.
            """
            start_msg = "안녕하십니까. 2026년 4월 13일 뉴스 브리핑입니다."
            end_msg = "이상으로 뉴스를 마치겠습니다. 시청해 주셔서 감사합니다."

        # --- [3단계: AI에게 보내는 최종 명령] ---
        prompt = f"""
        너의 역할은 지금부터 [{role_name}]야. 아래 지침을 완벽히 지켜줘.
        
        {content_rule}
        - 시작은 반드시 "{start_msg}"
        - 마무리는 반드시 "{end_msg}"
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
