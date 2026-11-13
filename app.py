import streamlit as st
import pandas as pd
import requests
import io
import re
import os
import base64
from datetime import datetime

# 페이지 기본 설정
st.set_page_config(page_title="선수 스카우팅 DB", page_icon="⚽", layout="wide")

# ----------------------------------------------------
# 📱 PC & 모바일 반응형 최적화 스타일 설정
# ----------------------------------------------------
st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 2.5rem !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        padding: 14px 18px !important;
        margin-bottom: 10px !important;
        border-radius: 12px;
        background-color: rgba(255, 255, 255, 0.08);
        cursor: pointer;
    }
    
    div[data-testid="stNumberInput"] button {
        display: none !important;
    }
    div[data-testid="stNumberInput"] input {
        text-align: center !important;
        padding: 4px 6px !important;
        font-weight: bold !important;
    }

    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            min-width: 290px !important;
            max-width: 330px !important;
        }
        [data-testid="stSidebar"] .stRadio label p {
            font-size: 18px !important;
            font-weight: 700 !important;
        }
        [data-testid="stSidebar"] button {
            padding: 14px 18px !important;
            font-size: 17px !important;
        }
        h1 {
            font-size: 19px !important;
            margin-top: 5px !important;
            margin-bottom: 12px !important;
        }
        h2 {
            font-size: 17px !important;
            margin-top: 8px !important;
            margin-bottom: 10px !important;
            word-break: keep-all !important;
        }
        h3 {
            font-size: 14px !important;
            word-break: keep-all !important;
        }
        [data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 4px !important;
        }
        [data-testid="stHorizontalBlock"] > div {
            flex: 1 !important;
            min-width: 0 !important;
        }
    }
    @media (min-width: 769px) {
        [data-testid="stSidebar"] {
            min-width: 260px;
            max-width: 300px;
        }
        [data-testid="stSidebar"] .stRadio label p {
            font-size: 15px !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# 🔗 1. 구글 시트 공유 링크
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1WSbVkwCr5Dv5hN3zU0Bw5tzzbNjMmlFyZiOCpG5DRjI/edit?usp=sharing"

# 🔗 2. 구글 Apps Script 웹앱 URL
GOOGLE_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxTTvgJqNnmBxwuCGvT3agMEo0_0Fon0JGWdREyR7usEIu4Mfw9M1lq66njtr8S_cbP/exec"

STATUS_OPTIONS = ["관심 선수 (Watchlist)", "집중 관찰 중", "컨택 완료", "계약 검토", "보류 / 제외"]
POSITION_OPTIONS = ["GK", "CB", "LCB", "RCB", "LB", "RB", "MF", "LW", "RW", "CF"]

# ⚽ 대한민국 주요 고등/대학/프로 U18 축구팀 기본 마스터 리스트
DEFAULT_TEAM_MASTER_LIST = [
    "매탄고", "보인고", "현대고", "오산고", "금호고", "포항제철고", "영생고", "개성고", "충남기계공고", "진주고", 
    "광양제철고", "풍생고", "전주영생고", "서울이랜드 U18", "안산그리너스 U18", "FC안양 U18", "부천FC1995 U18", 
    "성남FC U18", "수원FC U18", "충남아산 U18", "경남FC U18", "부산아이파크 U18", "대구FC U18", "강원FC U18",
    "제주유나이티드 U18", "전북현대 U18", "울산현대 U18", "포항스틸러스 U18", "수원삼성 U18", "FC서울 U18",
    "인천유나이티드 U18", "용인시축구센터 U18", "천안제일고", "신평고", "중앙고", "배재고", "동북고", "언남고",
    "장흥고", "과천고", "평택진위FC U18", "FC한양 U18", "서울디지털대", "고려대", "연세대", "용인대", "선문대",
    "인천대", "한남대", "광운대", "단국대", "중앙대", "수원대", "아주대", "경희대", "한국체대", "상지대", "청주대"
]

# ----------------------------------------------------
# 🏢 성문컴퍼니(SMC) 로고 HTML 렌더링
# ----------------------------------------------------
def display_logo():
    logo_html = """
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; padding: 10px 0 20px 0; margin-bottom: 10px;">
        <div style="color: #007bff; font-weight: 900; letter-spacing: 4px; font-size: 32px; font-family: sans-serif; line-height: 1.1;">SMC</div>
        <div style="color: #6c757d; font-weight: 700; letter-spacing: 4px; font-size: 11px; font-family: sans-serif; margin-top: 5px;">SUNGMUN COMPANY</div>
    </div>
    """
    st.sidebar.markdown(logo_html, unsafe_allow_html=True)
    st.markdown(logo_html, unsafe_allow_html=True)

def calculate_age(born_date):
    today = datetime.today()
