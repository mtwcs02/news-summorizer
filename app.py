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

# 👩‍👧 [지식 수준 세분화] 초4와 중1의 인지 수준에 딱 맞게!
    if "초등" in mode:
        # 초등학교 4학년 수준: 구체적 비유, 쉬운 단어 치환
        content_rule = """
        - 대상: 초등학교 4학년 (11살)
        - 지식 전달 방식: 어려운 한자어는 우리말 풀이로 바꿔줘. (예: '수입' -> '외국 물건을 사 오는 것')
        - 숫자 사용: 퍼센트(%)나 큰 수치는 '절반 정도', '조금' 같은 감각적인 표현으로 바꿔서 설명해줘.
        - 비유: 아이가 일상에서 경험하는 상황(학교, 마트, 용돈)에 빗대어 설명해줘.
        """
    elif "중등" in mode:
        # 중학교 1학년 수준: 시사 용어 입문, 논리적 인과관계
        content_rule = """
        - 대상: 중학교 1학년 (14살)
        - 지식 전달 방식: 교과서에 나오는 사회/경제 용어(환율, 금리, 인플레이션 등)는 그대로 사용하되, 반드시 그 뜻을 한 문장으로 친절하게 풀어서 배경지식을 쌓아줘.
        - 논리 구성: '이런 일이 생겨서 -> 우리 생활이 이렇게 바뀔 수 있단다' 처럼 사건의 원인과 결과를 논리적으로 연결해줘.
        - 수치 사용: 1.9%, 100억 달러 같은 구체적인 수치를 언급해 지식의 정확도를 높여줘.
        """
    else:
        content_rule = "- 전문가를 위한 핵심 정보 위주의 명확하고 객관적인 브리핑을 제공해줘."

    prompt = f"""
    [너의 역할]
    너는 자녀의 공부에 도움을 주는 지적인 '엄마'야. 뉴스 요약은 아래 규칙을 반드시 따라줘.
    
    [학년별 맞춤 지시]
    {content_rule}

    [군더더기 제거 규칙]
    - "우선 말이야", "그리고 또 말이야" 같은 불필요한 추임새는 절대 쓰지 마. 
    - 문장 시작마다 "그리고"를 붙이지 말고, 자연스럽게 다음 내용으로 넘어가줘.
    - 핵심만 담백하게 전달하되, 말투만 "~하단다", "~했대" 처럼 다정하게 유지해.

    [말투 가이드]
    1. 시작: "엄마가 오늘 뉴스 들려줄게." (간결하게)
    2. 번호(첫째, 둘째) 금지.
    3. 마침: "오늘 하루도 즐겁게 보내자!"

    [요약할 뉴스 리스트]
    {all_titles}
    """

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
