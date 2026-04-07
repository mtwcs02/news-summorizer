import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import edge_tts
import asyncio

# 1. 앱 설정
st.set_page_config(page_title="나만의 스마트 뉴스 비서", page_icon="🗞️", layout="wide")

with st.sidebar:
    st.header("⚙️ 맞춤 설정")
    level_mode = st.radio("요약 눈높이", ("초등학생용 🎒", "중학생용 📝", "전문가용 💼"), index=2)
    st.info("💡 1시간 동안 같은 뉴스는 AI가 기억해서 즉시 보여줍니다! (에러 방지)")

st.title("🗞️ AI 맞춤 뉴스 브리핑")

# 2. AI 모델 설정
@st.cache_resource
def get_working_model():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = next((m for m in available_models if 'gemini-1.5-flash' in m), None)
        if not target_model:
            target_model = next((m for m in available_models if 'gemini-pro' in m), available_models[0] if available_models else None)
        return genai.GenerativeModel(target_model) if target_model else None
    except Exception:
        return None

model = get_working_model()

# 3. 메뉴 구성
categories = ["오늘의 주요 뉴스", "정치", "경제", "사회"]
my_stocks = ["SGC에너지", "리플", "미국 증시", "비트코인"]

st.markdown("### 📍 빠른 선택")
cols = st.columns(4)
selected_keyword = ""
for i, cat in enumerate(categories):
    if cols[i].button(cat, key=f"cat_{i}", use_container_width=True): selected_keyword = cat

cols2 = st.columns(4)
for i, stock in enumerate(my_stocks):
    if cols2[i].button(stock, key=f"stock_{i}", use_container_width=True): selected_keyword = stock

st.divider()
user_input = st.text_input("🔍 직접 검색", value=selected_keyword)

# 🔊 음성 생성 함수
async def generate_speech(text, mode):
    voice = "ko-KR-SunHiNeural"
    rate = "-5%" if "전문가" not in mode else "+0%"
    pitch = "+2Hz" if "전문가" not in mode else "+0Hz"
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio": audio_data += chunk["data"]
    return audio_data

# --- 🧠 [핵심 근본 해결책] 기억력(캐시) 함수 ---
# 한 번 요약한 내용은 1시간(3600초) 동안 기억해두고, 구글에 다시 묻지 않습니다!
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_and_summarize(query, mode):
    q = query if query != "오늘의 주요 뉴스" else "대한민국 주요 뉴스 속보 when:1d"
    url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
    res = requests.get(url)
    items = BeautifulSoup(res.content, features="xml").find_all('item')[:10]
    
    if not items: return None, []
    
    all_titles = "\n".join([f"- {i.title.text}" for i in items])
    role = "자상한 이모" if "초등" in mode else ("선생님" if "중등" in mode else "여성 아나운서")
    prompt = f"너는 {role}야. 뉴스들을 읽고 3가지 핵심 내용을 풍성하게 요약해줘.\n\n{all_titles}"
    
    result = model.generate_content(prompt)
    
    # 요약된 텍스트와 원본 뉴스 데이터를 반환 (기억시킴)
    news_list = [{"title": i.title.text, "link": i.link.text} for i in items]
    return result.text, news_list

# 4. 실행 로직
if user_input and model:
    with st.spinner(f"'{user_input}' 정보를 가져오고 있습니다..."):
        try:
            # 기억된 결과가 있으면 즉시 꺼내오고, 없으면 구글에 물어봅니다.
            summary, news_data = fetch_and_summarize(user_input, level_mode)
            
            if summary:
                st.success(f"✅ {level_mode} 맞춤 요약 (1시간 내 재검색 시 즉시 표시됩니다)")
                st.markdown(summary)
                
                st.write("---")
                if st.button("🎧 음성 브리핑 듣기"):
                    with st.spinner("목소리를 입히는 중..."):
                        audio_bytes = asyncio.run(generate_speech(summary, level_mode))
                        st.audio(audio_bytes, format='audio/mp3')

                with st.expander("🔗 원본 뉴스 링크"):
                    for n in news_data:
                        st.markdown(f"- [{n['title']}]({n['link']})")
            else:
                st.warning("뉴스를 찾을 수 없습니다.")
        except Exception as e:
            st.error("🚨 구글 AI가 사용 한도를 초과했거나 바쁩니다. 잠시 후 다시 시도해주세요.")
elif not model:
    st.error("🚨 사용할 수 있는 AI 모델이 없습니다.")
