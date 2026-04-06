import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. 앱 화면 설정
st.set_page_config(page_title="나만의 뉴스 비서", page_icon="🤖")
st.title("🤖 나만의 AI 뉴스 비서")
st.write("오늘의 주요 소식을 AI가 깔끔하게 3줄 요약해 드립니다.")

# 2. 🔐 비밀 금고(Secrets)에서 API 키 가져오기
try:
    # 스트림릿 설정창에 넣은 이름과 똑같이 불러옵니다.
    GOOGLE_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # [수정] 가장 안정적인 'gemini-1.5-flash' 모델을 직접 지정합니다.
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("앗! API 키 설정에 문제가 있어요. 스트림릿 Secrets 설정을 다시 확인해 주세요.")
    st.stop()

# 3. 검색어 입력창 (기본값: SGC에너지)
keyword = st.text_input("궁금한 종목이나 키워드를 입력하세요", value="SGC에너지")

# 4. 실행 버튼 클릭 시 작동
if st.button("뉴스 요약 시작! 🔥"):
    if not keyword:
        st.warning("검색어를 입력해 주세요!")
    else:
        with st.spinner('뉴스를 읽고 분석하는 중입니다...'):
            try:
                # 구글 뉴스에서 정보 가져오기
                url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
                response = requests.get(url)
                soup = BeautifulSoup(response.content, features="xml")
                items = soup.find_all('item')
                
                if items:
                    # 상위 5개 뉴스 제목 합치기
                    news_list = [f"- {item.title.text}" for item in items[:5]]
                    all_titles = "\n".join(news_list)
                    
                    # AI에게 요약 부탁하기
                    prompt = f"다음 뉴스 제목들을 읽고 핵심 소식을 한글로 3줄 요약해줘:\n{all_titles}"
                    
                    # [중요] AI 실행
                    response = model.generate_content(prompt)
                    
                    # 결과 출력
                    st.success(f"✨ '{keyword}' 관련 주요 소식 요약 완료!")
                    st.info(response.text)
                else:
                    st.warning(f"'{keyword}'와 관련된 최신 뉴스를 찾을 수 없습니다.")
            except Exception as e:
                st.error(f"요약 중 오류가 발생했습니다: {e}")
