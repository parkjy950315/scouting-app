import streamlit as st
import pandas as pd
import requests
import io
import re
import os
import base64
import json
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
# 📱 PC & 모바일 최적화 스타일 설정
# ----------------------------------------------------
st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 4rem !important;
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
    
    input {
        font-size: 16px !important;
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
        h1 {
            font-size: 20px !important;
            margin-top: 2px !important;
            margin-bottom: 10px !important;
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
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; padding: 5px 0 15px 0; margin-bottom: 5px;">
        <div style="color: #007bff; font-weight: 900; letter-spacing: 4px; font-size: 28px; font-family: sans-serif; line-height: 1.1;">SMC</div>
        <div style="color: #6c757d; font-weight: 700; letter-spacing: 4px; font-size: 10px; font-family: sans-serif; margin-top: 3px;">SUNGMUN COMPANY</div>
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
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
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

    header_data = [[Paragraph("<b>SMC SCOUTING REPORT</b>", title_style), Paragraph(f"<b>발급일:</b> {datetime.today().strftime('%Y-%m-%d')}", header_date)]]
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

    match_title = row_data.get('선수명', '경기 기록')
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

def render_pitch_graphic_with_numbers(team_name, formation_name, num_dict):
    layout = formation_layouts.get(formation_name, formation_layouts["4-3-3"])
    rows_html = ""
    for row in layout:
        rows_html += f"<div style='color:#e2e8f0; font-weight:600; font-size:8px; letter-spacing: 1px; margin-bottom:1px; text-transform: uppercase; text-align: center;'>{row['line']}</div>"
        rows_html += "<div style='display: flex; justify-content: center; gap: 4px; margin-bottom: 4px; flex-wrap: nowrap; width: 100%;'>"
        for pos in row['positions']:
            assigned_num = num_dict.get(pos, "")
            display_num = assigned_num if assigned_num else "-"
            rows_html += f"""
            <div style="background: radial-gradient(circle, #ef4444 0%, #b91c1c 100%); color: white; border: 2px solid rgba(255, 255, 255, 0.9); border-radius: 50%; width: 32px; height: 32px; min-width: 32px; display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: 0 2px 6px rgba(0,0,0,0.3);">
                <span style="font-size: 5.5px; color: #fecaca; font-weight: 700; line-height: 1.0;">{pos}</span>
                <span style="font-size: 9px; color: #ffffff; font-weight: 900; line-height: 1.0;">{display_num}</span>
            </div>
            """
        rows_html += "</div>"

    complete_html = f"""
    <div style="background: linear-gradient(135deg, #1b4d3e 0%, #2e8b57 50%, #227b4f 100%); border: 2px solid rgba(255, 255, 255, 0.3); border-radius: 14px; padding: 8px 4px; box-shadow: 0 6px 15px rgba(0,0,0,0.25); margin-bottom: 10px; width: 100%; box-sizing: border-box; font-family: sans-serif;">
        <div style="text-align: center; color: #38bdf8; font-weight: 800; font-size: 11px; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 4px; border-bottom: 1px solid rgba(255,255,255,0.15); padding-bottom: 2px;">
            🏟️ {team_name} <span style="color: #cbd5e1; font-size: 9px; font-weight: normal;">({formation_name})</span>
        </div>
        {rows_html}
    </div>
    """
    import streamlit.components.v1 as components
    components.html(complete_html, height=360, scrolling=False)

display_logo()
st.title("⚽ 선수 스카우팅 관리 시스템")

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
    st.caption("포메이션 진형에 맞춰 등번호를 기입하면, 위쪽 피치(그라운드) 빨간 원에 즉시 반영됩니다.")

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        match_date = st.date_input("경기 일자", value=datetime.today())
    with col_m2:
        tournament_name = st.text_input("대회 이름", placeholder="예: 금석배 U18")

    st.write("---")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("### 🏠 홈팀 설정")
        home_team = st.text_input("홈팀 명*", placeholder="홈팀 이름 입력", key="new_home_team_input")
        home_formation = st.selectbox("홈팀 포메이션", ["4-3-3", "4-4-2", "4-2-3-1", "3-4-3", "3-5-2", "5-3-2", "5-4-1"], key="home_form")
    with col_t2:
        st.markdown("### ✈️ 어웨이팀 설정")
        away_team = st.text_input("어웨이팀 명*", placeholder="어웨이팀 이름 입력", key="new_away_team_input")
        away_formation = st.selectbox("어웨이팀 포메이션", ["4-3-3", "4-4-2", "4-2-3-1", "3-4-3", "3-5-2", "5-3-2", "5-4-1"], key="away_form")

    st.write("---")

    def render_team_compact_grid(team_name, formation_name, prefix):
        layout = formation_layouts.get(formation_name, formation_layouts["4-3-3"])
        team_entered_numbers = {}
        all_positions = [pos for row in layout for pos in row['positions']]
        nums_dict = {}
        for pos in all_positions:
            k_name = f"{prefix}_{pos}"
            current_val = st.session_state.get(k_name, "")
            nums_dict[pos] = current_val
            if current_val.strip():
                team_entered_numbers[pos] = current_val.strip()

        render_pitch_graphic_with_numbers(team_name if team_name else "팀", formation_name, nums_dict)
        st.markdown(f"**⚡ [{team_name if team_name else '팀'}] 포지션별 등번호 입력**")
        
        for row in layout:
            st.markdown(f"<div style='font-size: 10px; font-weight: bold; color: #64748B; margin-top: 2px;'>{row['line']}</div>", unsafe_allow_html=True)
            cols = st.columns(len(row['positions']))
            for idx, pos in enumerate(row['positions']):
                key_name = f"{prefix}_{pos}"
                with cols[idx]:
                    val = st.text_input(f"{pos}", value=st.session_state.get(key_name, ""), key=key_name, placeholder=pos, label_visibility="collapsed")
                    st.markdown(f"<p style='text-align:center; font-size:10px; color:#475569; margin-top:-10px;'>{pos}</p>", unsafe_allow_html=True)
                    if val.strip():
                        team_entered_numbers[pos] = val.strip()
        st.write("")
        return team_entered_numbers

    pitch_col1, pitch_col2 = st.columns(2)
    with pitch_col1:
        home_numbers = render_team_compact_grid(home_team, home_formation, "home")
    with pitch_col2:
        away_numbers = render_team_compact_grid(away_team, away_formation, "away")

    st.write("---")
    st.subheader("⭐ 눈에 띤 선수별 집중 메모")
    
    active_players = []
    for pos, num in home_numbers.items():
        if num:
            active_players.append(f"[홈] {home_team if home_team else '홈팀'} - {pos} (#{num})")
    for pos, num in away_numbers.items():
        if num:
            active_players.append(f"[어웨이] {away_team if away_team else '어웨이팀'} - {pos} (#{num})")

    player_specific_memos = {}
    if active_players:
        selected_players_to_memo = st.multiselect("관찰 메모를 작성할 선수 선택", options=active_players, key="selected_memo_players_multiselect")
        if selected_players_to_memo:
            st.markdown("---")
            for player_label in selected_players_to_memo:
                st.markdown(f"**📌 {player_label} 관찰 기록**")
                memo_key = f"memo_desc_{player_label}"
                player_note = st.text_area(f"{player_label}에 대한 세부 메모", value=st.session_state.get(memo_key, ""), key=memo_key, height=90)
                if player_note.strip():
                    player_specific_memos[player_label] = player_note.strip()
    else:
        st.info("💡 포메이션 칸에 등번호를 기입하면, 여기에 선수별 메모장 활성화 체크박스가 나타납니다.")

    st.write("---")
    st.subheader("📋 경기 전체 총평 및 핵심 메모")
    general_memo = st.text_area("경기 전체 흐름 및 총평", key="general_match_memo_input", height=120)

    if st.button("💾 현장 메모 임시 저장하기", type="primary", use_container_width=True):
        if not home_team.strip() or not away_team.strip():
            st.error("홈팀 명과 어웨이팀 명은 필수 입력 항목입니다.")
        else:
            with st.spinner("구글 시트에 현장 메모를 임시 저장하는 중..."):
                final_home_nums = {pos: st.session_state.get(f"home_{pos}", "") for row in formation_layouts[home_formation] for pos in row['positions'] if st.session_state.get(f"home_{pos}", "").strip()}
                final_away_nums = {pos: st.session_state.get(f"away_{pos}", "") for row in formation_layouts[away_formation] for pos in row['positions'] if st.session_state.get(f"away_{pos}", "").strip()}

                home_num_str = ", ".join([f"{pos}:#{num}" for pos, num in final_home_nums.items()]) if final_home_nums else "없음"
                away_num_str = ", ".join([f"{pos}:#{num}" for pos, num in final_away_nums.items()]) if final_away_nums else "없음"

                player_notes_formatted = ""
                if player_specific_memos:
                    player_notes_formatted = "\n\n⭐ [선수별 집중 관찰 메모]\n"
                    for p_label, p_note in player_specific_memos.items():
                        player_notes_formatted += f"- {p_label}:\n  {p_note}\n"

                memo_overall = (
                    f"📅 일자: {match_date} | 대회: {tournament_name}\n\n"
                    f"🏠 [홈팀: {home_team}] 포메이션: {home_formation}\n"
                    f"- 포지션별 등번호: {home_num_str}\n\n"
                    f"✈️ [어웨이팀: {away_team}] 포메이션: {away_formation}\n"
                    f"- 포지션별 등번호: {away_num_str}"
                    f"{player_notes_formatted}\n\n"
                    f"📝 [경기 전체 총평]\n{general_memo}"
                )

                new_memo_data = {
                    "선수명": f"[{tournament_name}] {home_team} vs {away_team}",
                    "소속팀": f"{home_team} (홈) vs {away_team} (어웨이)",
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
                    st.success("🎉 현장 경기 관찰 메모가 임시 저장되었습니다!")
                    st.balloons()

# ----------------------------------------------------
# 2. 📂 경기 일지 조회
# ----------------------------------------------------
elif menu == "📂 경기 일지 조회":
    st.header("📂 현장 경기 관찰 일지 모음")
    memo_df = df[df["진행 상태"].str.strip() == "현장 관찰 메모 (임시)"].copy().reset_index(drop=True)

    if memo_df.empty:
        st.info("아직 저장된 경기 관찰 일지가 없습니다.")
    else:
        tab_view, tab_delete = st.tabs(["📋 일지 목록 및 조회/다운로드", "🗑️ 일지 일괄 삭제"])
        with tab_view:
            memo_df_sorted = memo_df.sort_values(by="작성일자", ascending=False).reset_index(drop=True) if "작성일자" in memo_df.columns else memo_df.copy()
            
            search_query = st.text_input("🔍 검색어 입력", key="memo_search_box")
            filtered_memo_df = memo_df_sorted[memo_df_sorted["선수명"].str.contains(search_query, case=False, na=False) | memo_df_sorted["소속팀"].str.contains(search_query, case=False, na=False)] if search_query else memo_df_sorted

            display_memo_df = filtered_memo_df[["작성일자", "선수명", "소속팀", "장점/특기"]].copy()
            display_memo_df.columns = ["작성일자", "대회 및 대진", "홈 vs 어웨이", "대회 정보"]

            memo_selection = st.dataframe(display_memo_df, use_container_width=True, selection_mode="single-row", on_select="rerun")
            selected_memo_rows = memo_selection.selection.rows if hasattr(memo_selection, "selection") else []

            if selected_memo_rows:
                selected_row_filtered = filtered_memo_df.iloc[selected_memo_rows[0]]
                match_indices = df[(df["선수명"] == selected_row_filtered["선수명"]) & (df["소속팀"] == selected_row_filtered["소속팀"]) & (df["작성일자"] == selected_row_filtered["작성일자"]) & (df["진행 상태"] == "현장 관찰 메모 (임시)")].index

                if len(match_indices) > 0:
                    target_memo_idx = match_indices[0]
                    p_memo = df.loc[target_memo_idx]
                    raw_content = str(p_memo.get("종합 평가", ""))

                    st.write("---")
                    
                    act_col1, act_col2 = st.columns([3, 1])
                    with act_col1:
                        st.markdown(f"### ⚽ {p_memo.get('선수명')}")
                        st.markdown(f"**🗓️ 일자:** {p_memo.get('작성일자')} | **대진:** {p_memo.get('소속팀')}")
                    with act_col2:
                        try:
                            pdf_bytes = generate_pdf_report_for_memo(p_memo)
                            filename = f"{p_memo.get('선수명').replace(' ', '_')}_경기일지.pdf"
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

                    st.write("---")
                    st.markdown("**📝 저장된 경기 관찰 기록**")
                    st.info(raw_content)

                    st.write("")
                    if st.button("🗑️ 해당 경기 일지 삭제", type="secondary", key=f"del_memo_single_{target_memo_idx}"):
                        updated_df = df.drop([target_memo_idx]).reset_index(drop=True)
                        if save_data_to_sheet(updated_df):
                            st.success("삭제되었습니다!")
                            st.rerun()

        with tab_delete:
            st.subheader("🗑️ 경기 일지 일괄 삭제")
            del_selection = st.dataframe(memo_df[["작성일자", "선수명", "소속팀"]], use_container_width=True, selection_mode="multi-row", on_select="rerun")
            selected_del_rows = del_selection.selection.rows if hasattr(del_selection, "selection") else []
            if selected_del_rows and st.button("🗑️ 선택한 일지 영구 삭제", type="primary"):
                indices_to_drop = [df[(df["선수명"] == memo_df.iloc[r]["선수명"]) & (df["소속팀"] == memo_df.iloc[r]["소속팀"]) & (df["작성일자"] == memo_df.iloc[r]["작성일자"])].index[0] for r in selected_del_rows if r < len(memo_df)]
                if indices_to_drop:
                    if save_data_to_sheet(df.drop(indices_to_drop).reset_index(drop=True)):
                        st.success("삭제 완료!")
                        st.rerun()

# ----------------------------------------------------
# 3. 선수 등록
# ----------------------------------------------------
elif menu == "선수 등록":
    st.header("📋 신규 관찰 선수 등록")
    with st.form("player_reg_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("선수명*")
            team = st.text_input("현재 소속팀")
            position = st.selectbox("포지션", options=POSITION_OPTIONS)
            status = st.selectbox("진행 상태", STATUS_OPTIONS)
            back_num = st.selectbox("등번호", options=[""] + [str(i) for i in range(1, 100)])
        with col2:
            birth_date = st.date_input("생년월일", value=datetime(2005, 1, 1))
            foot = st.selectbox("주발", ["오른발", "왼발", "양발"])
            date = st.date_input("작성일자", value=datetime.today())
            h_val = st.text_input("신장 (cm)", value="175")
            w_val = st.text_input("체중 (kg)", value="70")
        pros = st.text_area("장점 및 주요 특기")
        cons = st.text_area("보완점 및 약점")
        overall = st.text_area("종합 평가")
        if st.form_submit_button("💾 선수 데이터 저장", type="primary", use_container_width=True):
            if not name.strip():
                st.error("선수명은 필수입니다.")
            else:
                af, ay = calculate_age(birth_date)
                nd = {"선수명": name.strip(), "소속팀": team.strip(), "등번호": str(back_num), "포지션": position, "생년월일": str(birth_date), "만 나이": af, "연 나이": ay, "주발": foot, "신장(cm)": h_val, "체중(kg)": w_val, "진행 상태": status, "장점/특기": pros.strip(), "보완점/단점": cons.strip(), "종합 평가": overall.strip(), "작성일자": str(date)}
                if save_data_to_sheet(pd.DataFrame([nd]) if df.empty else pd.concat([df, pd.DataFrame([nd])], ignore_index=True)):
                    st.success("저장 완료!")
                    st.rerun()

# ----------------------------------------------------
# 4. 선수 검색 및 관찰일지 조회
# ----------------------------------------------------
elif menu == "🔍 선수 검색 및 관찰일지 조회":
    st.header("🔍 관찰 선수 검색 및 상세 일지")
    official_df = df[df["진행 상태"].str.strip() != "현장 관찰 메모 (임시)"].copy().reset_index(drop=True)
    if official_df.empty:
        st.info("등록된 선수가 없습니다.")
    else:
        st_term = st.text_input("🔍 검색 (선수명, 팀명 등)")
        f_df = official_df[official_df["선수명"].str.contains(st_term, case=False, na=False) | official_df["소속팀"].str.contains(st_term, case=False, na=False)] if st_term else official_df
        sel = st.dataframe(f_df, use_container_width=True, selection_mode="single-row", on_select="rerun")
        s_rows = sel.selection.rows if hasattr(sel, "selection") else []
        if s_rows:
            target_idx = df[(df["선수명"] == f_df.iloc[s_rows[0]]["선수명"]) & (df["소속팀"] == f_df.iloc[s_rows[0]]["소속팀"])].index[0]
            p = df.loc[target_idx]
            st.write("---")
            head_c1, head_c2 = st.columns([3, 1])
            with head_c1:
                st.markdown(f"### ⚽ {p.get('선수명')}")
            with head_c2:
                pdf_bytes = generate_pdf_report(p)
                b64 = base64.b64encode(pdf_bytes.getvalue()).decode()
                st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="{p.get("선수명")}_리포트.pdf" style="background:#2563EB;color:white;padding:8px 12px;border-radius:6px;text-decoration:none;font-weight:bold;display:block;text-align:center;">📄 PDF 다운로드</a>', unsafe_allow_html=True)
            st.info(f"소속: {p.get('소속팀')} | 포지션: {p.get('포지션')} | 등번호: {p.get('등번호')}")
            st.markdown(f"**장점:** {p.get('장점/특기')}")
            st.markdown(f"**단점:** {p.get('보완점/단점')}")
            st.markdown(f"**평가:** {p.get('종합 평가')}")

# ----------------------------------------------------
# 5. 데이터 삭제
# ----------------------------------------------------
elif menu == "🗑️ 데이터 삭제":
    st.header("🗑️ 선수 데이터 삭제")
    if df.empty:
        st.info("데이터가 없습니다.")
    else:
        del_sel = st.dataframe(df, use_container_width=True, selection_mode="multi-row", on_select="rerun")
        d_rows = del_sel.selection.rows if hasattr(del_sel, "selection") else []
        if d_rows and st.button("🗑️ 선택한 선수 영구 삭제", type="primary"):
            if save_data_to_sheet(df.drop(d_rows).reset_index(drop=True)):
                st.success("삭제 완료!")
                st.rerun()
