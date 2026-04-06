import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 앱 화면 설정
st.set_page_config(page_title="나만의 뉴스 비서", page_icon="🤖")
st.title("🤖 나만의 AI 뉴스 비서")
st.write("오늘의 주요 소식을 AI가 요약해 드립니다.")

# 🔑 API 키 설정 (사용자님의 키를 넣어주세요)
GOOGLE_API_KEY = "AIzaSyB7HNe_EoIzzMErO687P4naCYOdUSZFzuU"
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 검색어 입력창
keyword = st.text_input("궁금한 종목이나 키워드를 입력하세요", value="SGC에너지")

if st.button("뉴스 요약 시작! 🔥"):
    with st.spinner('뉴스를 읽고 요약 중입니다...'):
        # 뉴스 가져오기
        url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, features="xml")
        items = soup.find_all('item')
        
        if items:
            all_titles = "\n".join([f"- {item.title.text}" for item in items[:5]])
            prompt = f"다음 뉴스 제목들을 읽고 핵심 내용을 한글로 3줄 요약해줘:\n{all_titles}"
            
            # AI 요약 실행
            result = model.generate_content(prompt)
            st.success("요약 완료!")
            st.info(result.text)
        else:
            st.warning("관련 뉴스를 찾지 못했습니다.")
