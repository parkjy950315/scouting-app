import streamlit as st
import pandas as pd
import requests
import io
import re
import os
import base64
from datetime import datetime

# ----------------------------------------------------
# 📌 세션 상태 및 메뉴 전환 사전 초기화 (StreamlitWidgetAlreadyInstantiatedError 방지)
# ----------------------------------------------------
if "menu_selection" not in st.session_state:
    st.session_state["menu_selection"] = "🏟️ 현장 경기 관찰 메모"

# 메뉴 이동 예약 플래그가 있으면 라디오 버튼 생성 전에 미리 반영
if "redirect_to_menu" in st.session_state:
    st.session_state["menu_selection"] = st.session_state["redirect_to_menu"]
    del st.session_state["redirect_to_menu"]

# 연관검색어 드롭다운을 위한 외부 라이브러리
try:
    from streamlit_searchbox import st_searchbox
except ImportError:
    st.error("⚠️ 'streamlit-searchbox' 라이브러리가 설치되지 않았습니다. requirements.txt에 'streamlit-searchbox'를 추가해 주세요.")

# PDF 생성을 위한 reportlab 라이브러리 및 폰트 등록 모듈
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttffonts import TTFont

# 페이지 기본 설정
st.set_page_config(page_title="선수 스카우팅 DB", page_icon="⚽", layout="wide")

# ----------------------------------------------------
# ⚽ 전국 고등학교 및 대학교 공식 팀 데이터베이스
# ----------------------------------------------------
OFFICIAL_HIGH_SCHOOL_TEAMS = [
    # [서울 고등]
    "YC목동U18", "노원SKDFC U18", "대한FC U18", "더풋볼A U18", "동대부고",
    "영등포선유FC U18", "인터서울U18", "장훈고", "JLFC U18", "NUFC U18", "경신고",
    "보인고", "숭실고", "인창고", "중경고", "중동고", "중앙고", "광운인공지능고", "광진U18", "남강고",
    "대동세무고", "여의도고", "영등포공고", "한양과학기술고", "JHLFC U18", "경희고", "동북고", "배재고",
    "상문고", "서울공고", "용문고", "중대부고", "풋볼A U18", "FC서울 U18 서울오산고",
    # [인천 고등]
    "부평고", "강화스포츠클럽U18", "인천남고", "인천유나이티드 U18 대건고",
    # [경기 고등]
    "HSFA U18", "수원공고", "광문고", "안양공고", "고양고", "평택JFC U18",
    "의정부G스포츠클럽 U18", "FC KHT 일동 U18", "용호고", "광주시G스포츠클럽 U18",
    "SC북내 U18", "수원고", "용인TAESUNGFC U18", "와이엠율면FC U18", "평택진위FC U18",
    "삼일공고", "안산FC U18", "화성서부 U18", "화성시 U18", "계명고", "청운고", "통진고",
    "포천시민축구단 U18", "의정부광동 U18", "초지고", "구리고", "부천SC", "안성 U18", "용인FC U18",
    "FC안양 U18", "김포FC U18", "부천FC1995 U18", "안산그리너스FC U18", "화성FC U18",
    "용인양지FC U18", "김포축구센터 U18", "DHFC U18", "수원삼성 U18 매탄고", "성남FC U18 풍생고",
    "뉴양동FC U18", "능곡고", "이천제일고", "경희FC U18", "GS경수클럽 U18", "김영권축구클럽 U18",
    "의왕시축구협회 U18", "FC광명시민 U18", "서해고", "AEGISFC U18", "부천중동FC U18",
    "HR축구센터 U18", "경기김포축구센터 U18", "남양주U18", "수원FC U18",
    # [강원 고등]
    "강릉문성고", "강릉중앙고", "춘천시민축구단 U18", "상지대관령고", "주천고", "미래고", "강원FC U18 강릉제일고",
    # [충북 고등]
    "충주상고", "제천제일고", "충주충원고", "청주대성고",
    # [충남·대전 고등]
    "신평고", "천안제일고", "천안시티FC U18", "예산삽교FC U18", "서산FC U18",
    "서산시체육회 U18", "천안축구센터 U18", "대전하나시티즌 U18 충남기계공고", "충남아산FC U18",
    # [세종 고등]
    "미래FC U18",
    # [전북 고등]
    "군산제일고", "전주공고", "고창북고", "이리고", "전북현대 U18 전주영생고",
    "정읍신태인축구센터 U18", "새만금FC U18",
    # [전남·광주 고등]
    "목포공고", "영광FC U18", "순천FC U18", "전남드래곤즈 U18 광양제철고", "여수해양FC U18",
    "강진군청자FC", "광주FC U18 금호고",
    # [대구 고등]
    "대륜고", "대구공고", "대구청구고", "대구FC U18 현풍고",
    # [경북 고등]
    "자연과학고", "영덕FC U18", "예일메디텍고", "고령FC", "포항스틸러스 U18 포철고",
    "김천상무FC U18 경북미용예술고", "글로벌선진고", "경북관광비즈니스고", "영천JWFC U18",
    "신라고", "영덕고", "경주정보고",
    # [부산·울산 고등]
    "부경고SC U18", "기장FC U18", "동래고", "부산정보고SC U18", "부산아이파크 U18 개성고",
    "경남공고SC U18", "SC동아 U18", "부산유나이티드 U18", "동명FC U18", "학성고FC U18", "울산HD U18 현대고",
    # [경남 고등]
    "함양FC U18", "보물섬남해스포츠클럽 U18 창선", "합천스포츠클럽FC U18", "거창FC U18",
    "진주외고 U18", "창녕고", "철성고", "거제고", "마산공고", "범어고", "통영고",
    "김해월스포츠 U18", "경남FC U18 진주고",
    # [제주 고등]
    "대기고", "오현고", "제주SK U18", "제주제일고", "제주중앙고", "서귀포고",
    
    # 🎓 [전국 대학교 명단]
    "사이버한국외국어대학교", "제주한라대학교", "고려대학교", "제주관광대학교", "동국대학교",
    "인천대학교", "순복음총신대학교", "동양대학교", "연세대학교", "예원예술대학교",
    "광운대학교", "경민대학교", "강서대학교", "김포대학교", "서울대학교",
    "숭실대학교", "장안대학교", "아주대학교", "연성대학교", "국제사이버대학교",
    "한양대학교", "명지대학교", "수원대학교", "경희대학교", "칼빈대학교",
    "동원대학교", "성균관대학교", "여주대학교", "경기대학교", "홍익대학교",
    "중앙대학교", "용인대학교", "중원대학교", "강동대학교", "상지대학교",
    "송곡대학교", "가톨릭관동대학교", "세경대학교", "송호대학교", "한라대학교",
    "우석대학교", "원광대학교", "목포과학대학교", "전주기전대학교", "전주대학교",
    "호원대학교", "남부대학교", "초당대학교", "광주대학교", "조선대학교",
    "전남과학대학교", "동신대학교", "동강대학교", "호남대학교", "조선이공대학교",
    "배재대학교", "선문대학교", "단국대학교", "청주대학교", "신성대학교",
    "한남대학교", "건국대학교", "안동과학대학교", "경일대학교", "김천대학교",
    "영남대학교", "대구대학교", "위덕대학교", "대구과학대학교", "대경대학교",
    "수성대학교", "동의대학교", "김해대학교", "가야대학교", "대신대학교",
    "동아대학교", "동명대학교", "인제대학교", "구미대학교", "울산대학교"
]

# ----------------------------------------------------
# 🔍 실시간 연관검색어 필터링 함수
# ----------------------------------------------------
def search_team_autocomplete(search_term: str):
    if not search_term or not search_term.strip():
        return OFFICIAL_HIGH_SCHOOL_TEAMS
    q = search_term.strip().lower()
    matches = [t for t in OFFICIAL_HIGH_SCHOOL_TEAMS if q in t.lower()]
    if search_term.strip() not in matches:
        matches.insert(0, search_term.strip())
    return matches

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
# 📱 모바일/PC 반응형 CSS 설정
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
        
        div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
        }
        div[data-testid="stHorizontalBlock"] > div {
            flex: 1 1 50% !important;
            min-width: 0 !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# 🔗 구글 시트 링크 설정
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1WSbVkwCr5Dv5hN3zU0Bw5tzzbNjMmlFyZiOCpG5DRjI/edit?usp=sharing"
GOOGLE_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxTTvgJqNnmBxwuCGvT3agMEo0_0Fon0JGWdREyR7usEIu4Mfw9M1lq66njtr8S_cbP/exec"

STATUS_OPTIONS = ["관심 선수 (Watchlist)", "집중 관찰 중", "컨택 완료", "계약 검토", "보류 / 제외"]
AGENCY_STATUS_OPTIONS = ["소속 선수 (Active Client)", "계약 협상 중", "이전 소속 선수"]
POSITION_OPTIONS = ["GK", "CB", "LCB", "RCB", "LB", "RB", "MF", "LW", "RW", "CF"]

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

# PDF 생성 함수들
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

def render_pitch_graphic_from_saved(team_name, formation_name, num_dict):
    display_team_name = team_name if team_name else "팀명 미입력"
    layout = formation_layouts.get(formation_name, formation_layouts["4-3-3"])
    
    rows_html = ""
    for row in layout:
        rows_html += f"<div style='color:#e2e8f0; font-weight:600; font-size:7.5px; letter-spacing: 0.5px; margin-bottom:1px; text-transform: uppercase; text-align: center;'>📍 {row['line']}</div>"
        rows_html += "<div class='pitch-row'>"
        for pos in row['positions']:
            assigned_num = num_dict.get(pos, "")
            display_num = assigned_num if assigned_num else "-"
            rows_html += f"""
            <div class="player-node">
                <span class="pos-text">{pos}</span>
                <span class="num-text">{display_num}</span>
            </div>
            """
        rows_html += "</div>"

    complete_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        .pitch-container {{
            background: linear-gradient(135deg, #1b4d3e 0%, #2e8b57 50%, #227b4f 100%);
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 14px;
            padding: 8px 4px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.25), inset 0 0 15px rgba(255,255,255,0.1);
            margin-bottom: 10px;
            width: 100%;
            box-sizing: border-box;
            font-family: sans-serif;
        }}
        .pitch-header {{
            text-align: center;
            color: #38bdf8;
            font-weight: 800;
            font-size: 11px;
            letter-spacing: 1px;
            text-transform: uppercase;
            margin-bottom: 4px;
            border-bottom: 1px solid rgba(255,255,255,0.15);
            padding-bottom: 2px;
        }}
        .pitch-row {{
            display: flex;
            justify-content: center;
            gap: 3px;
            margin-bottom: 3px;
            flex-wrap: nowrap;
            width: 100%;
        }}
        .player-node {{
            background: radial-gradient(circle, #ef4444 0%, #b91c1c 100%);
            color: white;
            border: 2px solid rgba(255, 255, 255, 0.95);
            border-radius: 50%;
            width: 28px;
            height: 28px;
            min-width: 28px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        .pos-text {{
            font-size: 5.5px;
            color: #fecaca;
            font-weight: 700;
            line-height: 1;
        }}
        .num-text {{
            font-size: 9.5px;
            color: #ffffff;
            font-weight: 900;
            line-height: 1.1;
        }}
    </style>
    </head>
    <body>
        <div class="pitch-container">
            <div class="pitch-header">
                🏟️ {display_team_name} <span style="color: #cbd5e1; font-size: 9px; font-weight: normal;">({formation_name})</span>
            </div>
            {rows_html}
        </div>
    </body>
    </html>
    """
    import streamlit.components.v1 as components
    components.html(complete_html, height=340, scrolling=False)

display_logo()

st.title("⚽ 선수 스카우팅 관리 시스템")

# ----------------------------------------------------
# 📌 사이드바 설정 (라디오 버튼 생성)
# ----------------------------------------------------
st.sidebar.title("📌 메뉴")

if st.sidebar.button("🔄 앱 새로고침 (실시간 동기화)", use_container_width=True, type="secondary"):
    st.rerun()

st.sidebar.markdown("---")

menu_options = [
    "🏟️ 현장 경기 관찰 메모", 
    "📂 경기 일지 조회", 
    "📂 경기관찰선수리스트", 
    "선수 등록", 
    "🔍 선수 검색 및 관찰일지 조회", 
    "🏢 회사 소속 선수 관리", 
    "🗑️ 데이터 삭제"
]

current_menu_index = menu_options.index(st.session_state["menu_selection"]) if st.session_state["menu_selection"] in menu_options else 0

menu = st.sidebar.radio("이동할 메뉴", menu_options, index=current_menu_index, key="menu_selection")

# ----------------------------------------------------
# 1. 🏟️ 현장 경기 관찰 메모
# ----------------------------------------------------
if menu == "🏟️ 현장 경기 관찰 메모":
    st.header("🏟️ 현장 경기 관찰 메모장")
    st.caption("포메이션 진형 모양 그대로 배치된 입력 칸을 터치하여 등번호를 바로 기입하세요. 이미 등록된 선수의 번호를 적으면 해당 선수의 관찰일지에도 자동으로 누적됩니다.")

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        match_date = st.date_input("경기 일자", value=datetime.today())
    with col_m2:
        tournament_name = st.text_input("대회 이름", placeholder="예: 금석배 U18, U리그 등")

    st.write("---")

    col_t1, col_t2 = st.columns(2)

    with col_t1:
        st.markdown("🏠 **홈팀 명***")
        selected_home = st_searchbox(
            search_function=search_team_autocomplete,
            placeholder="팀명을 입력하세요",
            key="home_team_searchbox"
        )
        home_team = selected_home if selected_home else ""
        home_formation = st.selectbox("홈팀 포메이션", ["4-3-3", "4-4-2", "4-2-3-1", "3-4-3", "3-5-2", "5-3-2", "5-4-1"], key="home_form")
        
    with col_t2:
        st.markdown("✈️ **어웨이팀 명***")
        selected_away = st_searchbox(
            search_function=search_team_autocomplete,
            placeholder="팀명을 입력하세요",
            key="away_team_searchbox"
        )
        away_team = selected_away if selected_away else ""
        away_formation = st.selectbox("어웨이팀 포메이션", ["4-3-3", "4-4-2", "4-2-3-1", "3-4-3", "3-5-2", "5-3-2", "5-4-1"], key="away_form")

    st.write("---")

    st.subheader("⚡ 등번호 입력")

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
            val = st.session_state.get(key_name, None)
            val_str = str(val) if val is not None else ""
            nums_dict[pos] = val_str
            if val_str.strip():
                team_entered_numbers[pos] = val_str.strip()

        render_pitch_graphic_from_saved(team_name, formation_name, nums_dict)
        
        display_sub_name = team_name.strip() if team_name.strip() else ("홈팀" if prefix == "home" else "어웨이팀")
        prefix_icon = "🏠" if prefix == "home" else "✈️"
        st.markdown(f"**{prefix_icon} {display_sub_name}**")

        for row in layout:
            st.markdown(f"<div style='font-size: 11px; font-weight: bold; color: #64748B; margin-top: 6px; margin-bottom: 2px;'>{row['line']}</div>", unsafe_allow_html=True)
            cols = st.columns(len(row['positions']))
            for idx, pos in enumerate(row['positions']):
                key_name = f"{prefix}_{pos}"
                with cols[idx]:
                    val_num = st.number_input(
                        f"{pos}", 
                        min_value=0, 
                        max_value=99, 
                        value=st.session_state.get(key_name, None), 
                        key=key_name,
                        step=1,
                        placeholder="번호"
                    )
                    if val_num is not None:
                        team_entered_numbers[pos] = str(int(val_num))

        st.write("")
        return team_entered_numbers

    pitch_col1, pitch_col2 = st.columns(2)
    with pitch_col1:
        home_numbers = render_team_interactive_grid(home_team, home_formation, "home")
    with pitch_col2:
        away_numbers = render_team_interactive_grid(away_team, away_formation, "away")

    st.write("---")

    st.markdown("## ⭐ 선수 메모")
    st.caption("포메이션에 등번호를 입력하면 아래에 해당 포지션들이 자동으로 활성화됩니다. 메모할 포지션을 체크하세요!")

    h_display_label = home_team.strip() if home_team.strip() else "홈팀"
    a_display_label = away_team.strip() if away_team.strip() else "어웨이팀"

    player_specific_memos = {}
    memo_col_h, memo_col_a = st.columns(2)

    with memo_col_h:
        st.markdown(f"**🏠 {h_display_label}**")
        active_home_pos = {pos: num for pos, num in home_numbers.items() if num}
        if active_home_pos:
            for pos, num in active_home_pos.items():
                chk_key = f"chk_memo_home_{pos}"
                is_checked = st.checkbox(f"📌 [{pos}] {num}번 메모", key=chk_key)
                if is_checked:
                    text_key = f"text_memo_home_{pos}"
                    note_val = st.text_area(f"[{pos}] {num}번 세부 관찰 기록", placeholder=f"[{pos}] {num}번 선수의 플레이 장점, 특징 등을 적어주세요...", key=text_key, height=90)
                    if note_val.strip():
                        player_specific_memos[f"{h_display_label.strip()} | [{pos}] {num}번"] = note_val.strip()
        else:
            st.info("💡 홈팀 포메이션 칸에 등번호를 입력해 주세요.")

    with memo_col_a:
        st.markdown(f"**✈️ {a_display_label}**")
        active_away_pos = {pos: num for pos, num in away_numbers.items() if num}
        if active_away_pos:
            for pos, num in active_away_pos.items():
                chk_key = f"chk_memo_away_{pos}"
                is_checked = st.checkbox(f"📌 [{pos}] {num}번 메모", key=chk_key)
                if is_checked:
                    text_key = f"text_memo_away_{pos}"
                    note_val = st.text_area(f"[{pos}] {num}번 세부 관찰 기록", placeholder=f"[{pos}] {num}번 선수의 플레이 장점, 특징 등을 적어주세요...", key=text_key, height=90)
                    if note_val.strip():
                        player_specific_memos[f"{a_display_label.strip()} | [{pos}] {num}번"] = note_val.strip()
        else:
            st.info("💡 어웨이팀 포메이션 칸에 등번호를 입력해 주세요.")

    st.write("---")
    st.subheader("📋 종합 메모")
    general_memo = st.text_area(
        "", 
        placeholder="[예시]\n- 교체선수\n- 경기양상\n- 스코어\n- 등",
        key="general_match_memo_input",
        height=140,
        label_visibility="collapsed"
    )

    st.write("")
    if st.button("💾 현장 메모 저장하기", type="primary", use_container_width=True):
        if not home_team.strip() or not away_team.strip():
            st.error("홈팀 명과 어웨이팀 명은 필수 입력 항목입니다. 팀 이름을 입력해 주세요.")
        else:
            with st.spinner("구글 시트에 현장 메모를 저장 중..."):
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
                    "선수명": memo_player_name, "소속팀": memo_team, "등번호": "-", "포지션": "경기분석",
                    "생년월일": "", "만 나이": "", "연 나이": "", "주발": "", "신장(cm)": "", "체중(kg)": "",
                    "진행 상태": "현장 관찰 메모 (임시)",
                    "장점/특기": tournament_name.strip() if tournament_name.strip() else "일반 경기",
                    "보완점/단점": "", "종합 평가": memo_overall, "작성일자": str(match_date)
                }

                updated_df = pd.DataFrame([new_memo_data]) if df.empty else pd.concat([pd.DataFrame([new_memo_data]), df], ignore_index=True)
                
                if save_data_to_sheet(updated_df):
                    st.success("🎉 현장 경기 관찰 메모 저장 완료!")
                    st.balloons()

# ----------------------------------------------------
# 2. 📂 경기 일지 조회
# ----------------------------------------------------
elif menu == "📂 경기 일지 조회":
    st.header("📂 경기일지리스트")
    memo_df = df[df["진행 상태"].str.strip() == "현장 관찰 메모 (임시)"].copy().reset_index(drop=True)
    if memo_df.empty:
        st.info("아직 저장된 경기 관찰 일지가 없습니다.")
    else:
        st.dataframe(memo_df[["작성일자", "소속팀", "선수명"]], use_container_width=True)

# ----------------------------------------------------
# 3. 📂 경기관찰선수리스트
# ----------------------------------------------------
elif menu == "📂 경기관찰선수리스트":
    st.header("📂 경기관찰 선수 리스트")
    st.info("현장 경기 관찰 메모에서 기록된 선수 목록입니다.")

# ----------------------------------------------------
# 4. 선수 등록
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
            back_num = st.text_input("등번호")
        with col2:
            birth_date = st.date_input("생년월일*", value=datetime(2005, 1, 1), min_value=datetime(1980, 1, 1), max_value=datetime.today())
            foot = st.selectbox("주발", ["오른발", "왼발", "양발"])
            date = st.date_input("관찰/작성일자", value=datetime.today())
            height_val = st.text_input("신장 (cm)", value="175")
            weight_val = st.text_input("체중 (kg)", value="70")

        pros = st.text_area("장점 및 주요 특기")
        cons = st.text_area("보완점 및 약점")
        overall = st.text_area("종합 평가 / 코멘트", height=150)
        
        if st.form_submit_button("💾 선수 데이터 저장", type="primary", use_container_width=True):
            if not name.strip():
                st.error("선수명은 필수 입력 항목입니다.")
            else:
                full_age, year_age = calculate_age(birth_date)
                new_data = {
                    "선수명": name.strip(), "소속팀": team.strip(), "등번호": str(back_num),
                    "포지션": position, "생년월일": str(birth_date), "만 나이": full_age,
                    "연 나이": year_age, "주발": foot, "신장(cm)": str(height_val),
                    "체중(kg)": str(weight_val), "진행 상태": status, "장점/특기": pros.strip(),
                    "보완점/단점": cons.strip(), "종합 평가": overall.strip(), "작성일자": str(date)
                }
                updated_df = pd.DataFrame([new_data]) if df.empty else pd.concat([pd.DataFrame([new_data]), df], ignore_index=True)
                if save_data_to_sheet(updated_df):
                    st.success("🎉 선수 데이터가 성공적으로 저장되었습니다!")
                    st.rerun()

# ----------------------------------------------------
# 5. 🔍 선수 검색 및 관찰일지 조회
# ----------------------------------------------------
elif menu == "🔍 선수 검색 및 관찰일지 조회":
    st.header("🔍 선수 검색 및 관찰일지 조회")
    official_df = df[df["진행 상태"].str.strip() != "현장 관찰 메모 (임시)"].copy().reset_index(drop=True)
    if official_df.empty:
        st.info("등록된 선수 데이터가 없습니다.")
    else:
        search_term = st.text_input("🔍 검색 (선수명, 소속팀 등)", key="live_search_input")
        filtered_df = official_df.copy()
        if search_term:
            keywords = search_term.strip().split()
            for kw in keywords:
                filtered_df = filtered_df[
                    filtered_df["선수명"].str.contains(kw, case=False, na=False) | 
                    filtered_df["소속팀"].str.contains(kw, case=False, na=False)
                ]
        st.dataframe(filtered_df, use_container_width=True)

# ----------------------------------------------------
# 6. 🏢 회사 소속 선수 관리 (HTML 프로필 연동 - 완전히 독립된 메뉴)
# ----------------------------------------------------
elif menu == "🏢 회사 소속 선수 관리":
    st.header("🏢 회사 소속 선수 관리 및 HTML 프로필")
    st.caption("우리 회사 소속 선수들의 명단을 독립적으로 관리하고, HTML 기반의 프로필 카드를 작성 및 조회할 수 있습니다.")

    agency_tab1, agency_tab2 = st.tabs(["📋 소속 선수 명단 및 HTML 프로필", "➕ 소속 선수 등록 및 프로필 작성"])

    with agency_tab1:
        st.subheader("⚽ 소속 선수 카드 라이브러리")
        
        agency_df = df[df["진행 상태"].isin(AGENCY_STATUS_OPTIONS) | (df["진행 상태"] == "소속 선수 (Active Client)")].copy().reset_index(drop=True)
        
        if agency_df.empty:
            st.info("💡 등록된 소속 선수가 없습니다. 우측 탭('소속 선수 등록 및 프로필 작성')에서 소속 선수를 등록해 주세요.")
        else:
            search_agency = st.text_input("🔍 소속 선수 검색 (선수명, 팀명 등)", key="agency_search_box")
            if search_agency.strip():
                q = search_agency.strip().lower()
                agency_df = agency_df[
                    agency_df["선수명"].str.lower().str.contains(q, na=False) |
                    agency_df["소속팀"].str.lower().str.contains(q, na=False)
                ]

            for idx, row in agency_df.iterrows():
                p_name = row.get("선수명", "선수명")
                p_team = row.get("소속팀", "소속팀")
                p_pos = row.get("포지션", "포지션")
                p_num = row.get("등번호", "-")
                p_foot = row.get("주발", "-")
                p_height = row.get("신장(cm)", "-")
                p_weight = row.get("체중(kg)", "-")
                p_pros = row.get("장점/특기", "내용 없음")
                p_cons = row.get("보완점/단점", "내용 없음")
                p_eval = row.get("종합 평가", "내용 없음")

                html_card = f"""
                <div style="background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); border: 1px solid #cbd5e1; border-radius: 12px; padding: 20px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #0f172a; padding-bottom: 10px; margin-bottom: 12px;">
                        <h3 style="margin: 0; color: #0f172a; font-size: 20px;">⚽ {p_name} <span style="font-size: 14px; color: #2563eb; font-weight: normal;">({p_pos} / {p_num}번)</span></h3>
                        <span style="background-color: #2563eb; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;">{p_team}</span>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 12px; font-size: 13.5px; color: #334155;">
                        <div><b>주발:</b> {p_foot}</div>
                        <div><b>신장:</b> {p_height} cm</div>
                        <div><b>체중:</b> {p_weight} kg</div>
                    </div>
                    <div style="background: white; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 13px; color: #1e293b;">
                        <p style="margin: 0 0 6px 0;"><b>🌟 장점 및 특기:</b> {p_pros}</p>
                        <p style="margin: 0 0 6px 0;"><b>⚠️ 보완점:</b> {p_cons}</p>
                        <p style="margin: 0;"><b>📋 종합 코멘트:</b> {p_eval}</p>
                    </div>
                </div>
                """
                st.markdown(html_card, unsafe_allow_html=True)

    with agency_tab2:
        st.subheader("➕ 신규 소속 선수 등록 (HTML 프로필 연동)")
        
        with st.form("agency_register_form", clear_on_submit=True):
            ac1, ac2 = st.columns(2)
            with ac1:
                ag_name = st.text_input("선수 이름*", key="agency_input_name")
                ag_team = st.text_input("소속 팀명", key="agency_input_team")
                ag_pos = st.selectbox("포지션", POSITION_OPTIONS, key="agency_input_pos")
                ag_stat = st.selectbox("계약/소속 상태", AGENCY_STATUS_OPTIONS, key="agency_input_stat")
                ag_num = st.text_input("등번호", key="agency_input_num")
            with ac2:
                ag_birth = st.date_input("생년월일", value=datetime(2005, 1, 1), key="agency_input_birth")
                ag_foot = st.selectbox("주발", ["오른발", "왼발", "양발"], key="agency_input_foot")
                ag_height = st.text_input("신장 (cm)", value="180", key="agency_input_height")
                ag_weight = st.text_input("체중 (kg)", value="75", key="agency_input_weight")

            ag_pros = st.text_area("장점 및 주요 특기", key="agency_input_pros")
            ag_cons = st.text_area("보완점 및 약점", key="agency_input_cons")
            ag_eval = st.text_area("종합 평가 및 에이전시 코멘트", key="agency_input_eval")

            ag_submitted = st.form_submit_button("💾 소속 선수 프로필 저장", type="primary", use_container_width=True)

            if ag_submitted:
                if not ag_name.strip():
                    st.error("선수 이름은 필수 입력 항목입니다.")
                else:
                    full_age, year_age = calculate_age(ag_birth)
                    new_agency_row = {
                        "선수명": ag_name.strip(),
                        "소속팀": ag_team.strip(),
                        "등번호": ag_num.strip(),
                        "포지션": ag_pos,
                        "생년월일": str(ag_birth),
                        "만 나이": full_age,
                        "연 나이": year_age,
                        "주발": ag_foot,
                        "신장(cm)": ag_height.strip(),
                        "체중(kg)": ag_weight.strip(),
                        "진행 상태": ag_stat,
                        "장점/특기": ag_pros.strip(),
                        "보완점/단점": ag_cons.strip(),
                        "종합 평가": ag_eval.strip(),
                        "작성일자": str(datetime.today().date())
                    }
                    
                    updated_df = pd.DataFrame([new_agency_row]) if df.empty else pd.concat([pd.DataFrame([new_agency_row]), df], ignore_index=True)
                    if save_data_to_sheet(updated_df):
                        st.success(f"🎉 '{ag_name.strip()}' 소속 선수 프로필이 안전하게 등록되었습니다!")
                        st.balloons()

# ----------------------------------------------------
# 7. 🗑️ 데이터 삭제
# ----------------------------------------------------
elif menu == "🗑️ 데이터 삭제":
    st.header("🗑️ 선수 데이터 삭제")
    if df.empty:
        st.info("삭제할 데이터가 없습니다.")
    else:
        del_selection = st.dataframe(df, use_container_width=True, selection_mode="multi-row", on_select="rerun")
        del_selected_rows = del_selection.selection.rows if hasattr(del_selection, "selection") else []
        
        if del_selected_rows:
            selected_count = len(del_selected_rows)
            st.warning(f"⚠️ 선택된 선수 총 {selected_count}명")
            if st.button(f"🗑️ 선택한 {selected_count}명 데이터 영구 삭제하기", type="primary", use_container_width=True):
                updated_df = df.drop(del_selected_rows).reset_index(drop=True)
                if save_data_to_sheet(updated_df):
                    st.success("삭제 완료!")
                    st.rerun()
