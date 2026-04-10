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

# 🧠 뉴스 수집 및 요약 함수 (들여쓰기 및 지식 수준 완벽 교정본)
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
    
    # 2. 모드별 페르소나 및 지식 수준 설정
    if "초등" in mode:
        # 🧒 초등학교 4학년 (11살) 모드: GPT 피드백 반영 (92점 버전)
        role_name = "다정한 엄마"
        content_rule = """
        - 핵심 뉴스 딱 2가지만 선정.
        - 지식 전달 순서: 쉬운 설명과 비유를 먼저 하고, 마지막에 "이걸 어려운 말로 OO라고 한단다"라고 덧붙여줘.
        - 비유 필수: 과자, 장난감, 용돈 등 일상생활에 빗대어 설명.
        - 문장을 아주 짧게 끊어서 말해줘. (호흡이 길면 듣기 힘들어함)
        """
        start_msg = "엄마가 오늘 뉴스 들려줄게."
        end_msg = "오늘 하루도 즐겁게 보내자!"

    elif "중등" in mode:
        # 🧑 중학교 1학년 (14살) 모드
        role_name = "지적인 엄마"
        content_rule = """
        - 핵심 뉴스 3가지 선정.
        - 지식 전달: 환율, 금리, 공급 충격 등 시사 용어를 사용하되, 반드시 한 문장으로 친절하게 풀이.
        - 논리 구성: 사건의 원인과 결과를 중학생이 이해할 수 있게 연결.
        """
        start_msg = "엄마가 오늘 뉴스 들려줄게."
        end_msg = "오늘 하루도 즐겁게 보내자!"

    else:
        # 🎙️ 전문가용 (성인/아나운서) 모드
        role_name = "전문 뉴스 아나운서"
        content_rule = """
        - 주요 뉴스 3가지를 객관적이고 정확하게 요약.
        - 지식 전달: 전문 용어와 구체적인 수치를 활용한 전문적인 톤.
        """
        start_msg = "안녕하십니까. 9시 뉴스 브리핑입니다."
        end_msg = "이상으로 뉴스 브리핑을 마치겠습니다. 감사합니다."

    # 3. AI에게 보내는 최종 명령서
    prompt = f"""
    너의 역할은 지금부터 [{role_name}]야. 아래 지시사항을 완벽하게 지켜줘.

    [지식 전달 규칙]
    {content_rule}

    [말투 가이드]
    - 시작: "{start_msg}" 로 시작할 것.
    - 마무리: "{end_msg}" 로 끝낼 것.
    - 번호(첫째, 둘째) 금지. 자연스럽게 문장을 이어줘.
    - "말이야", "말이지" 같은 불필요한 추임새는 절대 쓰지 마.
    - 말투만 "~했단다", "~하렴" (전문가 모드는 "~입니다")으로 유지해.

    [뉴스 리스트]
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
