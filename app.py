import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime
import edge_tts
import asyncio
import io

# 1. 앱 설정
st.set_page_config(page_title="나만의 스마트 뉴스 비서", page_icon="🗞️", layout="wide")

with st.sidebar:
    st.header("⚙️ 맞춤 설정")
    level_mode = st.radio("요약 눈높이", ("초등학생용 🎒", "중학생용 📝", "전문가용 💼"), index=2)
    st.info("💡 속도를 위해 음성은 버튼을 누를 때만 생성됩니다.")

st.title("🗞️ AI 맞춤 뉴스 브리핑")

# 2. 🔐 [핵심 수정] 사용할 수 있는 모델 이름을 직접 찾아내기 (404 방지)
@st.cache_resource
def get_working_model():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 현재 이 API 키로 쓸 수 있는 모든 모델 목록을 가져옵니다.
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 1순위: 가장 빠르고 최신인 flash 모델 찾기
        target_model = None
        for name in available_models:
            if 'gemini-1.5-flash' in name:
                target_model = name
                break
        
        # 2순위: flash가 없으면 pro 모델 찾기
        if not target_model:
            for name in available_models:
                if 'gemini-pro' in name or 'gemini-1.5-pro' in name:
                    target_model = name
                    break
        
        # 3순위: 그것도 없으면 사용 가능한 아무 모델이나 선택
        if not target_model and available_models:
            target_model = available_models[0]
            
        if target_model:
            return genai.GenerativeModel(target_model)
        return None
    except Exception as e:
        st.error(f"AI 모델 목록을 가져오는 중 오류: {e}")
        return None

# AI 두뇌 준비
model = get_working_model()

# 3. 메뉴 및 버튼 구성
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

# 4. 실행 로직
if user_input and model:
    with st.spinner(f"'{user_input}' 정보를 심층 분석 중입니다..."):
        try:
            # 뉴스 가져오기
            q = user_input if user_input != "오늘의 주요 뉴스" else "대한민국 주요 뉴스 속보 when:1d"
            url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(url)
            items = BeautifulSoup(res.content, features="xml").find_all('item')[:10]
            
            if items:
                all_titles = "\n".join([f"- {i.title.text}" for i in items])
                role = "자상한 이모" if "초등" in level_mode else ("선생님" if "중등" in level_mode else "여성 아나운서")
                prompt = f"너는 {role}야. 뉴스들을 읽고 3가지 핵심 내용을 풍성하게 요약해줘.\n\n{all_titles}"
                
                # AI 요약 실행
                result = model.generate_content(prompt)
                summary = result.text
                
                st.success(f"✅ {level_mode} 맞춤 요약 완료")
                st.markdown(summary)
                
                st.write("---")
                if st.button("🎧 음성 브리핑 듣기"):
                    with st.spinner("목소리를 입히는 중..."):
                        audio_bytes = asyncio.run(generate_speech(summary, level_mode))
                        st.audio(audio_bytes, format='audio/mp3')

                with st.expander("🔗 원본 뉴스 링크"):
                    for i in items:
                        st.markdown(f"- [{i.title.text}]({i.link.text})")
            else:
                st.warning("뉴스를 찾을 수 없습니다.")
        except Exception as e:
            if "429" in str(e):
                st.error("🚨 구글 AI가 너무 바쁘대요! 1분만 기다렸다가 다시 눌러주세요.")
            else:
                st.error(f"오류가 발생했습니다: {e}")
elif not model:
    st.error("🚨 사용할 수 있는 AI 모델이 없습니다. API 키를 다시 확인해주세요.")
