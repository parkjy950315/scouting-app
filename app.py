import streamlit as st
import pandas as pd
import requests
import io
import re
import os
import base64
from datetime import datetime

# PDF 생성을 위한 reportlab 라이브러리 및 폰트 등록 모듈
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 페이지 기본 설정
st.set_page_config(page_title="선수 스카우팅 DB", page_icon="⚽", layout="wide")

# ----------------------------------------------------
# 🔤 PDF 한글 폰트 자동 등록 함수
# ----------------------------------------------------
def register_korean_font():
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        try:
            font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
            r = requests.get(font_url)
            if r.status_code == 200:
                with open(font_path, "wb") as f:
                    f.write(r.content)
        except Exception:
            pass
            
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('NanumGothic', font_path))
        return 'NanumGothic'
    return 'Helvetica'

# ----------------------------------------------------
# 📱 PC & 모바일 최적화 스타일 설정 (모바일에서도 입력칸이 세로로 찌그러지지 않고 가로 배치되도록 강제)
# ----------------------------------------------------
st.markdown("""
    <style>
    .block-container {
        padding-top: 2.5rem !important;
        padding-bottom: 3rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
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
    
    /* 모바일 환경에서도 st.columns가 세로로 떨어지지 않고 그라운드처럼 가로 나열되도록 유지 */
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
            font-size: 22px !important;
            margin-top: 5px !important;
            margin-bottom: 15px !important;
        }
        /* 컬럼들을 강제로 가로 배치 유지 및 패딩 조절 */
        [data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
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
    if not born_date:
        return "", ""
    today = datetime.today()
    age_full = today.year - born_date.year - ((today.month, today.day) < (born_date.month, born_date.day))
    age_year = today.year - born_date.year
    return f"만 {age_full}세", f"{age_year}세"

def parse_date(date_str):
    try:
        if pd.isna(date_str) or not date_str:
            return datetime(2005, 1, 1)
        if isinstance(date_str, datetime):
            return date_str
        return datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
    except Exception:
        return datetime(2005, 1, 1)

def get_csv_export_url(sheet_url):
    if "/edit" in sheet_url:
        return sheet_url.split("/edit")[0] + "/gviz/tq?tqx=out:csv"
    return sheet_url

# 🛡️ 구글 시트 데이터 로드 및 컬럼 완벽 매핑 함수
def load_data():
    expected_cols = [
        "선수명", "소속팀", "등번호", "포지션", "생년월일", "만 나이", "연 나이", "주발", "신장(cm)", "체중(kg)",
        "진행 상태", "장점/특기", "보완점/단점", "종합 평가", "작성일자"
    ]
    try:
        base_csv_url = get_csv_export_url(GOOGLE_SHEET_URL)
        import time
        csv_url = f"{base_csv_url}&t={int(time.time())}" if "?" in base_csv_url else f"{base_csv_url}?t={int(time.time())}"
        
        df = pd.read_csv(csv_url, dtype=str)
        
        rename_map = {}
        for col in df.columns:
            clean_col = str(col).strip().replace(" ", "").lower()
            if any(k in clean_col for k in ["종합평가", "코멘트", "오버롤", "평가"]):
                rename_map[col] = "종합 평가"
            elif any(k in clean_col for k in ["장점", "특기"]):
                rename_map[col] = "장점/특기"
            elif any(k in clean_col for k in ["보완점", "단점", "약점"]):
                rename_map[col] = "보완점/단점"
            elif "선수" in clean_col:
                rename_map[col] = "선수명"
            elif "소속" in clean_col:
                rename_map[col] = "소속팀"
            elif "포지션" in clean_col:
                rename_map[col] = "포지션"
            elif "상태" in clean_col:
                rename_map[col] = "진행 상태"
                
        if rename_map:
            df = df.rename(columns=rename_map)

        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        df = df[expected_cols].fillna("")
    except Exception:
        df = pd.DataFrame(columns=expected_cols)
        
    for col in expected_cols:
        df[col] = df[col].astype(str).str.replace('.0', '', regex=False).replace(['nan', 'None', 'nat', 'NaT', ''], '')
            
    return df.astype(str)

def save_data_to_sheet(df):
    try:
        expected_cols = [
            "선수명", "소속팀", "등번호", "포지션", "생년월일", "만 나이", "연 나이", "주발", "신장(cm)", "체중(kg)",
            "진행 상태", "장점/특기", "보완점/단점", "종합 평가", "작성일자"
        ]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        df_clean = df[expected_cols].fillna("").astype(str)
        
        headers = expected_cols
        rows = []
        for _, row in df_clean.iterrows():
            row_list = [str(row[col]) if pd.notna(row[col]) and str(row[col]).lower() != 'nan' else "" for col in expected_cols]
            rows.append(row_list)
            
        data_to_send = [headers] + rows
        
        if GOOGLE_WEBAPP_URL and "여기에" not in GOOGLE_WEBAPP_URL:
            res = requests.post(GOOGLE_WEBAPP_URL, json=data_to_send)
            if res.status_code == 200:
                st.session_state['data_cache'] = df_clean
                return True
            else:
                st.error("구글 시트 저장 서버 응답 실패.")
                return False
        else:
            st.warning("⚠️ 구글 웹앱 URL이 설정되지 않았습니다.")
            return False
    except Exception as e:
        st.error(f"저장 중 오류 발생: {e}")
        return False

def parse_team_info(team_str):
    if not team_str or pd.isna(team_str):
        return "-", ""
    team_str = str(team_str).strip()
    if "(전:" in team_str:
        parts = team_str.split("(전:")
        current_team = parts[0].strip()
        past_teams = "(전:" + parts[1]
        return current_team, past_teams
    return team_str, ""

# ----------------------------------------------------
# 📄 PDF 보고서 생성 함수 (선수용)
# ----------------------------------------------------
def generate_pdf_report(player_data):
    korean_font = register_korean_font()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        rightMargin=36, 
        leftMargin=36, 
        topMargin=36, 
        bottomMargin=36
    )
    story = []
    
    PRIMARY_COLOR = colors.HexColor('#0F172A')
    TEXT_COLOR = colors.HexColor('#334155')
    BG_LIGHT = colors.HexColor('#F8FAFC')
    BORDER_COLOR = colors.HexColor('#CBD5E1')

    title_style = ParagraphStyle('TitleStyle', fontName=korean_font, fontSize=16, leading=20, alignment=0, textColor=PRIMARY_COLOR)
    header_date = ParagraphStyle('HeaderDate', fontName=korean_font, fontSize=8.5, leading=11, alignment=2, textColor=colors.HexColor('#64748B'))
    
    section_title_style = ParagraphStyle('SectionTitle', fontName=korean_font, fontSize=10, leading=14, alignment=0, textColor=PRIMARY_COLOR)
    body_style = ParagraphStyle('BodyStyle', fontName=korean_font, fontSize=9.5, leading=14, alignment=0, textColor=TEXT_COLOR)
    
    table_label = ParagraphStyle('TableLabel', fontName=korean_font, fontSize=8.5, leading=11, alignment=0, textColor=colors.HexColor('#64748B'))
    table_value = ParagraphStyle('TableValue', fontName=korean_font, fontSize=9, leading=12, alignment=0, textColor=PRIMARY_COLOR)

    header_data = [
        [Paragraph("<b>SMC SCOUTING REPORT</b>", title_style), Paragraph(f"<b>발급일:</b> {datetime.today().strftime('%Y-%m-%d')}", header_date)]
    ]
    header_table = Table(header_data, colWidths=[350, 170])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BOTTOMPADDING', (0,0), (-1,-1), 6)]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY_COLOR, spaceAfter=12))

    curr_team, past_team = parse_team_info(player_data.get('소속팀', ''))
    full_team = f"{curr_team} {past_team}".strip()
    weight_val = f"{player_data.get('체중(kg)')}kg" if player_data.get('체중(kg)') else "미입력"
    
    profile_data = [
        [Paragraph("선수명", table_label), Paragraph(f"<b>{player_data.get('선수명', '-')}</b>", table_value), Paragraph("포지션 / 등번호", table_label), Paragraph(f"<b>{player_data.get('포지션', '-')} / {player_data.get('등번호', '-')}번</b>", table_value)],
        [Paragraph("현재 소속팀", table_label), Paragraph(f"{curr_team}", table_value), Paragraph("진행 상태", table_label), Paragraph(f"<font color='#2563EB'><b>{player_data.get('진행 상태', '-')}</b></font>", table_value)],
        [Paragraph("소속팀 이력", table_label), Paragraph(f"{full_team}", table_value), Paragraph("주발", table_label), Paragraph(f"{player_data.get('주발', '-')}", table_value)],
        [Paragraph("생년월일 (나이)", table_label), Paragraph(f"{player_data.get('생년월일', '-')} ({player_data.get('만 나이', '-')})", table_value), Paragraph("피지컬 (신장/체중)", table_label), Paragraph(f"{player_data.get('신장(cm)', '-')}cm / {weight_val}", table_value)],
        [Paragraph("최근 관찰일자", table_label), Paragraph(f"{player_data.get('작성일자', '-')}", table_value), Paragraph("문서 보안", table_label), Paragraph("CONFIDENTIAL", table_value)]
    ]
    
    profile_table = Table(profile_data, colWidths=[90, 170, 90, 170])
    profile_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT), ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR), ('PADDING', (0,0), (-1,-1), 6), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(profile_table)
    story.append(Spacer(1, 14))

    def add_modern_card(title, content, accent_hex):
        story.append(Spacer(1, 4))
        cleaned_content = str(content).replace('\n', '<br/>') if content and str(content).strip() else "작성된 관찰 내용이 없습니다."
        card_data = [[Paragraph(f"<b>{title}</b>", section_title_style)], [Paragraph(cleaned_content, body_style)]]
        card_table = Table(card_data, colWidths=[520])
        card_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')), ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#FFFFFF')),
            ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR), ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor(accent_hex)),
            ('TOPPADDING', (0,0), (-1,-1), 7), ('BOTTOMPADDING', (0,0), (-1,-1), 7), ('LEFTPADDING', (0,0), (-1,-1), 12), ('RIGHTPADDING', (0,0), (-1,-1), 12)
        ]))
        story.append(card_table)
        story.append(Spacer(1, 8))

    add_modern_card("장점 및 주요 특기 (PROS)", player_data.get('장점/특기', ''), '#2563EB')
    add_modern_card("보완점 및 약점 (CONS)", player_data.get('보완점/단점', ''), '#D97706')
    add_modern_card("스카우터 종합 평가 및 코멘트 (OVERALL EVALUATION)", player_data.get('종합 평가', ''), '#475569')

    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceAfter=6))
    footer_style = ParagraphStyle('FooterStyle', fontName=korean_font, fontSize=8, leading=10, alignment=1, textColor=colors.HexColor('#94A3B8'))
    story.append(Paragraph("SUNGMUN COMPANY — Professional Player Scouting Database System", footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer

# ----------------------------------------------------
# 📄 경기 관찰 일지용 PDF 보고서 생성 함수
# ----------------------------------------------------
def generate_pdf_report_for_memo(row_data):
    korean_font = register_korean_font()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    PRIMARY_COLOR = colors.HexColor('#0F172A')
    TEXT_COLOR = colors.HexColor('#334155')
    BG_LIGHT = colors.HexColor('#F8FAFC')
    BORDER_COLOR = colors.HexColor('#CBD5E1')

    title_style = ParagraphStyle('TitleStyle', fontName=korean_font, fontSize=15, leading=18, alignment=0, textColor=PRIMARY_COLOR)
    header_date = ParagraphStyle('HeaderDate', fontName=korean_font, fontSize=8.5, leading=11, alignment=2, textColor=colors.HexColor('#64748B'))
    section_title_style = ParagraphStyle('SectionTitle', fontName=korean_font, fontSize=10, leading=14, alignment=0, textColor=PRIMARY_COLOR)
    body_style = ParagraphStyle('BodyStyle', fontName=korean_font, fontSize=9.5, leading=14, alignment=0, textColor=TEXT_COLOR)
    table_label = ParagraphStyle('TableLabel', fontName=korean_font, fontSize=8.5, leading=11, alignment=0, textColor=colors.HexColor('#64748B'))
    table_value = ParagraphStyle('TableValue', fontName=korean_font, fontSize=9, leading=12, alignment=0, textColor=PRIMARY_COLOR)

    raw_match_title = row_data.get('선수명', '경기 기록')
    match_title = re.sub(r' \(타임:\d+\)', '', str(raw_match_title))
    match_date = row_data.get('작성일자', '-')
    match_teams = row_data.get('소속팀', '-')

    header_data = [[Paragraph(f"<b>SMC MATCH REPORT</b>", title_style), Paragraph(f"<b>관찰일자:</b> {match_date}", header_date)]]
    header_table = Table(header_data, colWidths=[350, 170])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BOTTOMPADDING', (0,0), (-1,-1), 6)]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY_COLOR, spaceAfter=12))

    profile_data = [
        [Paragraph("경기/대회명", table_label), Paragraph(f"<b>{match_title}</b>", table_value)],
        [Paragraph("대진 정보", table_label), Paragraph(f"{match_teams}", table_value)],
        [Paragraph("기록 분류", table_label), Paragraph("현장 경기 관찰 일지 (CONFIDENTIAL)", table_value)]
    ]
    
    profile_table = Table(profile_data, colWidths=[100, 420])
    profile_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT), ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR), ('PADDING', (0,0), (-1,-1), 6), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(profile_table)
    story.append(Spacer(1, 14))

    def add_modern_card(title, content, accent_hex):
        story.append(Spacer(1, 4))
        cleaned_content = str(content).replace('\n', '<br/>') if content and str(content).strip() else "작성된 내용이 없습니다."
        card_data = [[Paragraph(f"<b>{title}</b>", section_title_style)], [Paragraph(cleaned_content, body_style)]]
        card_table = Table(card_data, colWidths=[520])
        card_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')), ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#FFFFFF')),
            ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR), ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor(accent_hex)),
            ('TOPPADDING', (0,0), (-1,-1), 7), ('BOTTOMPADDING', (0,0), (-1,-1), 7), ('LEFTPADDING', (0,0), (-1,-1), 12), ('RIGHTPADDING', (0,0), (-1,-1), 12)
        ]))
        story.append(card_table)
        story.append(Spacer(1, 8))

    add_modern_card("상세 관찰 기록 및 총평", row_data.get('종합 평가', ''), '#2563EB')

    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceAfter=6))
    footer_style = ParagraphStyle('FooterStyle', fontName=korean_font, fontSize=8, leading=10, alignment=1, textColor=colors.HexColor('#94A3B8'))
    story.append(Paragraph("SUNGMUN COMPANY — Professional Player Scouting Database System", footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer

df = load_data()

formation_layouts = {
    "4-3-3": [
        {"line": "FW LINE", "positions": ["LW", "CF", "RW"]},
        {"line": "MF LINE", "positions": ["LCM", "CDM", "RCM"]},
        {"line": "DF LINE", "positions": ["LB", "LCB", "RCB", "RB"]},
        {"line": "GK LINE", "positions": ["GK"]}
    ],
    "4-4-2": [
        {"line": "FW LINE", "positions": ["ST1", "ST2"]},
        {"line": "MF LINE", "positions": ["LM", "LCM", "RCM", "RM"]},
        {"line": "DF LINE", "positions": ["LB", "LCB", "RCB", "RB"]},
        {"line": "GK LINE", "positions": ["GK"]}
    ],
    "4-2-3-1": [
        {"line": "FW LINE", "positions": ["ST"]},
        {"line": "AM LINE", "positions": ["LAM", "CAM", "RAM"]},
        {"line": "DM LINE", "positions": ["LDM", "RDM"]},
        {"line": "DF LINE", "positions": ["LB", "LCB", "RCB", "RB"]},
        {"line": "GK LINE", "positions": ["GK"]}
    ],
    "3-4-3": [
        {"line": "FW LINE", "positions": ["LW", "CF", "RW"]},
        {"line": "MF LINE", "positions": ["LM", "LCM", "RCM", "RM"]},
        {"line": "DF LINE", "positions": ["LCB", "CB", "RCB"]},
        {"line": "GK LINE", "positions": ["GK"]}
    ],
    "3-5-2": [
        {"line": "FW LINE", "positions": ["ST1", "ST2"]},
        {"line": "MF LINE", "positions": ["LWB", "LCM", "CDM", "RCM", "RWB"]},
        {"line": "DF LINE", "positions": ["LCB", "CB", "RCB"]},
        {"line": "GK LINE", "positions": ["GK"]}
    ],
    "5-3-2": [
        {"line": "FW LINE", "positions": ["ST1", "ST2"]},
        {"line": "MF LINE", "positions": ["LCM", "CM", "RCM"]},
        {"line": "DF LINE", "positions": ["LWB", "LCB", "CB", "RCB", "RWB"]},
        {"line": "GK LINE", "positions": ["GK"]}
    ],
    "5-4-1": [
        {"line": "FW LINE", "positions": ["ST"]},
        {"line": "MF LINE", "positions": ["LM", "LCM", "RCM", "RM"]},
        {"line": "DF LINE", "positions": ["LWB", "LCB", "CB", "RCB", "RWB"]},
        {"line": "GK LINE", "positions": ["GK"]}
    ]
}

# ⚽ 포메이션별 라인 피치 렌더러 (LCB, RCB 적용)
def render_pitch_graphic_from_saved(team_name, formation_name, num_dict):
    display_team_name = team_name if team_name else "팀명 미입력"
    layout = formation_layouts.get(formation_name, formation_layouts["4-3-3"])
    
    rows_html = ""
    for row in layout:
        rows_html += f"<div style='color:#e2e8f0; font-weight:600; font-size:8.5px; letter-spacing: 1px; margin-bottom:2px; text-transform: uppercase; text-align: center;'>📍 {row['line']}</div>"
        rows_html += "<div style='display: flex; justify-content: center; gap: 5px; margin-bottom: 5px; flex-wrap: nowrap; width: 100%;'>"
        for pos in row['positions']:
            assigned_num = num_dict.get(pos, "")
            display_num = assigned_num if assigned_num else "-"
            rows_html += f"""
            <div style="background: radial-gradient(circle, #ef4444 0%, #b91c1c 100%); color: white; border: 2px solid rgba(255, 255, 255, 0.9); border-radius: 50%; width: 34px; height: 34px; min-width: 34px; display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: 0 3px 8px rgba(0,0,0,0.3);">
                <span style="font-size: 6px; color: #fecaca; font-weight: 700; line-height: 1.1;">{pos}</span>
                <span style="font-size: 9.5px; color: #ffffff; font-weight: 900; line-height: 1.1;">{display_num}</span>
            </div>
            """
        rows_html += "</div>"

    complete_html = f"""
    <div style="background: linear-gradient(135deg, #1b4d3e 0%, #2e8b57 50%, #227b4f 100%); border: 2px solid rgba(255, 255, 255, 0.3); border-radius: 16px; padding: 10px 6px; box-shadow: 0 10px 25px rgba(0,0,0,0.25), inset 0 0 20px rgba(255,255,255,0.1); margin-bottom: 15px; width: 100%; box-sizing: border-box; font-family: sans-serif;">
        <div style="text-align: center; color: #38bdf8; font-weight: 800; font-size: 11.5px; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,0.15); padding-bottom: 3px;">
            🏟️ {display_team_name} <span style="color: #cbd5e1; font-size: 9.5px; font-weight: normal;">({formation_name})</span>
        </div>
        {rows_html}
    </div>
    """
    
    import streamlit.components.v1 as components
    components.html(complete_html, height=410, scrolling=False)

display_logo()

st.title("⚽ 선수 스카우팅 관리 시스템")

# ----------------------------------------------------
# 사이드바 설정
# ----------------------------------------------------
st.sidebar.title("📌 메뉴")

if st.sidebar.button("🔄 앱 새로고침 (실시간 동기화)", use_container_width=True, type="secondary"):
    st.rerun()

st.sidebar.markdown("---")

menu = st.sidebar.radio("이동할 메뉴", [
    "🏟️ 현장 경기 관찰 메모", 
    "📂 경기 일지 조회", 
    "선수 등록", 
    "🔍 선수 검색 및 관찰일지 조회", 
    "🗑️ 데이터 삭제"
])

# ----------------------------------------------------
# 1. 🏟️ 현장 경기 관찰 메모
# ----------------------------------------------------
if menu == "🏟️ 현장 경기 관찰 메모":
    st.header("🏟️ 현장 경기 관찰 메모장")
    st.caption("포메이션 진형 모양 그대로 배치된 입력 칸을 터치하여 등번호를 바로 기입하세요.")

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        match_date = st.date_input("경기 일자", value=datetime.today())
    with col_m2:
        tournament_name = st.text_input("대회 이름", placeholder="예: 금석배 U18, 대통령배 등")

    st.write("---")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        home_team = st.text_input("🏠 홈팀 명*", value="", placeholder="홈팀명을 입력하세요", key="input_home_team_name")
        home_formation = st.selectbox("홈팀 포메이션", ["4-3-3", "4-4-2", "4-2-3-1", "3-4-3", "3-5-2", "5-3-2", "5-4-1"], key="home_form")
    with col_t2:
        away_team = st.text_input("✈️ 어웨이팀 명*", value="", placeholder="어웨이팀명을 입력하세요", key="input_away_team_name")
        away_formation = st.selectbox("어웨이팀 포메이션", ["4-3-3", "4-4-2", "4-2-3-1", "3-4-3", "3-5-2", "5-3-2", "5-4-1"], key="away_form")

    st.write("---")

    def render_team_interactive_grid(team_name, formation_name, prefix):
        layout = formation_layouts.get(formation_name, formation_layouts["4-3-3"])
        team_entered_numbers = {}
        
        valid_positions = [pos for row in layout for pos in row['positions']]
        all_possible_positions = ["LW", "CF", "RW", "ST1", "ST2", "ST", "LM", "LCM", "CM", "RCM", "RM", "LAM", "CAM", "RAM", "LDM", "RDM", "CDM", "LB", "LCB", "CB", "RCB", "RB", "LWB", "RWB", "GK"]
        for p in all_possible_positions:
            k = f"{prefix}_{p}"
            if p not in valid_positions and k in st.session_state:
                del st.session_state[k]

        nums_dict = {}
        for pos in valid_positions:
            key_name = f"{prefix}_{pos}"
            val = st.session_state.get(key_name, "")
            nums_dict[pos] = val
            if val.strip():
                team_entered_numbers[pos] = val.strip()

        render_pitch_graphic_from_saved(team_name, formation_name, nums_dict)

        display_t_name = team_name if team_name else "입력 대기중인 팀"
        st.markdown(f"**⚡ {display_t_name} 포메이션 진형별 등번호 직접 입력**")
        
        # 💡 모바일에서도 세로로 깨지지 않고 시각화 그라운드처럼 라인별 가로 칸 배치 유지
        for row in layout:
            st.markdown(f"<div style='font-size: 11px; font-weight: bold; color: #64748B; margin-top: 6px; margin-bottom: 2px;'>{row['line']}</div>", unsafe_allow_html=True)
            cols = st.columns(len(row['positions']))
            for idx, pos in enumerate(row['positions']):
                key_name = f"{prefix}_{pos}"
                with cols[idx]:
                    val = st.text_input(
                        f"{pos}", 
                        value=st.session_state.get(key_name, ""), 
                        key=key_name, 
                        placeholder="번호"
                    )
                    if val.strip():
                        team_entered_numbers[pos] = val.strip()

        st.write("")
        return team_entered_numbers

    pitch_col1, pitch_col2 = st.columns(2)
    with pitch_col1:
        st.markdown("### 🏠 홈팀 그라운드 및 등번호")
        home_numbers = render_team_interactive_grid(home_team, home_formation, "home")
    with pitch_col2:
        st.markdown("### ✈️ 어웨이팀 그라운드 및 등번호")
        away_numbers = render_team_interactive_grid(away_team, away_formation, "away")

    st.write("---")

    st.subheader("⭐ 시각화 포지션별 집중 관찰 메모")
    st.caption("위 그라운드 포메이션에 등번호를 입력하면 아래에 해당 포지션들이 자동으로 활성화됩니다. 메모할 포지션을 체크하세요!")

    h_display_label = home_team if home_team else "홈팀"
    a_display_label = away_team if away_team else "어웨이팀"

    player_specific_memos = {}

    memo_col_h, memo_col_a = st.columns(2)

    with memo_col_h:
        st.markdown(f"**🏠 홈팀 ({h_display_label}) 포지션별 메모**")
        active_home_pos = {pos: num for pos, num in home_numbers.items() if num}
        if active_home_pos:
            for pos, num in active_home_pos.items():
                chk_key = f"chk_memo_home_{pos}"
                is_checked = st.checkbox(f"📌 [{pos}] {num}번 메모", key=chk_key)
                if is_checked:
                    text_key = f"text_memo_home_{pos}"
                    note_val = st.text_area(f"[{pos}] {num}번 세부 관찰 기록", placeholder=f"[{pos}] {num}번 선수의 플레이 장점, 특징 등을 적어주세요...", key=text_key, height=90)
                    if note_val.strip():
                        player_specific_memos[f"[홈] {h_display_label} - [{pos}] {num}번"] = note_val.strip()
        else:
            st.info("💡 홈팀 포메이션 칸에 등번호를 입력해 주세요.")

    with memo_col_a:
        st.markdown(f"**✈️ 어웨이팀 ({a_display_label}) 포지션별 메모**")
        active_away_pos = {pos: num for pos, num in away_numbers.items() if num}
        if active_away_pos:
            for pos, num in active_away_pos.items():
                chk_key = f"chk_memo_away_{pos}"
                is_checked = st.checkbox(f"📌 [{pos}] {num}번 메모", key=chk_key)
                if is_checked:
                    text_key = f"text_memo_away_{pos}"
                    note_val = st.text_area(f"[{pos}] {num}번 세부 관찰 기록", placeholder=f"[{pos}] {num}번 선수의 플레이 장점, 특징 등을 적어주세요...", key=text_key, height=90)
                    if note_val.strip():
                        player_specific_memos[f"[어웨이] {a_display_label} - [{pos}] {num}번"] = note_val.strip()
        else:
            st.info("💡 어웨이팀 포메이션 칸에 등번호를 입력해 주세요.")

    st.write("---")
    st.subheader("📋 경기 전체 총평 및 핵심 메모")
    general_memo = st.text_area(
        "경기 전체 흐름 및 총평", 
        placeholder="[예시]\n- 전반전 탐색전 이후 후반 난타전 양상\n- 양팀 전술적 움직임 및 세트피스 분석 등",
        key="general_match_memo_input",
        height=140
    )

    st.write("")
    if st.button("💾 현장 메모 저장하기", type="primary", use_container_width=True):
        if not home_team.strip() or not away_team.strip():
            st.error("홈팀 명과 어웨이팀 명은 필수 입력 항목입니다. 팀 이름을 입력해 주세요.")
        else:
            with st.spinner("구글 시트에 현장 메모를 저장하는 중..."):
                home_valid_positions = [pos for row in formation_layouts[home_formation] for pos in row['positions']]
                away_valid_positions = [pos for row in formation_layouts[away_formation] for pos in row['positions']]

                final_home_nums = {pos: home_numbers[pos] for pos in home_valid_positions if pos in home_numbers and home_numbers[pos]}
                final_away_nums = {pos: away_numbers[pos] for pos in away_valid_positions if pos in away_numbers and away_numbers[pos]}

                home_num_str = ", ".join([f"{pos}:{num}" for pos, num in final_home_nums.items()]) if final_home_nums else "없음"
                away_num_str = ", ".join([f"{pos}:{num}" for pos, num in final_away_nums.items()]) if final_away_nums else "없음"

                player_notes_formatted = ""
                if player_specific_memos:
                    player_notes_formatted = "\n\n⭐ [선수별 집중 관찰 메모]\n"
                    for p_label, p_note in player_specific_memos.items():
                        player_notes_formatted += f"- {p_label}:\n  {p_note}\n"

                t_name_prefix = f"[{tournament_name}] " if tournament_name.strip() else ""
                
                timestamp_id = datetime.now().strftime('%H%M%S')
                memo_player_name = f"{t_name_prefix}{home_team.strip()} vs {away_team.strip()} (타임:{timestamp_id})"
                memo_team = f"{home_team.strip()} (홈) vs {away_team.strip()} (어웨이)"
                
                memo_overall = (
                    f"📅 일자: {match_date} | 대회: {tournament_name}\n"
                    f"[META_HOME_FORM:{home_formation}]\n"
                    f"[META_HOME_NUMS:{home_num_str}]\n"
                    f"[META_AWAY_FORM:{away_formation}]\n"
                    f"[META_AWAY_NUMS:{away_num_str}]\n\n"
                    f"🏠 [홈팀: {home_team.strip()}] 포메이션: {home_formation}\n"
                    f"- 포지션별 등번호: {home_num_str.replace(':', ': ')}\n\n"
                    f"✈️ [어웨이팀: {away_team.strip()}] 포메이션: {away_formation}\n"
                    f"- 포지션별 등번호: {away_num_str.replace(':', ': ')}"
                    f"{player_notes_formatted}\n\n"
                    f"📝 [경기 전체 총평]\n{general_memo}"
                )

                new_memo_data = {
                    "선수명": memo_player_name,
                    "소속팀": memo_team,
                    "등번호": "-",
                    "포지션": "경기분석",
                    "생년월일": "", "만 나이": "", "연 나이": "", "주발": "", "신장(cm)": "", "체중(kg)": "",
                    "진행 상태": "현장 관찰 메모 (임시)",
                    "장점/특기": f"대회: {tournament_name} / 홈: {home_formation} vs 어웨이: {away_formation}",
                    "보완점/단점": "",
                    "종합 평가": memo_overall,
                    "작성일자": str(match_date)
                }

                updated_df = pd.DataFrame([new_memo_data]) if df.empty else pd.concat([df, pd.DataFrame([new_memo_data])], ignore_index=True)
                if save_data_to_sheet(updated_df):
                    for p in ["LW", "CF", "RW", "ST1", "ST2", "ST", "LM", "LCM", "CM", "RCM", "RM", "LAM", "CAM", "RAM", "LDM", "RDM", "CDM", "LB", "LCB", "CB", "RCB", "RB", "LWB", "RWB", "GK"]:
                        if f"home_{p}" in st.session_state:
                            del st.session_state[f"home_{p}"]
                        if f"away_{p}" in st.session_state:
                            del st.session_state[f"away_{p}"]
                    
                    st.success("🎉 현장 경기 관찰 메모가 구글 시트에 성공적으로 저장되었습니다!")
                    st.balloons()

# ----------------------------------------------------
# 2. 📂 경기 일지 조회 (기존 메모 연동 및 깔끔한 포지션별 체크박스 수정 기능)
# ----------------------------------------------------
elif menu == "📂 경기 일지 조회":
    st.header("📂 현장 경기 관찰 일지 모음 및 추가 수정")
    st.caption("작성된 현장 경기 일지를 조회하고, 하단에서 기존 메모를 불러와 깔끔하게 이어서 작성하거나 수정할 수 있습니다.")

    memo_df = df[df["진행 상태"].str.strip() == "현장 관찰 메모 (임시)"].copy().reset_index(drop=True)

    if memo_df.empty:
        st.info("아직 저장된 경기 관찰 일지가 없습니다. [🏟️ 현장 경기 관찰 메모] 메뉴에서 첫 일지를 작성해 보세요!")
    else:
        tab_view, tab_delete = st.tabs(["📋 일지 목록 조회 및 이어서 수정", "🗑️ 일지 일괄 삭제"])

        with tab_view:
            if "작성일자" in memo_df.columns:
                memo_df_sorted = memo_df.sort_values(by="작성일자", ascending=False).reset_index(drop=True)
            else:
                memo_df_sorted = memo_df.copy()

            sc_col1, sc_col2 = st.columns([3, 1])
            with sc_col1:
                search_query = st.text_input("🔍 검색어 입력 (팀명, 대회명, 날짜 등)", placeholder="예: 안산, 금석배, 2026-03 등", key="memo_search_box")
            with sc_col2:
                available_months = ["전체"]
                if "작성일자" in memo_df_sorted.columns:
                    months_extracted = memo_df_sorted["작성일자"].apply(lambda x: str(x)[:7] if pd.notna(x) and len(str(x)) >= 7 else "").unique()
                    months_extracted = sorted([m for m in months_extracted if m and m != "nat"], reverse=True)
                    available_months.extend(months_extracted)
                
                selected_month_filter = st.selectbox("📅 월별 필터", options=available_months, key="memo_month_filter")

            filtered_memo_df = memo_df_sorted.copy()
            if search_query.strip():
                q = search_query.strip().lower()
                filtered_memo_df = filtered_memo_df[
                    filtered_memo_df["선수명"].str.lower().str.contains(q, na=False) |
                    filtered_memo_df["소속팀"].str.lower().str.contains(q, na=False) |
                    filtered_memo_df["작성일자"].str.lower().str.contains(q, na=False) |
                    filtered_memo_df["장점/특기"].str.lower().str.contains(q, na=False) |
                    filtered_memo_df["종합 평가"].str.lower().str.contains(q, na=False)
                ]

            if selected_month_filter != "전체":
                filtered_memo_df = filtered_memo_df[filtered_memo_df["작성일자"].str.startswith(selected_month_filter)]

            st.subheader("📋 경기 일지 목록 (조회 및 수정할 일지를 **클릭**하세요)")

            if filtered_memo_df.empty:
                st.warning("🔍 검색 조건에 일치하는 경기 일지가 없습니다.")
            else:
                display_memo_df = filtered_memo_df[["작성일자", "선수명", "소속팀", "장점/특기"]].copy()
                display_memo_df["선수명"] = display_memo_df["선수명"].apply(lambda x: re.sub(r' \(타임:\d+\)', '', str(x)))
                display_memo_df.columns = ["작성일자", "대회 및 대진", "홈 vs 어웨이", "대회 정보"]

                memo_selection = st.dataframe(
                    display_memo_df,
                    use_container_width=True,
                    selection_mode="single-row",
                    on_select="rerun"
                )

                selected_memo_rows = memo_selection.selection.rows if hasattr(memo_selection, "selection") else []

                if selected_memo_rows:
                    selected_row_filtered = filtered_memo_df.iloc[selected_memo_rows[0]]
                    match_indices = df[(df["선수명"] == selected_row_filtered["선수명"]) & 
                                       (df["진행 상태"] == "현장 관찰 메모 (임시)")].index

                    if len(match_indices) > 0:
                        target_memo_idx = match_indices[0]
                        p_memo = df.loc[target_memo_idx]

                        match_title = re.sub(r' \(타임:\d+\)', '', p_memo.get("선수명", "경기 기록"))
                        match_date_str = p_memo.get("작성일자", "-")
                        match_teams = p_memo.get("소속팀", "-")
                        raw_content = p_memo.get("종합 평가", "")

                        st.write("---")
                        
                        act_col1, act_col2 = st.columns([3, 1])
                        with act_col1:
                            st.markdown(f"### ⚽ {match_title}")
                            st.markdown(f"**🗓️ 일자:** {match_date_str} | **대진:** {match_teams}")
                        with act_col2:
                            try:
                                pdf_bytes = generate_pdf_report_for_memo(p_memo)
                                filename = f"{match_title.replace(' ', '_')}_경기일지.pdf"
                                b64 = base64.b64encode(pdf_bytes.getvalue()).decode()
                                dl_html = f"""
                                <div style="display: flex; flex-direction: column; width: 100%;">
                                    <a href="data:application/octet-stream;base64,{b64}" download="{filename}" 
                                       style="background-color: #2563EB; color: white; padding: 10px 16px; text-align: center; 
                                              text-decoration: none; display: inline-block; font-size: 14px; font-weight: bold; 
                                              border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); width: 100%;">
                                        📄 일지 PDF 다운로드
                                    </a>
                                </div>
                                """
                                st.markdown(dl_html, unsafe_allow_html=True)
                            except Exception as e:
                                st.error(f"PDF 생성 오류: {e}")

                        st.write("")

                        home_form = "4-3-3"
                        away_form = "4-3-3"
                        home_nums = {}
                        away_nums = {}

                        try:
                            if "[META_HOME_FORM:" in raw_content:
                                home_form = raw_content.split("[META_HOME_FORM:")[1].split("]")[0]
                            if "[META_HOME_NUMS:" in raw_content:
                                h_nums_raw = raw_content.split("[META_HOME_NUMS:")[1].split("]")[0]
                                if h_nums_raw and h_nums_raw != "없음":
                                    for item in h_nums_raw.split(","):
                                        if ":" in item:
                                            p_key, p_val = item.split(":")
                                            home_nums[p_key.strip()] = p_val.strip()

                            if "[META_AWAY_FORM:" in raw_content:
                                away_form = raw_content.split("[META_AWAY_FORM:")[1].split("]")[0]
                            if "[META_AWAY_NUMS:" in raw_content:
                                a_nums_raw = raw_content.split("[META_AWAY_NUMS:")[1].split("]")[0]
                                if a_nums_raw and a_nums_raw != "없음":
                                    for item in a_nums_raw.split(","):
                                        if ":" in item:
                                            p_key, p_val = item.split(":")
                                            away_nums[p_key.strip()] = p_val.strip()
                        except Exception:
                            pass

                        clean_content = raw_content
                        for tag in [f"[META_HOME_FORM:{home_form}]", f"[META_HOME_NUMS:", f"[META_AWAY_FORM:{away_form}]", f"[META_AWAY_NUMS:"]:
                            if tag in clean_content:
                                lines = clean_content.split("\n")
                                clean_content = "\n".join([l for l in lines if not tag in l])

                        st.markdown("### 🏟️ 당시 경기 그라운드 포메이션 & 등번호 시각화")
                        p_col1, p_col2 = st.columns(2)
                        
                        h_team_name = "홈팀"
                        a_team_name = "어웨이팀"
                        if " vs " in match_teams:
                            parts = match_teams.split(" vs ")
                            h_team_name = parts[0].replace(" (홈)", "").strip()
                            a_team_name = parts[1].replace(" (어웨이)", "").strip()

                        with p_col1:
                            render_pitch_graphic_from_saved(h_team_name, home_form, home_nums)
                        with p_col2:
                            render_pitch_graphic_from_saved(a_team_name, away_form, away_nums)

                        st.markdown("---")
                        st.markdown("**📝 현재 저장된 상세 관찰 기록 및 선수별 메모**")
                        st.info(clean_content)

                        existing_player_notes = ""
                        existing_general_memo = ""

                        if "⭐ [선수별 집중 관찰 메모]" in raw_content:
                            parts = raw_content.split("⭐ [선수별 집중 관찰 메모]")
                            rest_parts = parts[1].split("📝 [경기 전체 총평]\n")
                            existing_player_notes = rest_parts[0].strip()
                            existing_general_memo = rest_parts[1].strip() if len(rest_parts) > 1 else ""
                        else:
                            if "📝 [경기 전체 총평]\n" in raw_content:
                                existing_general_memo = raw_content.split("📝 [경기 전체 총평]\n")[-1]
                            else:
                                existing_general_memo = raw_content

                        parsed_pos_memos = {}
                        if existing_player_notes:
                            note_lines = existing_player_notes.split("\n- ")
                            for line in note_lines:
                                if ":" in line:
                                    header_part, content_part = line.split(":", 1)
                                    parsed_pos_memos[header_part.strip()] = content_part.strip()

                        st.markdown("---")
                        with st.expander("✏️ 포메이션별 선수 체크 및 기존 메모 이어서 수정·추가하기", expanded=True):
                            st.caption("등번호가 기입된 포지션별 체크박스를 켜면, **기존에 적어둔 메모가 그대로 유지되어 이어서 작성**할 수 있습니다.")

                            edit_player_specific_memos = {}
                            edit_memo_col_h, edit_memo_col_a = st.columns(2)

                            with edit_memo_col_h:
                                st.markdown(f"**🏠 홈팀 ({h_team_name}) 포지션별 메모**")
                                if home_nums:
                                    for pos, num in home_nums.items():
                                        chk_key = f"edit_chk_home_{target_memo_idx}_{pos}"
                                        p_label_key = f"[홈] {h_team_name} - [{pos}] {num}번"
                                        
                                        has_old_note = p_label_key in existing_player_notes or any(p_label_key in l for l in existing_player_notes.split("\n"))
                                        
                                        is_checked = st.checkbox(f"📌 [{pos}] {num}번 메모", value=has_old_note, key=chk_key)
                                        
                                        default_note_val = ""
                                        for key_str, val_str in parsed_pos_memos.items():
                                            if pos in key_str and num in key_str and "홈" in key_str:
                                                default_note_val = val_str
                                                break

                                        if is_checked:
                                            text_key = f"edit_text_home_{target_memo_idx}_{pos}"
                                            note_val = st.text_area(f"[{pos}] {num}번 세부 관찰 기록", value=default_note_val, placeholder=f"[{pos}] {num}번 선수 메모 입력...", key=text_key, height=90)
                                            if note_val.strip():
                                                edit_player_specific_memos[p_label_key] = note_val.strip()
                                else:
                                    st.info("등록된 홈팀 등번호가 없습니다.")

                            with edit_memo_col_a:
                                st.markdown(f"**✈️ 어웨이팀 ({a_team_name}) 포지션별 메모**")
                                if away_nums:
                                    for pos, num in away_nums.items():
                                        chk_key = f"edit_chk_away_{target_memo_idx}_{pos}"
                                        p_label_key = f"[어웨이] {a_team_name} - [{pos}] {num}번"
                                        
                                        has_old_note = p_label_key in existing_player_notes or any(p_label_key in l for l in existing_player_notes.split("\n"))
                                        
                                        is_checked = st.checkbox(f"📌 [{pos}] {num}번 메모", value=has_old_note, key=chk_key)
                                        
                                        default_note_val = ""
                                        for key_str, val_str in parsed_pos_memos.items():
                                            if pos in key_str and num in key_str and "어웨이" in key_str:
                                                default_note_val = val_str
                                                break

                                        if is_checked:
                                            text_key = f"edit_text_away_{target_memo_idx}_{pos}"
                                            note_val = st.text_area(f"[{pos}] {num}번 세부 관찰 기록", value=default_note_val, placeholder=f"[{pos}] {num}번 선수 메모 입력...", key=text_key, height=90)
                                            if note_val.strip():
                                                edit_player_specific_memos[p_label_key] = note_val.strip()
                                else:
                                    st.info("등록된 어웨이팀 등번호가 없습니다.")

                            st.write("")
                            edit_general_input = st.text_area(
                                "📋 경기 전체 총평 수정 및 이어쓰기",
                                value=existing_general_memo,
                                key=f"edit_general_memo_{target_memo_idx}",
                                height=140
                            )

                            if st.button("💾 메모 및 총평 수정·추가 반영하기", type="primary", use_container_width=True, key=f"btn_save_all_memo_edit_{target_memo_idx}"):
                                with st.spinner("구글 시트의 일지 내용을 업데이트하는 중..."):
                                    meta_part = raw_content.split("⭐ [선수별 집중 관찰 메모]")[0] if "⭐ [선수별 집중 관찰 메모]" in raw_content else raw_content.split("📝 [경기 전체 총평]")[0]

                                    new_notes_str = ""
                                    for p_label, p_note in edit_player_specific_memos.items():
                                        new_notes_str += f"- {p_label}:\n  {p_note}\n"

                                    player_notes_section = f"\n\n⭐ [선수별 집중 관찰 메모]\n{new_notes_str.strip()}" if new_notes_str.strip() else ""
                                    general_section = f"\n\n📝 [경기 전체 총평]\n{edit_general_input.strip()}"

                                    new_full_content = f"{meta_part}{player_notes_section}{general_section}"

                                    records = df.to_dict('records')
                                    records[target_memo_idx]["종합 평가"] = new_full_content
                                    updated_df = pd.DataFrame(records).astype(str)

                                    if save_data_to_sheet(updated_df):
                                        st.success("🎉 경기 일지 및 선수별 집중 메모가 깔끔하게 업데이트되었습니다!")
                                        st.rerun()
                else:
                    st.info("💡 위 목록 표에서 조회하거나 수정할 **경기 일지 행을 클릭**하세요.")

        with tab_delete:
            st.subheader("🗑️ 경기 일지 다중 선택 및 일괄 삭제")
            st.caption("표에서 **삭제할 일지들을 여러 개 선택(다중 클릭)**한 뒤, 하단의 삭제 버튼을 누르세요.")

            memo_df_del = memo_df.sort_values(by="작성일자", ascending=False).reset_index(drop=True) if "작성일자" in memo_df.columns else memo_df.copy()
            
            display_del_df = memo_df_del[["작성일자", "선수명", "소속팀", "장점/특기"]].copy()
            display_del_df["선수명"] = display_del_df["선수명"].apply(lambda x: re.sub(r' \(타임:\d+\)', '', str(x)))
            display_del_df.columns = ["작성일자", "대회 및 대진", "홈 vs 어웨이", "대회 정보"]

            del_selection = st.dataframe(
                display_del_df,
                use_container_width=True,
                selection_mode="multi-row",
                on_select="rerun",
                key="memo_multi_delete_dataframe"
            )

            selected_del_rows = del_selection.selection.rows if hasattr(del_selection, "selection") else []

            st.write("---")

            if selected_del_rows:
                st.warning(f"⚠️ 총 {len(selected_del_rows)}개의 경기 일지가 선택되었습니다. 아래 버튼을 누르면 영구 삭제됩니다.")
                if st.button("🗑️ 선택한 경기 일지 일괄 삭제하기", type="primary", use_container_width=True, key="btn_execute_batch_delete"):
                    with st.spinner("구글 시트에서 선택된 일지들을 삭제하는 중..."):
                        indices_to_drop = []
                        for r_idx in selected_del_rows:
                            if r_idx < len(memo_df_del):
                                selected_row_data = memo_df_del.iloc[r_idx]
                                orig_indices = df[(df["선수명"] == memo_df_del.iloc[r_idx]["선수명"]) & 
                                                  (df["진행 상태"] == "현장 관찰 메모 (임시)")].index
                                if len(orig_indices) > 0:
                                    indices_to_drop.append(orig_indices[0])

                        if indices_to_drop:
                            df = df.drop(indices_to_drop).reset_index(drop=True)
                            if save_data_to_sheet(df):
                                st.success("🎉 선택한 경기 일지들이 성공적으로 일괄 삭제되었습니다! 페이지를 갱신합니다.")
                                st.rerun()
            else:
                st.info("💡 위 표에서 삭제할 경기 일지 행들을 마우스로 **다중 선택(Shift/Ctrl 클릭 또는 체크)**해 주세요.")

# ----------------------------------------------------
# 3. 선수 등록
# ----------------------------------------------------
elif menu == "선수 등록":
    st.header("📋 신규 관찰 선수 등록")
    
    if "reg_success_msg" in st.session_state and st.session_state["reg_success_msg"]:
        st.success(st.session_state["reg_success_msg"])
        st.balloons()
        st.session_state["reg_success_msg"] = None

    with st.form("player_reg_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("선수명*")
            team = st.text_input("현재 소속팀")
            position = st.selectbox("포지션", options=POSITION_OPTIONS)
            status = st.selectbox("진행 상태", STATUS_OPTIONS)
            
            back_num_options = [""] + [str(i) for i in range(1, 100)]
            back_num_val = st.selectbox("등번호", options=back_num_options, index=0, placeholder="등번호 선택")

        with col2:
            birth_date = st.date_input("생년월일 선택*", value=datetime(2005, 1, 1), min_value=datetime(1980, 1, 1), max_value=datetime.today())
            foot = st.selectbox("주발", ["오른발", "왼발", "양발"])
            date = st.date_input("관찰/작성일자", value=datetime.today())
            
            hw_col1, hw_col2 = st.columns(2)
            with hw_col1:
                height_val = st.text_input("신장 (cm)", value="175", placeholder="예: 182")
            with hw_col2:
                weight_val = st.text_input("체중 (kg)", value="70", placeholder="예: 75")

        st.subheader("📝 관찰 리포트 / 첫 메모")
        pros = st.text_area("장점 및 주요 특기")
        cons = st.text_area("보완점 및 약점")
        overall = st.text_area("종합 평가 / 코멘트")
        
        submitted = st.form_submit_button("💾 선수 데이터 저장", type="primary", use_container_width=True)
        
        if submitted:
            if not name.strip():
                st.error("선수명은 필수 입력 항목입니다.")
            else:
                age_full_str, age_year_str = calculate_age(birth_date)
                with st.spinner("구글 시트에 데이터를 안전하게 저장하는 중..."):
                    new_data = {
                        "선수명": name.strip(), "소속팀": team.strip(), "등번호": str(back_num_val),
                        "포지션": position, "생년월일": str(birth_date),
                        "만 나이": age_full_str, "연 나이": age_year_str, "주발": foot,
                        "신장(cm)": str(height_val).strip(), "체중(kg)": str(weight_val).strip(),
                        "진행 상태": status, "장점/특기": pros.strip(), "보완점/단점": cons.strip(),
                        "종합 평가": overall.strip(), "작성일자": str(date)
                    }
                    updated_df = pd.DataFrame([new_data]) if df.empty else pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                    if save_data_to_sheet(updated_df):
                        st.session_state["reg_success_msg"] = f"🎉 '{name.strip()}' 선수의 데이터가 구글 시트에 성공적으로 저장되었습니다!"
                        st.rerun()

# ----------------------------------------------------
# 4. 🔍 선수 검색 및 관찰일지 조회
# ----------------------------------------------------
elif menu == "🔍 선수 검색 및 관찰일지 조회":
    st.header("🔍 관찰 선수 검색 및 상세 일지 / PDF 다운로드")
    
    official_df = df[df["진행 상태"].str.strip() != "현장 관찰 메모 (임시)"].copy().reset_index(drop=True)
    
    if official_df.empty:
        st.info("등록된 선수 데이터가 없습니다.")
    else:
        total_count = len(official_df)
        watchlist_count = len(official_df[official_df["진행 상태"] == "관심 선수 (Watchlist)"])
        observing_count = len(official_df[official_df["진행 상태"] == "집중 관찰 중"])
        review_count = len(official_df[official_df["진행 상태"] == "계약 검토"])
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("공식 등록 선수", f"{total_count}명")
        m2.metric("관심 선수 (Watchlist)", f"{watchlist_count}명")
        m3.metric("집중 관찰 중", f"{observing_count}명")
        m4.metric("계약 검토", f"{review_count}명")
        
        st.write("---")
        
        f_col1, f_col2, f_col3, f_col4 = st.columns([2, 1, 1, 1])
        with f_col1:
            search_term = st.text_input("🔍 검색 (선수명, 소속팀, 등번호, 키워드)", key="live_search_input")
        with f_col2:
            position_filter = st.selectbox("🛡️ 포지션 필터", ["전체"] + POSITION_OPTIONS, key="live_position_filter")
        with f_col3:
            foot_filter = st.selectbox("⚽ 주발 필터", ["전체", "왼발", "오른발", "양발"], key="live_foot_filter")
        with f_col4:
            status_filter = st.selectbox("📌 진행 상태 필터", ["전체"] + STATUS_OPTIONS, key="live_status_filter")
        
        filtered_df = official_df.copy()
        
        if search_term:
            filtered_df = filtered_df[
                filtered_df["선수명"].str.contains(search_term, case=False, na=False) | 
                filtered_df["소속팀"].str.contains(search_term, case=False, na=False) |
                filtered_df["등번호"].str.contains(search_term, case=False, na=False) |
                filtered_df["장점/특기"].str.contains(search_term, case=False, na=False) |
                filtered_df["종합 평가"].str.contains(search_term, case=False, na=False)
            ]
            
        if position_filter != "전체":
            filtered_df = filtered_df[filtered_df["포지션"].str.strip() == position_filter]
        if foot_filter != "전체":
            filtered_df = filtered_df[filtered_df["주발"] == foot_filter]
        if status_filter != "전체":
            filtered_df = filtered_df[filtered_df["진행 상태"] == status_filter]
        
        st.subheader(f"📋 선수 목록 (클릭 시 하단에 관찰일지 및 수정/삭제 폼 표출)")
        
        display_cols = [c for c in filtered_df.columns if c != "연 나이"]
        display_df = filtered_df[display_cols].copy()
        display_df["소속팀"] = display_df["소속팀"].apply(lambda x: parse_team_info(x)[0])
        
        def highlight_search(val):
            if search_term and search_term.strip() and str(search_term).lower() in str(val).lower():
                return 'background-color: #fff9c4; color: #000000; font-weight: bold;'
            return ''

        if not display_df.empty:
            styled_df = display_df.style.map(highlight_search)
            selection = st.dataframe(
                styled_df,
                use_container_width=True,
                selection_mode="single-row",
                on_select="rerun"
            )
        else:
            selection = st.dataframe(
                display_df,
                use_container_width=True,
                selection_mode="single-row",
                on_select="rerun"
            )
        
        selected_rows = selection.selection.rows if hasattr(selection, "selection") else []
        
        if selected_rows:
            selected_row_filtered = filtered_df.iloc[selected_rows[0]]
            match_indices = df[(df["선수명"] == selected_row_filtered["선수명"]) & 
                               (df["소속팀"] == selected_row_filtered["소속팀"]) & 
                               (df["생년월일"] == selected_row_filtered["생년월일"]) &
                               (df["진행 상태"] != "현장 관찰 메모 (임시)")].index

            if len(match_indices) > 0:
                target_idx = match_indices[0]
                p = df.loc[target_idx]
                
                current_team_name, past_team_history = parse_team_info(p.get('소속팀', ''))
                
                st.write("---")
                
                head_col1, head_col2 = st.columns([3, 1])
                with head_col1:
                    st.markdown(f"### ⚽ [{p.get('진행 상태', '')}] {p.get('선수명', '')} 상세 관찰일지")
                with head_col2:
                    try:
                        pdf_bytes = generate_pdf_report(p)
                        filename = f"{p.get('선수명', '선수')}_스카우팅관찰일지.pdf"
                        
                        b64 = base64.b64encode(pdf_bytes.getvalue()).decode()
                        dl_html = f"""
                        <div style="display: flex; flex-direction: column; width: 100%;">
                            <a href="data:application/octet-stream;base64,{b64}" download="{filename}" 
                               style="background-color: #2563EB; color: white; padding: 10px 16px; text-align: center; 
                                      text-decoration: none; display: inline-block; font-size: 14px; font-weight: bold; 
                                      border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); width: 100%;">
                                📄 관찰일지 PDF 다운로드
                            </a>
                            <span style="font-size: 11px; color: #64748B; text-align: center; margin-top: 5px;">
                                💡 모바일에서 새 창이 열리지 않고 안전하게 파일로 저장됩니다.
                            </span>
                        </div>
                        """
                        st.markdown(dl_html, unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"PDF 생성 중 오류 발생: {e}")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("현재 소속팀 / 등번호", f"{current_team_name} / {p.get('등번호', '-')}번")
                c2.metric("포지션 / 주발", f"{p.get('포지션', '-')} / {p.get('주발', '-')}")
                c3.metric("나이", f"{p.get('만 나이', '-')}")
                
                weight_display = f"{p.get('체중(kg)')}kg" if p.get('체중(kg)') else "미입력"
                c4.metric("피지컬", f"{p.get('신장(cm)', '-')}cm / {weight_display}")
                
                if past_team_history:
                    st.info(f"📜 **소속팀 이력**: {current_team_name} {past_team_history}")
                    
                st.write(f"• **생년월일**: {p.get('생년월일', '-')} | **최근 업데이트**: {p.get('작성일자', '-')}")
                
                st.markdown("---")

                st.subheader("📚 날짜별 관찰일지 및 누적 메모")
                
                with st.container():
                    st.markdown("#### 🌟 [장점 및 주요 특기 메모]")
                    pros_text = p.get('장점/특기', '')
                    if pd.notna(pros_text) and str(pros_text).strip():
                        st.info(pros_text)
                    else:
                        st.write("등록된 내용이 없습니다.")
                        
                    st.markdown("#### ⚠️ [보완점 및 약점 메모]")
                    cons_text = p.get('보완점/단점', '')
                    if pd.notna(cons_text) and str(cons_text).strip():
                        st.warning(cons_text)
                    else:
                        st.write("등록된 내용이 없습니다.")
                        
                    st.markdown("#### 📋 [스카우터 종합 평가 코멘트]")
                    overall_text = p.get('종합 평가', '')
                    if pd.notna(overall_text) and str(overall_text).strip():
                        st.success(overall_text)
                    else:
                        st.write("등록된 내용이 없습니다.")

                st.write("---")
                with st.expander(f"✏️ [{p.get('선수명', '')}] 선수 정보 수정 및 추가 관찰 일지 작성 폼 열기", expanded=False):
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        edit_name = st.text_input("선수명", value=str(p.get("선수명", "")), key=f"inline_edit_name_{target_idx}")
                        edit_team_input = st.text_input("소속팀 (팀이 바뀐 경우 새 팀명 입력)", value=current_team_name, key=f"inline_edit_team_{target_idx}")
                        
                        cur_pos = str(p.get("포지션", "MF"))
                        pos_idx = POSITION_OPTIONS.index(cur_pos) if cur_pos in POSITION_OPTIONS else 4
                        edit_position = st.selectbox("포지션", POSITION_OPTIONS, index=pos_idx, key=f"inline_edit_pos_{target_idx}")
                        
                        default_status = str(p.get("진행 상태", STATUS_OPTIONS[0]))
                        status_index = STATUS_OPTIONS.index(default_status) if default_status in STATUS_OPTIONS else 0
                        edit_status = st.selectbox("진행 상태", STATUS_OPTIONS, index=status_index, key=f"inline_edit_status_{target_idx}")
                        
                        cur_num = str(p.get("등번호", "")).strip()
                        back_num_options = [""] + [str(i) for i in range(1, 100)]
                        num_idx = back_num_options.index(cur_num) if cur_num in back_num_options else 0
                        edit_back_num = st.selectbox("등번호", options=back_num_options, index=num_idx, key=f"inline_edit_num_{target_idx}")

                    with col_e2:
                        default_birth = parse_date(p.get("생년월일"))
                        edit_birth_date = st.date_input("생년월일", value=default_birth, key=f"inline_edit_birth_{target_idx}")
                        age_full_str, age_year_str = calculate_age(edit_birth_date)
                        
                        default_foot = str(p.get("주발", "오른발"))
                        foot_options = ["오른발", "왼발", "양발"]
                        foot_index = foot_options.index(default_foot) if default_foot in foot_options else 0
                        edit_foot = st.selectbox("주발", foot_options, index=foot_index, key=f"inline_edit_foot_{target_idx}")
                        
                        edit_date = st.date_input("관찰 작성일자", value=datetime.today(), key=f"inline_edit_date_{target_idx}")
                        
                        edit_hw1, edit_hw2 = st.columns(2)
                        with edit_hw1:
                            edit_height = st.text_input("신장 (cm)", value=str(p.get("신장(cm)", "175")), key=f"inline_edit_h_{target_idx}")
                        with edit_hw2:
                            edit_weight = st.text_input("체중 (kg)", value=str(p.get("체중(kg)", "70")), key=f"inline_edit_w_{target_idx}")

                    st.subheader("➕ 오늘 관찰한 내용 추가 입력 (누적 기록)")
                    new_pros = st.text_area("새 관찰 장점", key=f"inline_new_pros_{target_idx}")
                    new_cons = st.text_area("새로 관찰한 보완점", key=f"inline_new_cons_{target_idx}")
                    new_overall = st.text_area("새로 관찰한 종합 평가", key=f"inline_new_overall_{target_idx}")
                    
                    col_btn_save, col_btn_del = st.columns([1, 1])
                    with col_btn_save:
                        if st.button("🔄 변경사항 및 추가 일지 저장하기", type="primary", use_container_width=True, key=f"inline_btn_save_{target_idx}"):
                            if not edit_name.strip():
                                st.error("선수명은 필수입니다.")
                            else:
                                with st.spinner("변경사항을 구글 시트에 업데이트하는 중..."):
                                    new_team_input = edit_team_input.strip()
                                    raw_old_team = str(p.get("소속팀", "")).strip()
                                    
                                    if current_team_name and new_team_input and current_team_name != new_team_input:
                                        if "(전:" not in raw_old_team:
                                            final_team_str = f"{new_team_input} (전: {current_team_name})"
                                        else:
                                            history_part = raw_old_team.split("(전:")[1]
                                            final_team_str = f"{new_team_input} (전: {current_team_name}, {history_part}"
                                    else:
                                        final_team_str = raw_old_team if raw_old_team else new_team_input

                                    old_pros = str(p.get("장점/특기", ""))
                                    old_cons = str(p.get("보완점/단점", ""))
                                    old_overall = str(p.get("종합 평가", ""))
                                    
                                    today_str = str(edit_date)
                                    updated_pros = f"{old_pros}\n\n[{today_str} 관찰]\n{new_pros.strip()}".strip() if new_pros.strip() else old_pros
                                    updated_cons = f"{old_cons}\n\n[{today_str} 관찰]\n{new_cons.strip()}".strip() if new_cons.strip() else old_cons
                                    updated_overall = f"{old_overall}\n\n[{today_str} 관찰]\n{new_overall.strip()}".strip() if new_overall.strip() else old_overall

                                    records = df.to_dict('records')
                                    records[target_idx] = {
                                        "선수명": str(edit_name).strip(), "소속팀": str(final_team_str),
                                        "등번호": str(edit_back_num), "포지션": str(edit_position),
                                        "생년월일": str(edit_birth_date), "만 나이": str(age_full_str),
                                        "연 나이": str(age_year_str), "주발": str(edit_foot),
                                        "신장(cm)": str(edit_height).strip(), "체중(kg)": str(edit_weight).strip(),
                                        "진행 상태": str(edit_status), "장점/특기": str(updated_pros),
                                        "보완점/단점": str(updated_cons), "종합 평가": str(updated_overall),
                                        "작성일자": str(today_str)
                                    }
                                    updated_df = pd.DataFrame(records).astype(str)
                                    if save_data_to_sheet(updated_df):
                                        st.success("🎉 선수 정보와 소속 이력, 추가 관찰 일지가 성공적으로 수정·저장되었습니다!")
                                        st.rerun()

                    with col_btn_del:
                        confirm_inline_del = st.checkbox("⚠️ 이 선수 데이터 삭제 확인", key=f"inline_chk_del_{target_idx}")
                        if confirm_inline_del:
                            if st.button("🗑️ 해당 선수 데이터 영구 삭제", type="secondary", use_container_width=True, key=f"inline_btn_del_{target_idx}"):
                                with st.spinner("구글 시트에서 선수 데이터를 영구 삭제하는 중..."):
                                    updated_df = df.drop([target_idx]).reset_index(drop=True)
                                    if save_data_to_sheet(updated_df):
                                        st.success("🎉 해당 선수 데이터가 성공적으로 영구 삭제되었습니다!")
                                        st.rerun()
        else:
            st.info("💡 위 선수 목록 표에서 조회하고 싶은 **선수 행을 클릭**하시면 관찰일지와 PDF 다운로드 버튼, 수정/삭제 폼이 나타납니다.")

# ----------------------------------------------------
# 5. 데이터 삭제
# ----------------------------------------------------
elif menu == "🗑️ 데이터 삭제":
    st.header("🗑️ 선수 데이터 삭제")
    if df.empty:
        st.info("삭제할 데이터가 없습니다.")
    else:
        st.subheader("📋 삭제할 선수를 표에서 **여러 명 다중 선택**하세요")
        
        del_selection = st.dataframe(
            df,
            use_container_width=True,
            selection_mode="multi-row",
            on_select="rerun"
        )
        
        del_selected_rows = del_selection.selection.rows if hasattr(del_selection, "selection") else []
        
        if del_selected_rows:
            selected_count = len(del_selected_rows)
            st.write("---")
            
            selected_names = [df.loc[idx, '선수명'] for idx in del_selected_rows]
            st.warning(f"⚠️ 선택된 선수 총 **{selected_count}명**: {', '.join(selected_names)}")
            
            confirm_key = "confirm_delete_mode"
            if confirm_key not in st.session_state:
                st.session_state[confirm_key] = False
            
            if not st.session_state[confirm_key]:
                if st.button(f"🗑️ 선택한 {selected_count}명 데이터 영구 삭제하기", type="primary", use_container_width=True):
                    st.session_state[confirm_key] = True
                    st.rerun()
            else:
                st.error(f"🚨 **정말로 총 {selected_count}명의 데이터를 삭제하시겠습니까?** 이 작업은 되돌릴 수 없습니다!")
                
                c_yes, c_no = st.columns(2)
                with c_yes:
                    if st.button("✅ 예, 삭제합니다", type="primary", use_container_width=True):
                        with st.spinner("구글 시트에서 선택된 데이터를 영구 삭제하는 중..."):
                            updated_df = df.drop(del_selected_rows).reset_index(drop=True)
                            if save_data_to_sheet(updated_df):
                                st.session_state[confirm_key] = False
                                st.success(f"총 {selected_count}명의 선수 데이터가 성공적으로 영구 삭제되었습니다!")
                                st.rerun()
                with c_no:
                    if st.button("❌ 아니오 (취소)", use_container_width=True):
                        st.session_state[confirm_key]= False
                        st.rerun()
        else:
            if "confirm_delete_mode" in st.session_state:
                st.session_state["confirm_delete_mode"] = False
                
            st.info("💡 위 목록 표에서 삭제하고 싶은 **선수 행들을 체크(다중 선택)** 하시면 삭제 버튼이 나타납니다.")
