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

# 🧠 뉴스 수집 및 요약 함수 (분량 및 들여쓰기 완벽 교정본)
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
    
    # 2. 모드별 세부 규칙 (수직 정렬 주의!)
    if "초등" in mode:
        # 🧒 초등 4학년: 딱 2개 뉴스, 5~6문장 이내 (아주 짧게!)
        role_name = "다정한 엄마"
        content_rule = """
        - [강력 제약]: 뉴스 주제는 **무조건 딱 2개**만 골라줘. 
        - [분량 제한]: 전체 내용을 읽었을 때 **40초 이내**로 끝날 만큼 짧게 써줘. (총 5~6문장)
        - [금지어]: '징검다리 문장' 같은 단어는 절대 밖으로 노출하지 마.
        - [정치 정의]: "정치는 우리나라를 더 좋게 만드는 행복한 고민"이라고 1문장으로 시작해.
        - [비유]: 한 뉴스당 비유는 딱 1개씩만! (설명 -> 비유 -> 용어 순서)
        """
        start_msg = "엄마가 오늘 뉴스 들려줄게."
        end_msg = "오늘 하루도 즐겁게 보내자!"

    elif "중등" in mode:
        # 🧑 중등 1학년: 뉴스 3개, 논리적 설명
        role_name = "지적인 엄마"
        content_rule = """
        - 뉴스 주제 3개 선정. 시사 용어를 사용하되 한 문장으로 풀이해줘.
        - 사건의 원인과 결과를 논리적으로 연결해줘.
        """
        start_msg = "엄마가 오늘 뉴스 들려줄게."
        end_msg = "오늘 학교 잘 다녀오렴!"

    else:
        # 🎙️ 전문가용: 객관적인 아나운서 브리핑
        role_name = "전문 뉴스 아나운서"
        content_rule = """
        - 주요 뉴스 3가지를 데이터와 수치를 섞어 정확하게 요약해줘.
        - 지적이고 신뢰감 있는 톤을 유지해줘.
        """
        start_msg = "안녕하십니까. 뉴스 브리핑입니다."
        end_msg = "감사합니다."

    # 3. AI에게 보내는 최종 명령
    prompt = f"""
    너는 지금부터 [{role_name}]야. 아래 지침을 지켜서 요약해줘.

    [작성 규칙]
    {content_rule}
    - 시작은 반드시 "{start_msg}"로 하고, 끝은 "{end_msg}"로 할 것.
    - '첫째, 둘째' 번호 쓰지 말고 문장을 부드럽게 이어줘.
    - 문장을 짧게 끊어서 리듬감을 살려줘.
    - '말이지', '있지' 같은 추임새는 1번만 쓰거나 아예 쓰지 마.

    뉴스 리스트:
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
