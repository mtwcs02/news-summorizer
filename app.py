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

# 2. 🔐 AI 모델 설정 (404 에러 방지용)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 404 에러를 피하기 위해 가장 표준적인 모델 이름을 사용합니다.
    # 'models/'를 붙이지 않고 호출해보고, 안되면 목록에서 찾아내는 방식입니다.
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"AI 연결 설정 중 오류: {e}")
    st.stop()

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

# 4. 실행 로직
if user_input:
    with st.spinner(f"'{user_input}' 정보를 심층 분석 중입니다..."):
        try:
            # 뉴스 가져오기
            q = user_input if user_input != "오늘의 주요 뉴스" else "대한민국 주요 뉴스 속보 when:1d"
            url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(url)
            items = BeautifulSoup(res.content, features="xml").find_all('item')[:10]
            
            if items:
                all_titles = "\n".join([f"- {i.title.text}" for i in items])
                
                # 프롬프트 설정 (풍성한 요약 버전)
                role = "자상한 이모" if "초등" in level_mode else ("선생님" if "중등" in level_mode else "여성 아나운서")
                prompt = f"너는 {role}야. 키워드 '{user_input}'에 대한 뉴스 {len(items)}개를 읽고 3가지 핵심 내용을 풍성하게 요약해줘."
                
                # AI 실행 (여기서 에러가 날 확률이 높으므로 한 번 더 감쌉니다)
                try:
                    result = model.generate_content(prompt)
                    summary = result.text
                except:
                    # 'gemini-1.5-flash'가 안되면 'gemini-pro'로 재시도
                    alt_model = genai.GenerativeModel('gemini-pro')
                    result = alt_model.generate_content(prompt)
                    summary = result.text
                
                st.success(f"✅ {level_mode} 맞춤 요약 완료")
                st.markdown(summary)
                
                st.write("---")
                if st.button("🎧 음성 브리핑 듣기 (사람 같은 목소리)"):
                    with st.spinner("목소리를 입히는 중..."):
                        audio_bytes = asyncio.run(generate_speech(summary, level_mode))
                        st.audio(audio_bytes, format='audio/mp3')

                with st.expander("🔗 참고한 뉴스 원본 보기"):
                    for i in items:
                        st.markdown(f"- [{i.title.text}]({i.link.text})")
            else:
                st.warning("뉴스를 찾을 수 없습니다.")
        except Exception as e:
            if "429" in str(e):
                st.error("🚨 구글 AI가 잠시 쉬고 싶어 하네요! 1분만 기다렸다가 다시 시도해 주세요.")
            else:
                st.error(f"오류가 발생했습니다: {e}")
