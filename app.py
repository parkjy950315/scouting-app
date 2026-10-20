import streamlit as st
import pandas as pd
import requests
import io
import re
import os
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
# 📱 PC & 모바일 상단 여백 및 스타일 설정
# ----------------------------------------------------
st.markdown("""
    <style>
    .block-container {
        padding-top: 3rem !important;
        padding-bottom: 3rem !important;
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
        .block-container {
            padding-left: 1.2rem !important;
            padding-right: 1.2rem !important;
            padding-top: 2rem !important;
        }
        h1 {
            font-size: 23px !important;
            margin-top: 10px !important;
            margin-bottom: 20px !important;
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
POSITION_OPTIONS = ["GK", "CB", "LB", "RB", "MF", "LW", "RW", "CF"]

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

def load_data():
    expected_cols = [
        "선수명", "소속팀", "등번호", "포지션", "생년월일", "만 나이", "연 나이", "주발", "신장(cm)", "체중(kg)",
        "진행 상태", "장점/특기", "보완점/단점", "종합 평가", "작성일자"
    ]
    try:
        csv_url = get_csv_export_url(GOOGLE_SHEET_URL)
        df = pd.read_csv(csv_url, dtype=str)
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

# 소속팀 텍스트 분리 함수 (현재 소속팀 / 과거 소속팀 이력 분리)
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

# 🧠 메모 기반 플레이스타일 분석 및 요약 리포트 생성기
def generate_ai_scouting_summary(player):
    name = player.get('선수명', '미확인')
    full_team_str = player.get('소속팀', '소속미상')
    current_team, past_teams = parse_team_info(full_team_str)
    team_display = f"{current_team} {past_teams}".strip()
    
    pos = player.get('포지션', '미정')
    height = player.get('신장(cm)', '')
    weight = player.get('체중(kg)', '')
    foot = player.get('주발', '미확인')
    age = player.get('만 나이', '미확인')
    status = player.get('진행 상태', '관찰 중')
    date_str = player.get('작성일자', '-')
    
    pros = str(player.get('장점/특기', '')).strip()
    cons = str(player.get('보완점/단점', '')).strip()
    overall = str(player.get('종합 평가', '')).strip()
    
    obs_count = len(re.findall(r'\[\d{4}-\d{2}-\d{2}\s*관찰\]', pros + cons + overall))
    if obs_count == 0 and (pros or cons or overall):
        obs_count = 1
        
    physical_info = f"{height}cm" if height else "신장 미입력"
    if weight:
        physical_info += f" / {weight}kg"
        
    combined_notes = (pros + " " + cons + " " + overall).lower()
    
    style_keywords = []
    if any(k in combined_notes for k in ["빌드업", "패스", "시야", "전개", "킥"]):
        style_keywords.append("• **패스 및 빌드업 성향**: 후방 또는 중원에서 정확한 킥과 시야를 바탕으로 공격 전개를 주도하는 플레이를 선호합니다.")
    if any(k in combined_notes for k in ["스피드", "주력", "빠른", "돌파", "침투", "속도"]):
        style_keywords.append("• **속도 및 기동력**: 뛰어난 주력과 순간 스피드를 활용해 측면 돌파나 뒷공간 침투에 강점을 보입니다.")
    if any(k in combined_notes for k in ["피지컬", "경합", "몸싸움", "제공권", "대인", "수비"]):
        style_keywords.append("• **피지컬 및 경합 능력**: 단단한 신체 조건을 바탕으로 한 대인 방어와 공중볼 경합에서 존재감을 드러냅니다.")
    if any(k in combined_notes for k in ["활동량", "압박", "성실", "수비가담", "체력"]):
        style_keywords.append("• **활동량 및 전술 이해도**: 경기 내내 성실한 움직임과 적극적인 압박 가담으로 팀에 기여하는 스타일입니다.")
    if any(k in combined_notes for k in ["결정력", "슈팅", "골문", "마무리", "찬스"]):
        style_keywords.append("• **결정력 및 파이널 서드 영향력**: 박스 안팎에서 위협적인 슈팅과 침착한 마무리를 보여줍니다.")

    if not style_keywords and (pros or overall):
        style_keywords.append("• **종합 플레이 성향**: 작성된 관찰 메모를 바탕으로 볼 때, 해당 포지션에서 성실한 플레이와 기본기를 갖춘 자원입니다.")
    
    style_analysis_text = "\n".join(style_keywords) if style_keywords else "❌ *분석할 충분한 메모 데이터가 없습니다. 장점이나 평가를 더 기록해 주세요.*"

    summary = f"""
### 📊 [{name} 선수 스카우팅 심층 분석 리포트]

#### 1. 기본 프로필 및 소속 이력
- **소속팀**: {team_display}
- **포지션 / 나이**: `{pos}` ({age} | 주발: `{foot}`)
- **피지컬**: {physical_info}
- **관리 상태**: 진행 상태 [`{status}`] | 총 관찰 기록 **{obs_count}회** (최근 작성: {date_str})

---

#### 2. 🧠 메모 기반 AI 플레이스타일 분석
{style_analysis_text}

---

#### 3. 🌟 작성된 장점 및 특기 메모
{f"```text\n{pros}\n```" if pros else "*(작성된 내용 없음)*"}

---

#### 4. ⚠️ 작성된 보완점 및 약점 메모
{f"```text\n{cons}\n```" if cons else "*(작성된 내용 없음)*"}

---

#### 5. 📋 스카우터 종합 평가 및 코멘트
{f"```text\n{overall}\n```" if overall else "*(작성된 내용 없음)*"}
"""
    return summary

# ----------------------------------------------------
# 📄 프리미엄 디자인 PDF 보고서 생성 함수
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
    
    # 고급 스타일 정의
    title_style = ParagraphStyle('TitleStyle', fontName=korean_font, fontSize=20, leading=24, alignment=1, textColor=colors.HexColor('#003366'), fontName_bold=True)
    subtitle_style = ParagraphStyle('SubtitleStyle', fontName=korean_font, fontSize=10, leading=14, alignment=1, textColor=colors.HexColor('#6c757d'))
    
    section_heading = ParagraphStyle('SectionHeading', fontName=korean_font, fontSize=12, leading=16, textColor=colors.HexColor('#003366'), spaceBefore=12, spaceAfter=6, fontName_bold=True)
    body_style = ParagraphStyle('BodyStyle', fontName=korean_font, fontSize=9.5, leading=14, textColor=colors.HexColor('#222222'))
    table_label = ParagraphStyle('TableLabel', fontName=korean_font, fontSize=9, leading=12, textColor=colors.HexColor('#555555'))
    table_value = ParagraphStyle('TableValue', fontName=korean_font, fontSize=9.5, leading=13, textColor=colors.HexColor('#111111'))

    # 헤더 타이틀
    story.append(Paragraph("SMC — SUNGMUN COMPANY", title_style))
    story.append(Paragraph("PROFESSIONAL PLAYER SCOUTING REPORT", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#003366'), spaceAfter=15))

    # 선수 프로필 정보 정리
    curr_team, past_team = parse_team_info(player_data.get('소속팀', ''))
    full_team = f"{curr_team} {past_team}".strip()
    weight_val = f"{player_data.get('체중(kg)')}kg" if player_data.get('체중(kg)') else "미입력"
    
    profile_data = [
        [Paragraph("선수명", table_label), Paragraph(f"<b>{player_data.get('선수명', '-')}</b>", table_value), Paragraph("포지션 / 등번호", table_label), Paragraph(f"<b>{player_data.get('포지션', '-')} / {player_data.get('등번호', '-')}번</b>", table_value)],
        [Paragraph("현재 소속팀", table_label), Paragraph(f"{curr_team}", table_value), Paragraph("진행 상태", table_label), Paragraph(f"<font color='#007bff'><b>{player_data.get('진행 상태', '-')}</b></font>", table_value)],
        [Paragraph("소속팀 이력", table_label), Paragraph(f"{full_team}", table_value), Paragraph("주발", table_label), Paragraph(f"{player_data.get('주발', '-')}", table_value)],
        [Paragraph("생년월일 (나이)", table_label), Paragraph(f"{player_data.get('생년월일', '-')} ({player_data.get('만 나이', '-')})", table_value), Paragraph("피지컬 (신장/체중)", table_label), Paragraph(f"{player_data.get('신장(cm)', '-')}cm / {weight_val}", table_value)],
        [Paragraph("최근 작성일자", table_label), Paragraph(f"{player_data.get('작성일자', '-')}", table_value), Paragraph("보고서 발급일", table_label), Paragraph(datetime.today().strftime('%Y-%m-%d'), table_value)]
    ]
    
    profile_table = Table(profile_data, colWidths=[90, 180, 90, 180])
    profile_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd3da')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e6ea')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(profile_table)
    story.append(Spacer(1, 15))

    # 공통 섹션 박스 생성 헬퍼 함수
    def add_section_box(title, content, bg_color, border_color):
        story.append(Paragraph(title, section_heading))
        cleaned_content = str(content).replace('\n', '<br/>') if content and str(content).strip() else "작성된 관찰 내용이 없습니다."
        content_table = Table([[Paragraph(cleaned_content, body_style)]], colWidths=[540])
        content_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(bg_color)),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor(border_color)),
            ('PADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(content_table)
        story.append(Spacer(1, 10))

    # 각 관찰 영역 추가 (고급스러운 배경 컬러 적용)
    add_section_box("📌 장점 및 주요 특기 (PROS)", player_data.get('장점/특기', ''), '#f1f8ff', '#bbe1fa')
    add_section_box("⚠️ 보완점 및 약점 (CONS)", player_data.get('보완점/단점', ''), '#fffdf4', '#ffeeba')
    add_section_box("📋 스카우터 종합 평가 및 코멘트 (OVERALL EVALUATION)", player_data.get('종합 평가', ''), '#f4f6f8', '#ced4da')

    # 하단 푸터 텍스트 추가
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#ced4da'), spaceAfter=8))
    footer_style = ParagraphStyle('FooterStyle', fontName=korean_font, fontSize=8, leading=10, alignment=1, textColor=colors.HexColor('#888888'))
    story.append(Paragraph("CONFIDENTIAL — This scouting report is exclusively prepared for SUNGMUN COMPANY internal use.", footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer

df = load_data()

# 로고 출력
display_logo()

st.title("⚽ 선수 스카우팅 관리 시스템")

# ----------------------------------------------------
# 사이드바 설정
# ----------------------------------------------------
st.sidebar.title("📌 메뉴")

if st.sidebar.button("🔄 새로고침", use_container_width=True):
    st.rerun()

st.sidebar.markdown("---")

menu = st.sidebar.radio("이동할 메뉴", ["선수 등록", "🔍 선수 검색 및 관찰일지 조회", "✏️ 선수 정보/일지 수정 및 추가", "🗑️ 데이터 삭제"])

# ----------------------------------------------------
# 1. 선수 등록
# ----------------------------------------------------
if menu == "선수 등록":
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
# 2. 선수 검색 및 상세 관찰일지 조회 & AI 분석 & PDF 다운로드
# ----------------------------------------------------
elif menu == "🔍 선수 검색 및 관찰일지 조회":
    st.header("🔍 관찰 선수 검색 및 상세 일지 / AI 분석 / PDF 다운로드")
    
    if df.empty:
        st.info("등록된 선수 데이터가 없습니다.")
    else:
        total_count = len(df)
        watchlist_count = len(df[df["진행 상태"] == "관심 선수 (Watchlist)"])
        observing_count = len(df[df["진행 상태"] == "집중 관찰 중"])
        review_count = len(df[df["진행 상태"] == "계약 검토"])
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("전체 등록 선수", f"{total_count}명")
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
        
        filtered_df = df.copy()
        
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
        
        st.subheader(f"📋 선수 목록 (클릭 시 하단에 관찰일지 표출)")
        
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
                st.markdown(f"### ⚽ [{p.get('진행 상태', '')}] {p.get('선수명', '')} 상세 관찰일지")
            with head_col2:
                try:
                    pdf_bytes = generate_pdf_report(p)
                    st.download_button(
                        label="📄 관찰일지 PDF 다운로드",
                        data=pdf_bytes,
                        file_name=f"{p.get('선수명', '선수')}_스카우팅관찰일지.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
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
            
            if st.button("🧠 메모 기반 플레이스타일 심층 분석 리포트 생성", type="primary", use_container_width=True):
                with st.spinner("작성된 관찰 메모 분석 중..."):
                    ai_report = generate_ai_scouting_summary(p)
                    st.markdown(ai_report)
            
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
        else:
            st.info("💡 위 선수 목록 표에서 조회하고 싶은 **선수 행을 클릭**하시면 관찰일지와 AI 분석, PDF 다운로드 버튼이 나타납니다.")

# ----------------------------------------------------
# 3. 선수 정보 수정 및 소속 이력 누적
# ----------------------------------------------------
elif menu == "✏️ 선수 정보/일지 수정 및 추가":
    st.header("✏️ 기존 선수 정보 수정 및 추가 관찰 일지 작성")
    if df.empty:
        st.info("수정할 선수 데이터가 없습니다.")
    else:
        player_options = [f"{idx}번 | [{row.get('진행 상태', '')}] {parse_team_info(row.get('소속팀', ''))[0]} - {row.get('선수명', '')}" for idx, row in df.iterrows()]
        selected_option = st.selectbox("수정할 선수를 선택하세요", player_options)
        
        if selected_option:
            target_idx = int(selected_option.split("번 |")[0])
            target_row = df.loc[target_idx]
            
            current_t, past_t = parse_team_info(target_row.get("소속팀", ""))
            
            with st.expander("📖 현재 소속팀 및 전체 누적 관찰 기록 펼쳐보기", expanded=False):
                st.markdown(f"**[소속팀]** {current_t} {past_t}")
                st.write("---")
                st.markdown(f"**[장점/특기]**\n{target_row.get('장점/특기', '(없음)')}")
                st.write("---")
                st.markdown(f"**[보완점/단점]**\n{target_row.get('보완점/단점', '(없음)')}")
                st.write("---")
                st.markdown(f"**[종합 평가]**\n{target_row.get('종합 평가', '(없음)')}")

            col1, col2 = st.columns(2)
            with col1:
                edit_name = st.text_input("선수명", value=str(target_row.get("선수명", "")), key=f"edit_name_{target_idx}")
                edit_team_input = st.text_input("소속팀 (팀이 바뀐 경우 새 팀명 입력)", value=current_t, key=f"edit_team_{target_idx}")
                
                cur_pos = str(target_row.get("포지션", "MF"))
                pos_idx = POSITION_OPTIONS.index(cur_pos) if cur_pos in POSITION_OPTIONS else 4
                edit_position = st.selectbox("포지션", POSITION_OPTIONS, index=pos_idx, key=f"edit_pos_{target_idx}")
                
                default_status = str(target_row.get("진행 상태", STATUS_OPTIONS[0]))
                status_index = STATUS_OPTIONS.index(default_status) if default_status in STATUS_OPTIONS else 0
                edit_status = st.selectbox("진행 상태", STATUS_OPTIONS, index=status_index, key=f"edit_status_{target_idx}")
                
                cur_num = str(target_row.get("등번호", "")).strip()
                back_num_options = [""] + [str(i) for i in range(1, 100)]
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

            st.subheader("➕ 오늘 관찰한 내용 추가 입력 (누적 기록)")
            new_pros = st.text_area("새 관찰 장점", key=f"new_pros_{target_idx}")
            new_cons = st.text_area("새로 관찰한 보완점", key=f"new_cons_{target_idx}")
            new_overall = st.text_area("새로 관찰한 종합 평가", key=f"new_overall_{target_idx}")
            
            if st.button("🔄 변경사항 및 추가 일지 저장하기", type="primary", use_container_width=True, key=f"btn_save_{target_idx}"):
                if not edit_name.strip():
                    st.error("선수명은 필수입니다.")
                else:
                    with st.spinner("변경사항을 구글 시트에 업데이트하는 중..."):
                        new_team_input = edit_team_input.strip()
                        raw_old_team = str(target_row.get("소속팀", "")).strip()
                        
                        if current_t and new_team_input and current_t != new_team_input:
                            if "(전:" not in raw_old_team:
                                final_team_str = f"{new_team_input} (전: {current_t})"
                            else:
                                history_part = raw_old_team.split("(전:")[1]
                                final_team_str = f"{new_team_input} (전: {current_t}, {history_part}"
                        else:
                            final_team_str = raw_old_team if raw_old_team else new_team_input

                        old_pros = str(target_row.get("장점/특기", ""))
                        old_cons = str(target_row.get("보완점/단점", ""))
                        old_overall = str(target_row.get("종합 평가", ""))
                        
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
                            "신장(cm)": str(edit_height), "체중(kg)": str(edit_weight),
                            "진행 상태": str(edit_status), "장점/특기": str(updated_pros),
                            "보완점/단점": str(updated_cons), "종합 평가": str(updated_overall),
                            "작성일자": str(today_str)
                        }
                        updated_df = pd.DataFrame(records).astype(str)
                        if save_data_to_sheet(updated_df):
                            st.success("🎉 선수 정보와 소속 이력, 추가 관찰 일지가 성공적으로 수정·저장되었습니다!")

# ----------------------------------------------------
# 4. 데이터 삭제
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
                        st.session_state[confirm_key] = False
                        st.rerun()
        else:
            if "confirm_delete_mode" in st.session_state:
                st.session_state["confirm_delete_mode"] = False
                
            st.info("💡 위 목록 표에서 삭제하고 싶은 **선수 행들을 체크(다중 선택)** 하시면 삭제 버튼이 나타납니다.")
