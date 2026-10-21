import streamlit as st
import pandas as pd
import requests
import io
import os
import base64
from datetime import datetime

# PDF 생성을 위한 reportlab 라이브러리 및 폰트 등록 모듈
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
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
# 📱 깔끔하고 안정적인 기본 CSS 스타일 및 잔디 피치 스타일
# ----------------------------------------------------
st.markdown("""
    <style>
    .block-container {
        padding-top: 2.5rem !important;
        padding-bottom: 2.5rem !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 2rem !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        padding: 12px 16px !important;
        margin-bottom: 8px !important;
        border-radius: 10px;
        background-color: rgba(255, 255, 255, 0.05);
        cursor: pointer;
    }
    
    /* ⚽ 잔디 피치 작전판 그라운드 박스 스타일 */
    .match-soccer-pitch {
        background: radial-gradient(circle, #2e8b57 0%, #154335 100%);
        border: 4px solid #ffffff;
        border-radius: 18px;
        padding: 20px 15px;
        box-shadow: inset 0 0 40px rgba(0,0,0,0.6), 0 8px 20px rgba(0,0,0,0.4);
        margin-bottom: 15px;
    }
    
    /* 🔴 피치 위 포지션 핀 스타일 */
    .match-pitch-pin {
        background: radial-gradient(circle, #ff5252 0%, #b71c1c 100%);
        color: white;
        border: 2.5px solid #ffffff;
        border-radius: 50%;
        width: 54px;
        height: 54px;
        margin: 0 auto 4px auto;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.4);
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# 🔗 1. 구글 시트 공유 링크
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1WSbVkwCr5Dv5hN3zU0Bw5tzzbNjMmlFyZiOCpG5DRjI/edit?usp=sharing"

# 🔗 2. 구글 Apps Script 웹앱 URL
GOOGLE_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxTTvgJqNnmBxwuCGvT3agMEo0_0Fon0JGWdREyR7usEIu4Mfw9M1lq66njtr8S_cbP/exec"

STATUS_OPTIONS = ["관심 선수 (Watchlist)", "집중 관찰 중", "컨택 완료", "계약 검토", "보류 / 제외"]
POSITION_OPTIONS = ["GK", "CB", "LB", "RB", "MF", "LW", "RW", "CF"]

# ----------------------------------------------------
# 🏢 성문컴퍼니(SMC) 로고 렌더링
# ----------------------------------------------------
def display_logo():
    logo_html = """
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; padding: 5px 0 15px 0; margin-bottom: 5px;">
        <div style="color: #007bff; font-weight: 900; letter-spacing: 4px; font-size: 28px; font-family: sans-serif; line-height: 1.1;">SMC</div>
        <div style="color: #6c757d; font-weight: 700; letter-spacing: 3px; font-size: 10px; font-family: sans-serif; margin-top: 4px;">SUNGMUN COMPANY</div>
    </div>
    """
    st.sidebar.markdown(logo_html, unsafe_allow_html=True)

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

def safe_int(val, default_val):
    try:
        cleaned = str(val).replace('.0', '').strip()
        return int(cleaned) if cleaned.isdigit() else default_val
    except:
        return default_val

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

# 포메이션별 라인업 구조 데이터 정의
formation_layouts = {
    "4-3-3": [
        {"line": "FW LINE", "positions": ["LW", "CF", "RW"]},
        {"line": "MF LINE", "positions": ["LCM", "CDM", "RCM"]},
        {"line": "DF LINE", "positions": ["LB", "CB1", "CB2", "RB"]},
        {"line": "GK LINE", "positions": ["GK"]}
    ],
    "4-4-2": [
        {"line": "FW LINE", "positions": ["ST1", "ST2"]},
        {"line": "MF LINE", "positions": ["LM", "LCM", "RCM", "RM"]},
        {"line": "DF LINE", "positions": ["LB", "CB1", "CB2", "RB"]},
        {"line": "GK LINE", "positions": ["GK"]}
    ],
    "4-2-3-1": [
        {"line": "FW LINE", "positions": ["ST"]},
        {"line": "AM LINE", "positions": ["LAM", "CAM", "RAM"]},
        {"line": "DM LINE", "positions": ["LDM", "RDM"]},
        {"line": "DF LINE", "positions": ["LB", "CB1", "CB2", "RB"]},
        {"line": "GK LINE", "positions": ["GK"]}
    ],
    "3-4-3": [
        {"line": "FW LINE", "positions": ["LW", "CF", "RW"]},
        {"line": "MF LINE", "positions": ["LM", "LCM", "RCM", "RM"]},
        {"line": "DF LINE", "positions": ["CB1", "CB2", "CB3"]},
        {"line": "GK LINE", "positions": ["GK"]}
    ],
    "3-5-2": [
        {"line": "FW LINE", "positions": ["ST1", "ST2"]},
        {"line": "MF LINE", "positions": ["LWB", "LCM", "CDM", "RCM", "RWB"]},
        {"line": "DF LINE", "positions": ["CB1", "CB2", "CB3"]},
        {"line": "GK LINE", "positions": ["GK"]}
    ]
}

def render_pitch_graphic_from_saved(team_name, formation_name, num_dict):
    st.markdown(f"""
    <div class="match-soccer-pitch">
        <div style="text-align: center; color: #ffeb3b; font-weight: 900; font-size: 15px; letter-spacing: 2px; text-shadow: 2px 2px 4px #000; margin-bottom: 8px;">
            🏟️ {team_name} ({formation_name})
        </div>
    """, unsafe_allow_html=True)
    
    layout = formation_layouts.get(formation_name, formation_layouts["4-3-3"])
    
    for row in layout:
        st.markdown(f"<div style='color:#a3e4d7; font-weight:bold; font-size:10px; margin-bottom:2px;'>📍 {row['line']}</div>", unsafe_allow_html=True)
        cols = st.columns(len(row['positions']))
        for idx, pos in enumerate(row['positions']):
            assigned_num = num_dict.get(pos, "")
            display_num = assigned_num if assigned_num else pos

            with cols[idx]:
                st.markdown(f"""
                <div class="match-pitch-pin">
                    <span style="font-size: 8px; color: #ffeb3b;">{pos}</span>
                    <span style="font-size: 11px; line-height: 1.1;">{display_num}</span>
                </div>
                """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# 사이드바 로고 및 메뉴 구성
display_logo()

st.sidebar.title("📌 메뉴")
if st.sidebar.button("🔄 앱 새로고침", use_container_width=True, type="secondary"):
    st.rerun()

st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "이동할 메뉴",
    [
        "🏟️ 현장 경기 관찰 메모", 
        "📂 경기 일지 조회", 
        "선수 등록", 
        "🔍 선수 검색 및 관찰일지 조회", 
        "✏️ 선수 정보/일지 수정 및 삭제"
    ]
)

st.title("⚽ 선수 스카우팅 관리 시스템")

# ----------------------------------------------------
# 1. 🏟️ 현장 경기 관찰 메모
# ----------------------------------------------------
if menu == "🏟️ 현장 경기 관찰 메모":
    st.header("🏟️ 현장 경기 관찰 메모장")
    st.caption("경기를 보며 등번호나 메모를 중간중간 추가해도 작성 중인 내용이 날아가지 않고 유지됩니다.")

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        match_date = st.date_input("경기 일자", value=datetime.today())
    with col_m2:
        tournament_name = st.text_input("대회 이름", placeholder="예: 금석배 U18, 대통령배 등")

    st.write("---")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        home_team = st.text_input("🏠 홈팀 명*", value="홈팀")
        home_formation = st.selectbox("홈팀 포메이션", ["4-3-3", "4-4-2", "4-2-3-1", "3-4-3", "3-5-2"], key="home_form")
    with col_t2:
        away_team = st.text_input("✈️ 어웨이팀 명*", value="어웨이팀")
        away_formation = st.selectbox("어웨이팀 포메이션", ["4-3-3", "4-4-2", "4-2-3-1", "3-4-3", "3-5-2"], key="away_form")

    st.write("---")

    def render_team_pitch_with_inputs(team_name, formation_name, prefix):
        st.markdown(f"### 🛡️ [{team_name}] 포메이션 및 등번호 입력 ({formation_name})")
        layout = formation_layouts.get(formation_name, formation_layouts["4-3-3"])
        
        team_entered_numbers = {}

        st.markdown(f"""
        <div class="match-soccer-pitch">
            <div style="text-align: center; color: #ffeb3b; font-weight: 900; font-size: 15px; letter-spacing: 2px; text-shadow: 2px 2px 4px #000; margin-bottom: 8px;">
                🏟️ {team_name} ({formation_name})
            </div>
        """, unsafe_allow_html=True)
        
        for row in layout:
            st.markdown(f"<div style='color:#a3e4d7; font-weight:bold; font-size:10px; margin-bottom:2px;'>📍 {row['line']}</div>", unsafe_allow_html=True)
            cols = st.columns(len(row['positions']))
            for idx, pos in enumerate(row['positions']):
                key_name = f"{prefix}_{pos}"
                current_num = st.session_state.get(key_name, "")
                display_num = current_num if current_num else pos

                with cols[idx]:
                    st.markdown(f"""
                    <div class="match-pitch-pin">
                        <span style="font-size: 8px; color: #ffeb3b;">{pos}</span>
                        <span style="font-size: 11px; line-height: 1.1;">{display_num}</span>
                    </div>
                    """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(f"**📝 {team_name} 포지션별 등번호 기입**")
        for row in layout:
            cols_input = st.columns(len(row['positions']))
            for idx, pos in enumerate(row['positions']):
                key_name = f"{prefix}_{pos}"
                with cols_input[idx]:
                    val = st.text_input(f"{pos}", value=st.session_state.get(key_name, ""), key=key_name, placeholder="등번호")
                    if val.strip():
                        team_entered_numbers[pos] = val.strip()
        
        return team_entered_numbers

    pitch_col1, pitch_col2 = st.columns(2)
    with pitch_col1:
        home_numbers = render_team_pitch_with_inputs(home_team if home_team else "홈팀", home_formation, "home")
    with pitch_col2:
        away_numbers = render_team_pitch_with_inputs(away_team if away_team else "어웨이팀", away_formation, "away")

    st.write("---")

    st.subheader("⭐ 눈에 띈 선수별 집중 메모")
    st.caption("위에서 등번호가 기입된 선수들 중 메모를 남기고 싶은 선수를 선택하세요.")

    active_players = []
    for pos, num in home_numbers.items():
        active_players.append(f"[홈] {home_team} - {pos} (#{num})")
    for pos, num in away_numbers.items():
        active_players.append(f"[어웨이] {away_team} - {pos} (#{num})")

    player_specific_memos = {}

    if active_players:
        selected_players_to_memo = st.multiselect(
            "관찰 메모를 작성할 선수 선택",
            options=active_players,
            placeholder="메모할 선수를 체크하세요 (복수 선택 가능)",
            key="selected_memo_players_multiselect"
        )

        if selected_players_to_memo:
            st.markdown("---")
            for player_label in selected_players_to_memo:
                st.markdown(f"**📌 {player_label} 관찰 기록**")
                memo_key = f"memo_desc_{player_label}"
                player_note = st.text_area(
                    f"{player_label}에 대한 세부 메모",
                    value=st.session_state.get(memo_key, ""),
                    placeholder="장점, 플레이 스타일, 특이사항 등을 적어주세요...",
                    key=memo_key,
                    height=100
                )
                if player_note.strip():
                    player_specific_memos[player_label] = player_note.strip()
    else:
        st.info("💡 위 포메이션 입력창에 선수 등번호를 기입하면, 여기에 선수별 메모장 활성화 체크박스가 나타납니다.")

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
            st.error("홈팀 명과 어웨이팀 명은 필수 입력 항목입니다.")
        else:
            with st.spinner("구글 시트에 현장 메모를 저장하는 중..."):
                home_num_str = ", ".join([f"{pos}:{num}" for pos, num in home_numbers.items()]) if home_numbers else "없음"
                away_num_str = ", ".join([f"{pos}:{num}" for pos, num in away_numbers.items()]) if away_numbers else "없음"

                player_notes_formatted = ""
                if player_specific_memos:
                    player_notes_formatted = "\n\n⭐ [선수별 집중 관찰 메모]\n"
                    for p_label, p_note in player_specific_memos.items():
                        player_notes_formatted += f"- {p_label}:\n  {p_note}\n"

                memo_player_name = f"[{tournament_name}] {home_team} vs {away_team}"
                memo_team = f"{home_team} (홈) vs {away_team} (어웨이)"
                
                memo_overall = (
                    f"📅 일자: {match_date} | 대회: {tournament_name}\n"
                    f"[META_HOME_FORM:{home_formation}]\n"
                    f"[META_HOME_NUMS:{home_num_str}]\n"
                    f"[META_AWAY_FORM:{away_formation}]\n"
                    f"[META_AWAY_NUMS:{away_num_str}]\n\n"
                    f"🏠 [홈팀: {home_team}] 포메이션: {home_formation}\n"
                    f"- 포지션별 등번호: {home_num_str.replace(':', ': #')}\n\n"
                    f"✈️ [어웨이팀: {away_team}] 포메이션: {away_formation}\n"
                    f"- 포지션별 등번호: {away_num_str.replace(':', ': #')}"
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
                    st.success("🎉 현장 경기 관찰 메모가 구글 시트에 성공적으로 저장되었습니다!")
                    st.balloons()

# ----------------------------------------------------
# 2. 📂 경기 일지 조회 (현장 관찰 메모 데이터만 엄격하게 분리)
# ----------------------------------------------------
elif menu == "📂 경기 일지 조회":
    st.header("📂 현장 경기 관찰 일지 모음")
    st.caption("팀명, 날짜, 대회명으로 검색하고 리스트에서 행을 선택하여 당시 포메이션 피치 시각화, PDF 다운로드, 데이터 삭제를 수행하세요.")

    # ⚠️ 수정 포인트: 진행 상태가 정확히 "현장 관찰 메모 (임시)"인 데이터만 엄격하게 필터링
    memo_df = df[df["진행 상태"].str.strip() == "현장 관찰 메모 (임시)"].copy()

    if memo_df.empty:
        st.info("아직 저장된 경기 관찰 일지가 없습니다. [🏟️ 현장 경기 관찰 메모] 메뉴에서 첫 일지를 작성해 보세요!")
    else:
        if "작성일자" in memo_df.columns:
            memo_df = memo_df.sort_values(by="작성일자", ascending=False).reset_index(drop=True)

        sc_col1, sc_col2 = st.columns([3, 1])
        with sc_col1:
            search_query = st.text_input("🔍 검색어 입력 (팀명, 대회명, 날짜 등)", placeholder="예: 안산, 금석배, 2026-03 등", key="memo_search_box")
        with sc_col2:
            available_months = ["전체"]
            if "작성일자" in memo_df.columns:
                months_extracted = memo_df["작성일자"].apply(lambda x: str(x)[:7] if pd.notna(x) and len(str(x)) >= 7 else "").unique()
                months_extracted = sorted([m for m in months_extracted if m and m != "nat"], reverse=True)
                available_months.extend(months_extracted)
            
            selected_month_filter = st.selectbox("📅 월별 필터", options=available_months, key="memo_month_filter")

        filtered_memo_df = memo_df.copy()
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

        st.subheader("📋 경기 일지 목록 (조회할 일지를 **클릭**하세요)")

        if filtered_memo_df.empty:
            st.warning("🔍 검색 조건에 일치하는 경기 일지가 없습니다.")
        else:
            display_memo_df = filtered_memo_df[["작성일자", "선수명", "소속팀", "장점/특기"]].copy()
            display_memo_df.columns = ["작성일자", "대회 및 대진", "홈 vs 어웨이", "대회 정보"]

            memo_selection = st.dataframe(
                display_memo_df,
                use_container_width=True,
                selection_mode="single-row",
                on_select="rerun"
            )

            selected_memo_rows = memo_selection.selection.rows if hasattr(memo_selection, "selection") else []

            if selected_memo_rows:
                target_memo_idx = filtered_memo_df.index[selected_memo_rows[0]]
                p_memo = df.loc[target_memo_idx]

                match_title = p_memo.get("선수명", "경기 기록")
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
                st.markdown("**📝 상세 관찰 기록 및 총평**")
                st.info(clean_content)

                st.write("")
                if st.button("⚠️ 이 경기 일지 영구 삭제하기", type="secondary", use_container_width=True, key=f"btn_del_memo_{target_memo_idx}"):
                    with st.spinner("구글 시트에서 일지를 삭제하는 중..."):
                        df = df.drop(target_memo_idx).reset_index(drop=True)
                        if save_data_to_sheet(df):
                            st.success("🗑️ 경기 일지가 성공적으로 삭제되었습니다! 페이지를 갱신합니다.")
                            st.rerun()
            else:
                st.info("💡 위 목록 표에서 조회할 **경기 일지 행을 클릭**하시면 하단에 상세 내용과 시각화 화면이 나타납니다.")

# ----------------------------------------------------
# 3. 선수 정식 등록
# ----------------------------------------------------
elif menu == "선수 등록":
    st.header("📋 신규 관찰 선수 정식 등록")
    
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
            
            st.write("---")
            height_options = [str(h) for h in range(150, 205)] + [""]
            height_val = st.selectbox("신장 (cm)", options=height_options, index=25, placeholder="신장 선택")
            
            weight_options = [""] + [str(w) for w in range(50, 105)]
            weight_val = st.selectbox("체중 (kg)", options=weight_options, index=0, placeholder="체중 선택")

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
                        "신장(cm)": str(height_val), "체중(kg)": str(weight_val),
                        "진행 상태": status, "장점/특기": pros.strip(), "보완점/단점": cons.strip(),
                        "종합 평가": overall.strip(), "작성일자": str(date)
                    }
                    updated_df = pd.DataFrame([new_data]) if df.empty else pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                    if save_data_to_sheet(updated_df):
                        st.session_state["reg_success_msg"] = f"🎉 '{name.strip()}' 선수의 데이터가 구글 시트에 성공적으로 저장되었습니다!"
                        st.rerun()

# ----------------------------------------------------
# 4. 선수 검색 및 상세 관찰일지 조회 & PDF 다운로드 (현장 메모 제외)
# ----------------------------------------------------
elif menu == "🔍 선수 검색 및 관찰일지 조회":
    st.header("🔍 관찰 선수 검색 및 상세 일지 / PDF 다운로드")
    
    # ⚠️ 수정 포인트: 정식 등록된 선수들만 대상으로 필터링 (현장 메모 제외)
    official_df = df[df["진행 상태"].str.strip() != "현장 관찰 메모 (임시)"].copy()
    
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
        
        st.subheader(f"📋 목록 (클릭 시 하단에 상세 내용 표출)")
        
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
            target_idx = filtered_df.index[selected_rows[0]]
            p = df.loc[target_idx]
            
            current_team_name, past_team_history = parse_team_info(p.get('소속팀', ''))
            
            st.write("---")
            
            head_col1, head_col2 = st.columns([3, 1])
            with head_col1:
                st.markdown(f"### ⚽ [{p.get('진행 상태', '')}] {p.get('선수명', '')}")
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
            
            st.write(f"• **작성일자**: {p.get('작성일자', '-')}")
            st.markdown("---")

            st.subheader("📚 상세 메모 및 분석 내용")
            with st.container():
                overall_text = p.get('종합 평가', '')
                if pd.notna(overall_text) and str(overall_text).strip():
                    st.info(overall_text)
                else:
                    st.write("등록된 내용이 없습니다.")
        else:
            st.info("💡 목록 표에서 조회하고 싶은 **행을 클릭**하시면 상세 내용이 하단에 나타납니다.")

# ----------------------------------------------------
# 5. 선수 정보 수정 및 삭제 (현장 메모 제외)
# ----------------------------------------------------
elif menu == "✏️ 선수 정보/일지 수정 및 삭제":
    st.header("✏️ 기존 정보 수정 및 데이터 삭제")
    
    # ⚠️ 수정 포인트: 정식 등록된 선수들만 대상으로 수정/삭제 처리
    edit_base_df = df[df["진행 상태"].str.strip() != "현장 관찰 메모 (임시)"].copy()
    
    if edit_base_df.empty:
        st.info("수정할 선수 데이터가 없습니다.")
    else:
        st.subheader("📋 수정 또는 삭제할 항목을 표에서 **클릭**하세요")
        
        s_col1, s_col2 = st.columns([2, 1])
        with s_col1:
            edit_search = st.text_input("🔍 검색어 입력", key="edit_grid_search")
        with s_col2:
            edit_pos_filter = st.selectbox("🛡️ 포지션 필터", ["전체"] + POSITION_OPTIONS, key="edit_grid_pos")
            
        edit_filtered_df = edit_base_df.copy()
        if edit_search.strip():
            edit_filtered_df = edit_filtered_df[
                edit_filtered_df["선수명"].str.contains(edit_search, case=False, na=False) |
                edit_filtered_df["소속팀"].str.contains(edit_search, case=False, na=False) |
                edit_filtered_df["등번호"].str.contains(edit_search, case=False, na=False)
            ]
        if edit_pos_filter != "전체":
            edit_filtered_df = edit_filtered_df[edit_filtered_df["포지션"].str.strip() == edit_pos_filter]
            
        edit_display_cols = [c for c in edit_filtered_df.columns if c != "연 나이"]
        edit_display_df = edit_filtered_df[edit_display_cols].copy()
        edit_display_df["소속팀"] = edit_display_df["소속팀"].apply(lambda x: parse_team_info(x)[0])
        
        if not edit_display_df.empty:
            edit_selection = st.dataframe(
                edit_display_df,
                use_container_width=True,
                selection_mode="single-row",
                on_select="rerun"
            )
        else:
            edit_selection = st.dataframe(
                edit_display_df,
                use_container_width=True,
                selection_mode="single-row",
                on_select="rerun"
            )
            
        edit_selected_rows = edit_selection.selection.rows if hasattr(edit_selection, "selection") else []
        
        if edit_selected_rows:
            target_idx = edit_filtered_df.index[edit_selected_rows[0]]
            target_row = df.loc[target_idx]
            
            current_t, past_t = parse_team_info(target_row.get("소속팀", ""))
            
            st.write("---")

            st.markdown(f"### 🗑️ [{target_row.get('선수명', '')}] 데이터 삭제")
            if st.button("⚠️ 이 데이터를 영구 삭제하기", type="secondary", use_container_width=True, key=f"btn_delete_{target_idx}"):
                with st.spinner("구글 시트에서 데이터를 삭제하는 중..."):
                    df = df.drop(target_idx).reset_index(drop=True)
                    if save_data_to_sheet(df):
                        st.success("🗑️ 데이터가 성공적으로 삭제되었습니다! 페이지를 갱신합니다.")
                        st.rerun()

            st.write("---")
            st.markdown(f"### ✏️ [{target_row.get('선수명', '')}] 정보 수정")
            
            col1, col2 = st.columns(2)
            with col1:
                edit_name = st.text_input("이름 / 제목", value=str(target_row.get("선수명", "")), key=f"edit_name_{target_idx}")
                edit_team_input = st.text_input("소속팀 / 대진", value=current_t, key=f"edit_team_{target_idx}")
                
                cur_pos = str(target_row.get("포지션", "MF"))
                pos_idx = POSITION_OPTIONS.index(cur_pos) if cur_pos in POSITION_OPTIONS else 2
                edit_position = st.selectbox("포지션", POSITION_OPTIONS, index=pos_idx, key=f"edit_pos_{target_idx}")
                
                default_status = str(target_row.get("진행 상태", STATUS_OPTIONS[0]))
                status_index = STATUS_OPTIONS.index(default_status) if default_status in STATUS_OPTIONS else 0
                edit_status = st.selectbox("진행 상태", STATUS_OPTIONS, index=status_index, key=f"edit_status_{target_idx}")
                
                cur_num = str(target_row.get("등번호", "")).strip()
                back_num_options = ["-"] + [str(i) for i in range(1, 100)]
                num_idx = back_num_options.index(cur_num) if cur_num in back_num_options else 0
                edit_back_num = st.selectbox("등번호", options=back_num_options, index=num_idx, key=f"edit_num_{target_idx}")

            with col2:
                default_birth = parse_date(target_row.get("생년월일"))
                edit_birth_date = st.date_input("생년월일", value=default_birth, key=f"edit_birth_{target_idx}")
                age_full_str, age_year_str = calculate_age(edit_birth_date)
                
                default_foot = str(target_row.get("주발", "오른발"))
                foot_options = ["오른발", "왼발", "양발"]
                foot_index = foot_options.index(default_foot) if default_foot in foot_options else 0
                edit_foot = st.selectbox("주발", foot_options, index=foot_index, key=f"edit_foot_{target_idx}")
                
                edit_date = st.date_input("관찰 작성일자", value=datetime.today(), key=f"edit_date_{target_idx}")
                
                cur_h = safe_int(target_row.get("신장(cm)", ""), 175)
                cur_w = safe_int(target_row.get("체중(kg)", ""), 70)
                
                h_options = [str(h) for h in range(150, 205)]
                h_idx = h_options.index(str(cur_h)) if str(cur_h) in h_options else 25
                edit_height = st.selectbox("신장 (cm)", options=h_options + [""], index=h_idx, key=f"edit_h_{target_idx}")
                
                w_options = [str(w) for w in range(50, 105)]
                w_idx = w_options.index(str(cur_w)) if str(cur_w) in w_options else 20
                edit_weight = st.selectbox("체중 (kg)", options=[""] + w_options, index=w_idx + 1 if str(cur_w) in w_options else 0, key=f"edit_w_{target_idx}")

            st.subheader("➕ 메모 내용 수정")
            edit_overall = st.text_area("상세 내용 / 종합 평가", value=str(target_row.get("종합 평가", "")), height=150, key=f"edit_overall_{target_idx}")
            
            if st.button("🔄 변경사항 저장하기", type="primary", use_container_width=True, key=f"btn_save_{target_idx}"):
                if not edit_name.strip():
                    st.error("이름은 필수입니다.")
                else:
                    with st.spinner("구글 시트에 업데이트하는 중..."):
                        df.loc[target_idx, "선수명"] = edit_name.strip()
                        df.loc[target_idx, "소속팀"] = edit_team_input.strip()
                        df.loc[target_idx, "등번호"] = str(edit_back_num)
                        df.loc[target_idx, "포지션"] = edit_position
                        df.loc[target_idx, "진행 상태"] = edit_status
                        df.loc[target_idx, "생년월일"] = str(edit_birth_date)
                        df.loc[target_idx, "만 나이"] = age_full_str
                        df.loc[target_idx, "연 나이"] = age_year_str
                        df.loc[target_idx, "주발"] = edit_foot
                        df.loc[target_idx, "신장(cm)":] = str(edit_height)
                        df.loc[target_idx, "체중(kg)"] = str(edit_weight)
                        df.loc[target_idx, "종합 평가"] = edit_overall.strip()
                        df.loc[target_idx, "작성일자"] = str(edit_date)

                        if save_data_to_sheet(df):
                            st.success("🎉 정보가 성공적으로 업데이트되었습니다!")
                            st.rerun()
