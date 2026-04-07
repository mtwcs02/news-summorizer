import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime
from gtts import gTTS # 🔊 음성 변환 라이브러리
import io

# 1. 앱 설정
st.set_page_config(page_title="나만의 스마트 뉴스 비서", page_icon="🗞️", layout="wide")

with st.sidebar:
    st.header("⚙️ 맞춤 설정")
    level_mode = st.radio("요약 눈높이", ("초등학생용 🎒", "중학생용 📝", "전문가용 💼"), index=2)
    st.write("---")
    st.write("💡 모드에 따라 AI의 말투와 목소리 느낌이 달라집니다.")

st.title("🗞️ AI 맞춤 뉴스 브리핑")

# 2. 🔐 AI 모델 설정
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
        queries = ["오늘의 주요 뉴스", "대한민국 주요 뉴스 1면", "오늘의 속보"]
    for q in queries:
        url = f"https://news.google.com/rss/search?q={q} when:1d&hl=ko&gl=KR&ceid=KR:ko"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, features="xml")
        items = soup.find_all('item')
        if items: return items[:10]
    return []

# 5. 실행 로직
if user_input:
    with st.spinner(f"'{user_input}' 정보를 분석 중입니다..."):
        items = get_news(user_input)
        if items:
            news_data = []
            for item in items:
                news_data.append({"title": item.title.text, "link": item.link.text})
            
            all_titles = "\n".join([f"- {n['title']}" for n in news_data])
            
            # [수정] 음성 지원을 위해 말투(Tone) 지시를 더 구체화했습니다.
            if "초등학생" in level_mode:
                system_role = "너는 아이들에게 뉴스를 들려주는 '자상한 이모'야. '안녕 친구들? 오늘 소식을 들려줄게'처럼 다정한 대화체로 3줄 요약해줘."
            elif "중학생" in level_mode:
                system_role = "너는 '다정한 선생님'이야. '학생들, 오늘은 이런 소식이 있단다'처럼 부드럽고 차분한 말투로 3줄 요약해줘."
            else:
                system_role = "너는 '여성 아나운서'야. '안녕하십니까, 오늘의 경제 브리핑입니다'처럼 신뢰감 있고 딱딱한 뉴스 톤으로 3줄 요약해줘."

            prompt = f"{system_role}\n\n키워드: {user_input}\n뉴스 목록:\n{all_titles}\n\n위 내용을 바탕으로 핵심 소식 3가지만 요약해줘."
            
            result = model.generate_content(prompt)
            summary_text = result.text # 요약된 텍스트 저장
            
            st.success(f"✅ {level_mode} 맞춤 요약 완료")
            st.markdown(summary_text)

            # 🔊 [새 기능] 음성 재생 버튼
            st.write("---")
            st.subheader("🎧 음성 브리핑 듣기")
            try:
                # 텍스트를 음성으로 변환
                tts = gTTS(text=summary_text, lang='ko')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp, format='audio/mp3')
                st.caption("위의 재생 버튼을 누르면 AI가 뉴스를 읽어줍니다.")
            except Exception as e:
                st.error("음성 변환 중 오류가 발생했습니다.")

            with st.expander("🔗 원본 뉴스 링크"):
                for n in news_data:
                    st.markdown(f"- [{n['title']}]({n['link']})")
        else:
            st.warning("최신 뉴스가 없습니다.")
