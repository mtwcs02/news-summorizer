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

# 2. 🔐 [3중 안전장치] AI 모델 설정
def generate_with_fallback(prompt):
    # 사용할 모델 후보들
    model_names = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    
    for name in model_names:
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel(name)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            # 429(바쁨) 에러가 나면 다음 모델로 넘어갑니다.
            if "429" in str(e):
                continue
            else:
                raise e
    return None

# 3. 메뉴 및 버튼
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
if user_input:
    with st.spinner(f"'{user_input}' 정보를 분석 중입니다..."):
        try:
            # 뉴스 가져오기
            q = user_input if user_input != "오늘의 주요 뉴스" else "대한민국 주요 뉴스 속보 when:1d"
            url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(url)
            items = BeautifulSoup(res.content, features="xml").find_all('item')[:10]
            
            if items:
                all_titles = "\n".join([f"- {i.title.text}" for i in items])
                role = "자상한 이모" if "초등" in level_mode else ("선생님" if "중등" in level_mode else "여성 아나운서")
                prompt = f"너는 {role}야. 키워드 '{user_input}' 뉴스들을 읽고 3가지 핵심을 풍성하게 요약해줘.\n\n{all_titles}"
                
                # [핵심] 여러 모델 중 가능한 것을 찾아 요약
                summary = generate_with_fallback(prompt)
                
                if summary:
                    st.success(f"✅ {level_mode} 맞춤 요약 완료")
                    st.markdown(summary)
                    
                    st.write("---")
                    if st.button("🎧 음성 브리핑 듣기"):
                        with st.spinner("목소리를 입히는 중..."):
                            audio_bytes = asyncio.run(generate_speech(summary, level_mode))
                            st.audio(audio_bytes, format='audio/mp3')

                    with st.expander("🔗 참고한 뉴스 원본 보기"):
                        for i in items:
                            st.markdown(f"- [{i.title.text}]({i.link.text})")
                else:
                    st.error("🚨 모든 AI 모델이 현재 바쁩니다. 잠시 후 다시 시도해 주세요.")
            else:
                st.warning("뉴스를 찾을 수 없습니다.")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
