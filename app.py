import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime
import edge_tts  # 🔊 MS의 고품질 신경망 음성 도구
import asyncio
import io

# 1. 앱 설정
st.set_page_config(page_title="나만의 스마트 뉴스 비서", page_icon="🗞️", layout="wide")

with st.sidebar:
    st.header("⚙️ 맞춤 설정")
    level_mode = st.radio("요약 눈높이", ("초등학생용 🎒", "중학생용 📝", "전문가용 💼"), index=2)

st.title("🗞️ AI 맞춤 뉴스 브리핑")

# 2. AI 모델 설정
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
    model = genai.GenerativeModel(model_name)
except:
    st.error("API 설정을 확인해주세요.")
    st.stop()

# 3. 메뉴 구성
categories = ["오늘의 주요 뉴스", "정치", "경제", "사회"]
my_stocks = ["SGC에너지", "리플", "미국 증시", "비트코인"]

st.markdown("### 📍 빠른 선택")
cols = st.columns(4)
selected_keyword = ""
for i, cat in enumerate(categories):
    if cols[i].button(cat, use_container_width=True): selected_keyword = cat

cols2 = st.columns(4)
for i, stock in enumerate(my_stocks):
    if cols2[i].button(stock, use_container_width=True): selected_keyword = stock

st.divider()
user_input = st.text_input("🔍 직접 검색", value=selected_keyword)

# 4. 뉴스 수집 함수
def get_news(query):
    queries = [query]
    if query == "오늘의 주요 뉴스":
        queries = ["오늘의 주요 뉴스 1면 헤드라인", "대한민국 주요 소식 속보"]
    for q in queries:
        url = f"https://news.google.com/rss/search?q={q} when:1d&hl=ko&gl=KR&ceid=KR:ko"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, features="xml")
        items = soup.find_all('item')
        if items: return items[:10]
    return []

# 🔊 5. 사람 같은 음성 생성 함수 (MS Neural TTS)
async def generate_speech(text, mode):
    # 모드에 따라 목소리 톤을 조절 (SunHi는 맑고 전문적인 여성 목소리입니다)
    # 초등/중등용은 조금 더 부드럽게(pitch 조절), 전문가는 아나운서처럼 설정합니다.
    if "전문가" in mode:
        voice = "ko-KR-SunHiNeural"
        rate = "+0%"  # 정상 속도
        pitch = "+0Hz" # 정상 톤
    else:
        voice = "ko-KR-SunHiNeural"
        rate = "-5%"   # 조금 천천히 (자상하게)
        pitch = "+2Hz" # 조금 더 밝은 톤
        
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

# 6. 실행 로직
if user_input:
    with st.spinner(f"'{user_input}' 뉴스를 분석하고 목소리를 입히는 중입니다..."):
        try:
            items = get_news(user_input)
            if items:
                news_data = []
                for item in items:
                    news_data.append({"title": item.title.text, "link": item.link.text})
                
                all_titles = "\n".join([f"- {n['title']}" for n in news_data])
                
                # 프롬프트 설정 (말투 구체화)
                if "초등학생" in level_mode:
                    system_role = "너는 아이들을 사랑하는 자상한 이모야. '친구들 안녕?'으로 시작해서 아주 쉽고 따뜻한 말투로 요약해줘."
                elif "중학생" in level_mode:
                    system_role = "너는 학생들을 아끼는 다정한 선생님이야. '학생들 반가워요'로 시작해서 부드러운 말투로 요약해줘."
                else:
                    system_role = "너는 신뢰감 있는 여성 아나운서야. '안녕하십니까, 오늘의 뉴스 브리핑입니다'로 시작해서 전문적인 톤으로 요약해줘."

                prompt = f"{system_role}\n\n키워드: {user_input}\n뉴스 목록:\n{all_titles}\n\n위 내용을 바탕으로 핵심 3가지만 풍성하게 요약해줘."
                
                result = model.generate_content(prompt)
                summary_text = result.text
                
                st.success(f"✅ {level_mode} 맞춤 브리핑 완료")
                st.markdown(summary_text)

                # 🎧 음성 브리핑 (MS Neural TTS 적용)
                st.write("---")
                st.subheader("🎧 AI 음성 브리핑 (신경망 음성)")
                
                # 비동기 함수 실행을 위한 처리
                audio_bytes = asyncio.run(generate_speech(summary_text, level_mode))
                st.audio(audio_bytes, format='audio/mp3')
                st.caption(f"현재 목소리 스타일: {level_mode} (AI가 톤을 조절했습니다)")

                with st.expander("🔗 원본 뉴스 링크"):
                    for n in news_data:
                        st.markdown(f"- [{n['title']}]({n['link']})")
            else:
                st.warning("최신 뉴스를 찾을 수 없습니다.")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
