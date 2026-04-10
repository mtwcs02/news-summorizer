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

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 맞춤 설정")
    level_mode = st.radio("요약 눈높이", ("초등학생용 🎒", "중학생용 📝", "전문가용 💼"), index=2)
    st.info("💡 실시간 뉴스 요약! (엄마뉴스)")

st.title("🗞️ 엄마가 읽어주는 뉴스 브리핑")

# 2. AI 모델 설정 (한도 넉넉한 Lite 모델)
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
except Exception as e:
    st.error(f"⚠️ API 키 설정 오류: {e}")
    model = None

# ======= 🧠 스트림릿 기억상실증 방지 (메모리) =======
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

# ======= 🎙️ 고음질 여성 음성 (SunHi - 가장 자연스러운 한국어 여성 목소리) =======
async def generate_high_quality_speech(text):
    voice = "ko-KR-SunHiNeural" # 확실한 여성 목소리 고정!
    communicate = edge_tts.Communicate(text, voice)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
        temp_filename = fp.name
        
    await communicate.save(temp_filename)
    
    with open(temp_filename, 'rb') as f:
        audio_bytes = f.read()
        
    os.unlink(temp_filename) 
    return audio_bytes

# 🧠 뉴스 수집 및 요약 함수 (초4·중1·전문가 완벽 통합 버전)
@st.cache_data(ttl=60, show_spinner=False)
def fetch_and_summarize(query, mode):
    # 1. 뉴스 데이터 수집
    q = query if query != "오늘의 주요 뉴스" else "대한민국 주요 뉴스 속보 when:1d"
    url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
    
    res = requests.get(url)
    items = BeautifulSoup(res.content, features="xml").find_all('item')[:10]
    
    if not items: 
        return None, []
    
    all_titles = "\n".join([f"- {i.title.text}" for i in items])
    
    # 2. 모드별 페르소나 및 세부 규칙 설정
    if "초등" in mode:
        # 🧒 초등학교 4학년 (11살) 모드: 다정한 엄마표 지식 전달
        role_name = "다정한 엄마"
        content_rule = """
        - 핵심 뉴스 딱 2가지만 선정.
        - [정치 뉴스 정의]: 정치는 '싸움'이 아니라 '우리나라를 더 좋게 만들기 위해 어른들이 생각을 나누는 일'이라고 긍정적으로 설명할 것.
        - [지식 전달 방식]: 무조건 '비유와 설명'을 먼저 하고, 마지막에 "이걸 어려운 말로 OO라고 한단다"라고 이름을 알려줄 것. (예: 아픈 뒤 회복 느린 것 -> 성장 둔화)
        - [지역 표현 자제]: '강남', '부산' 같은 구체적 지명 대신 '인기 있는 동네', '우리 주변'처럼 일반적인 말로 바꿀 것.
        - [비유 대상]: 과자, 장난감, 반장 선거, 학교생활 등 아이가 직접 겪는 일에 빗대어 설명할 것.
        - 문장을 아주 짧게 끊고 리듬감 있게 구성할 것.
        """
        start_msg = "엄마가 오늘 뉴스 들려줄게."
        end_msg = "오늘 하루도 즐겁게 보내자!"

    elif "중등" in mode:
        # 🧑 중학교 1학년 (14살) 모드: 지적인 엄마의 시사 가이드
        role_name = "지적인 엄마"
        content_rule = """
        - 핵심 뉴스 3가지 선정.
        - [지식 전달 방식]: 공급 충격, 환율, 금리 등 시사 용어를 그대로 사용하되, 반드시 한 문장으로 친절하게 풀이해서 배경지식을 쌓아줄 것.
        - [논리 구성]: 사건의 원인과 결과를 논리적으로 연결해줄 것.
        - [연결고리]: 뉴스 사이사이에 "그리고 또 눈여겨볼 소식이 있어" 같은 자연스러운 징검다리 문장을 넣을 것.
        """
        start_msg = "엄마가 오늘 뉴스 들려줄게."
        end_msg = "오늘 하루도 즐겁게 보내자! 학교 가서 오늘 배운 내용 아는 척 한번 해보렴."

    else:
        # 🎙️ 전문가용 (성인/아나운서) 모드: 9시 뉴스 브리핑
        role_name = "전문 뉴스 아나운서"
        content_rule = """
        - 주요 뉴스 3가지를 객관적이고 정확하게 요약.
        - 전문 용어와 구체적인 수치(데이터)를 활용해 신뢰감 있는 정보 전달.
        - 군더더기 없이 깔끔하고 지적인 톤 유지.
        """
        start_msg = "안녕하십니까. 뉴스 브리핑입니다."
        end_msg = "이상으로 뉴스를 마치겠습니다. 감사합니다."

    # 3. AI에게 보내는 최종 명령 (말투와 흐름 집중)
    prompt = f"""
    너의 역할은 지금부터 [{role_name}]야. 아래 규칙을 완벽하게 지켜서 뉴스를 요약해줘.

    [지식 및 흐름 규칙]
    {content_rule}

    [말투 가이드]
    - 시작은 반드시 "{start_msg}"로 하고, 마무리는 "{end_msg}"로 해.
    - '첫째, 둘째' 같은 번호는 절대 쓰지 말고 문장을 자연스럽게 이어줘.
    - '말이야', '있지' 같은 반복적인 추임새는 촌스러우니 쓰지 마.
    - 문장 끝은 모드에 맞게 다정하게(~란다, ~했대) 혹은 전문적으로(~입니다) 유지해.

    [요약할 뉴스 리스트]
    {all_titles}
    """
    
    response = model.generate_content(prompt)
    news_list = [{"title": i.title.text, "link": i.link.text} for i in items]
    return response.text, news_list

    # 3. AI에게 보내는 최종 명령서 (엄마 모드)
    prompt = f"""
    [너의 역할]
    너는 자녀의 공부를 돕는 지적이고 다정한 '엄마'야. 아나운서 말투는 절대 금지!

    [학년별 맞춤 지식 수준]
    {content_rule}

    [군더더기 제거 규칙]
    - "우선 말이야", "그리고 또 말이야" 같은 불필요한 추임새는 절대 쓰지 마. 
    - 문장마다 "그리고"로 시작하지 말고 자연스럽게 내용을 이어줘.
    - 말투만 "~하단다", "~했대" 처럼 다정하게 유지해.

    [말투 가이드]
    1. 시작: "엄마가 오늘 뉴스 들려줄게." (간결하게)
    2. 번호(첫째, 둘째) 금지.
    3. 마침: "오늘 하루도 즐겁게 보내자!"

    [요약할 뉴스 리스트]
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
                st.warning("관련 뉴스를 찾을 수 없어요. 다른 검색어를 입력해 보세요.")
                
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
