import streamlit as st
import pandas as pd
import requests

# 페이지 기본 설정
st.set_page_config(
    page_title="Football Scouting & Agency Management",
    page_icon="⚽",
    layout="wide"
)

# PDF 생성 관련 라이브러리 안전 로드 (에러 방지)
PDF_AVAILABLE = True
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttffonts import TTFont
except ImportError:
    PDF_AVAILABLE = False

# 앱 타이틀
st.title("⚽ Football Scouting & Agency Management")
st.markdown("---")

# 사이드바 메뉴 구성
menu = st.sidebar.selectbox(
    "메뉴 선택",
    ["홈 및 대시보드", "선수 검색 및 관찰 일지", "에이전시 클라이언트 관리", "선수 프로필 PDF 생성"]
)

# 1. 홈 및 대시보드
if menu == "홈 및 대시보드":
    st.header("📌 스카우팅 및 에이전시 통합 대시보드")
    st.info("환영합니다! 좌측 메뉴에서 원하는 기능을 선택하여 선수 관찰 일지와 에이전시 클라이언트를 관리하세요.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="등록된 선수 데이터", value="0명")
    with col2:
        st.metric(label="작성된 관찰 일지", value="0건")
    with col3:
        st.metric(label="관리 중인 에이전시 클라이언트", value="0명")

# 2. 선수 검색 및 관찰 일지
elif menu == "선수 검색 및 관찰 일지":
    st.header("🔍 선수 검색 및 관찰 일지 작성")
    
    search_keyword = st.text_input("팀명 또는 선수 이름, 백넘버로 검색하세요", placeholder="예: 안양, 10번")
    
    st.markdown("### 관찰 일지 입력")
    with st.form("observation_form"):
        col1, col2 = st.columns(2)
        with col1:
            team_name = st.text_input("소속 팀명")
            player_name = st.text_input("선수 이름")
            back_number = st.text_number = st.text_input("등번호 (Back Number)")
        with col2:
            position = st.selectbox("포지션", ["FW", "MF", "DF", "GK"])
            match_date = st.date_input("관찰 경기일")
            
        memo = st.text_area("스카우팅 평가 및 메모", placeholder="선수의 장단점, 피지컬, 전술 이해도 등 작성")
        submitted = st.form_submit_button("일지 저장하기")
        
        if submitted:
            st.success(f"[{team_name}] {player_name} 선수의 관찰 일지가 성공적으로 기록되었습니다!")

# 3. 에이전시 클라이언트 관리
elif menu == "에이전시 클라이언트 관리":
    st.header("🤝 에이전시 클라이언트 관리")
    st.write("소속 선수 및 계약 관리 대상 프로필을 등록하고 수정합니다.")
    
    with st.form("client_form"):
        c_name = st.text_input("클라이언트 선수 이름")
        c_birth = st.text_input("생년월일 (예: 2000-01-01)")
        c_club = st.text_input("현재 소속팀")
        c_contract = st.date_input("계약 만료일")
        
        c_submit = st.form_submit_button("클라이언트 등록")
        if c_submit:
            st.success(f"{c_name} 클라이언트 프로필이 추가되었습니다.")

# 4. 선수 프로필 PDF 생성
elif menu == "선수 프로필 PDF 생성":
    st.header("📄 선수 프로필 및 CV PDF 다운로드")
    
    if not PDF_AVAILABLE:
        st.warning("⚠️ 현재 서버 환경에 ReportLab 라이브러리가 설치되지 않아 PDF 다운로드 기능이 제한될 수 있습니다. (기본 화면은 정상 작동합니다)")
    
    target_player = st.text_input("PDF로 출력할 선수 이름 입력")
    
    if st.button("PDF 프로필 생성하기"):
        if target_player:
            st.success(f"{target_player} 선수의 프로필 PDF 생성 준비 완료되었습니다.")
            # PDF 생성 로직 자리
        else:
            st.warning("선수 이름을 입력해주세요.")
