import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import edge_tts
import asyncio

# 1. 앱 설정
st.set_page_config(page_title="나만의 스마트 뉴스 비서", page_icon="🗞️", layout="wide")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 맞춤 설정")
    level_mode = st.radio("요약 눈높이", ("초등학생용 🎒", "중학생용 📝", "전문가용 💼"), index=2)
    st.info("💡 실시간 뉴스 요약! (엄마뉴스)")

st.title("🗞️ AI 맞춤 뉴스 브리핑")

# 2. AI 모델 설정 (사진에서 찾은 진짜 최신 모델 이름 적용!)
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    # 드디어 찾은 진짜 이름!
    model = genai.GenerativeModel('gemini-2.0-flash')
except Exception as e:
    st.error(f"⚠️ API 키 설정 오류: {e}")
    model = None

# 3. 메뉴 구성
categories = ["오늘의 주요 뉴스", "정치", "경제", "사회"]
my_stocks = ["SGC에너지", "리플", "미국 증시", "비트코인"]

st.markdown("### 📍 빠른 선택")
cols = st.columns(4)
selected_keyword = ""
for i, cat in enumerate(categories):
    if cols[i].button(cat, key=f"cat_{i}", use_container_width=True): 
        selected_keyword = cat

cols2 = st.columns(4)
for i, stock in enumerate(my_stocks):
    if cols2[i].button(stock, key=f"stock_{i}", use_container_width=True): 
        selected_keyword = stock

st.divider()
user_input = st.text_input("🔍 직접 검색 (검색어를 입력하고 엔터를 치세요)", value=selected_keyword)

# 🔊 음성 생성 함수
async def generate_speech(text, mode):
    voice = "ko-KR-SunHiNeural"
    rate = "-5%" if "전문가" not in mode else "+0%"
    pitch = "+2Hz" if "전문가" not in mode else "+0Hz"
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio": 
            audio_data += chunk["data"]
    return audio_data

# 🧠 뉴스 수집 및 요약 함수
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_and_summarize(query, mode):
    q = query if query != "오늘의 주요 뉴스" else "대한민국 주요 뉴스 속보 when:1d"
    url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
    
    res = requests.get(url)
    items = BeautifulSoup(res.content, features="xml").find_all('item')[:10]
    
    if not items: 
        return None, []
    
    all_titles = "\n".join([f"- {i.title.text}" for i in items])
    
    role = "자상한 이모" if "초등" in mode else ("선생님" if "중등" in mode else "여성 아나운서")
    prompt = f"""
    너는 {role}야. 다음 뉴스 제목들을 보고 {mode} 눈높이에 맞춰서 
    오늘의 핵심 내용을 3가지 포인트로 풍성하고 친절하게 요약해줘.
    
    뉴스 리스트:
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
                if st.button("🎧 음성 브리핑 듣기"):
                    with st.spinner("목소리를 입히는 중..."):
                        audio_bytes = asyncio.run(generate_speech(summary, level_mode))
                        st.audio(audio_bytes, format='audio/mp3')

                with st.expander("🔗 참고한 뉴스 원본 링크"):
                    for n in news_data:
                        st.markdown(f"- [{n['title']}]({n['link']})")
            else:
                st.warning("관련 뉴스를 찾을 수 없어요. 다른 검색어를 입력해 보세요.")
                
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
