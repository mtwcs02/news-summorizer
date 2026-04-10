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

# 🧠 뉴스 수집 및 요약 함수 (강력한 엄마 모드 버전)
@st.cache_data(ttl=60, show_spinner=False) # 테스트를 위해 기억 시간을 1분으로 확 줄였습니다!
def fetch_and_summarize(query, mode):
    # 구글 뉴스 검색
    q = query if query != "오늘의 주요 뉴스" else "대한민국 주요 뉴스 속보 when:1d"
    url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
    
    res = requests.get(url)
    items = BeautifulSoup(res.content, features="xml").find_all('item')[:10]
    
    if not items: 
        return None, []
    
    all_titles = "\n".join([f"- {i.title.text}" for i in items])
    
    # 👩‍👧 [핵심] 말투 지시사항을 더 독하게 수정
    if "초등" in mode:
        persona = "초등학생 자녀를 둔 다정한 엄마. 유치하지 않게 친구처럼 조곤조곤함."
        style = "안녕~ 우리 딸/아들! 오늘 이런 뉴스가 있네? / 그랬대요~ / 했단다."
    elif "중등" in mode:
        persona = "중학생 자녀와 대화하는 지적이고 다정한 엄마. 절대 아나운서 아님!"
        style = "오늘 이런 소식이 있더라~ / 이건 이런 뜻이야 / 했대요 / 인 것 같아."
    else:
        persona = "9시 뉴스 전문 여성 아나운서"
        style = "안녕하십니까 / 입니다 / 하시기 바랍니다."

    # 프롬프트를 AI가 거부할 수 없게 구조화
    prompt = f"""
    [너의 역할]
    너는 지금부터 {persona}야.
    
    [말투 규칙]
    반드시 다음 말투로만 대답해: "{style}"
    - '안녕하십니까', '9시 뉴스입니다', '보도해 드립니다' 같은 방송용 멘트는 절대 사용 금지.
    - 첫 문장은 반드시 "엄마가 뉴스 들려줄게~" 혹은 "오늘 이런 일이 있었대!" 로 시작해.
    
    [내용]
    다음 뉴스 제목들을 보고 핵심 내용 3가지를 친절하게 설명해줘.
    
    뉴스 리스트:
    {all_titles}
    """
    
    # 💡 팁: 동일 검색어 캐시 충돌을 피하기 위해 내부적으로 살짝 변화를 줌
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
