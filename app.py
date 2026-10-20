import streamlit as st
import pandas as pd
import requests
import io
import re
from datetime import datetime

# 페이지 기본 설정
st.set_page_config(page_title="선수 스카우팅 DB", page_icon="⚽", layout="wide")

# 🔗 1. 구글 시트 공유 링크
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1WSbVkwCr5Dv5hN3zU0Bw5tzzbNjMmlFyZiOCpG5DRjI/edit?usp=sharing"

# 🔗 2. 구글 Apps Script 웹앱 URL
GOOGLE_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxTTvgJqNnmBxwuCGvT3agMEo0_0Fon0JGWdREyR7usEIu4Mfw9M1lq66njtr8S_cbP/exec"

STATUS_OPTIONS = ["관심 선수 (Watchlist)", "집중 관찰 중", "컨택 완료", "계약 검토", "보류 / 제외"]

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
        df = df.fillna("")
    except Exception:
        df = pd.DataFrame(columns=expected_cols)
        
    for col in expected_cols:
        if col not in df.columns:
            if col == "진행 상태":
                df[col] = "관심 선수 (Watchlist)"
            else:
                df[col] = ""
        else:
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

def generate_ai_scouting_summary(player):
    name = player.get('선수명', '미확인')
    team = player.get('소속팀', '소속미상')
    pos = player.get('포지션', '미정')
    height = player.get('신장(cm)', '')
    weight = player.get('체중(kg)', '')
    foot = player.get('주발', '미확인')
    age = player.get('만 나이', '미확인')
    status = player.get('진행 상태', '관찰 중')
    
    pros = str(player.get('장점/특기', '')).strip()
    cons = str(player.get('보완점/단점', '')).strip()
    overall = str(player.get('종합 평가', '')).strip()
    
    obs_count = len(re.findall(r'\[\d{4}-\d{2}-\d{2}\s*관찰\]', pros + cons + overall))
    if obs_count == 0 and (pros or cons or overall):
        obs_count = 1
        
    physical_info = f"{height}cm" if height else "신장 미입력"
    if weight:
        physical_info += f" / {weight}kg"
        
    pos_upper = pos.upper()
    tactical_role = "필드 플레이어"
    if any(p in pos_upper for p in ["GK", "골키퍼"]):
        tactical_role = "최후방 빌드업 및 Shot Stopping 담당 골키퍼"
    elif any(p in pos_upper for p in ["CB", "DF", "수비"]):
        tactical_role = "후방 지역 대율 및 Defensive Duels 담당 센터백/수비수"
    elif any(p in pos_upper for p in ["MF", "CM", "CDM", "CAM", "미드필더"]):
        tactical_role = "중원 연결고리 및 Progressive Passes/Distribution 담당 미드필더"
    elif any(p in pos_upper for p in ["FW", "ST", "RW", "LW", "공격"]):
        tactical_role = "전방 침투 및 파이널 서드 마무리 담당 공격수"

    pros_list = [p.strip() for p in pros.split('\n') if p.strip() and not p.strip().startswith('[')]
    pros_formatted = "\n".join([f"  • {p}" for p in pros_list]) if pros_list else "  • 기록된 장점 항목이 없습니다."

    cons_list = [c.strip() for c in cons.split('\n') if c.strip() and not c.strip().startswith('[')]
    cons_formatted = "\n".join([f"  • {c}" for c in cons_list]) if cons_list else "  • 특별한 약점 항목이 보고되지 않았습니다."

    summary = f"""
### 📊 [스카우팅 심화 분석 리포트: {name}]

#### 1. 선수 프로필 & 데이터 신뢰도
- **인적 사항**: {name} ({team} / {pos}) | {age} | {foot}
- **피지컬 조건**: {physical_info}
- **역할 규정**: {tactical_role}
- **데이터 누적 정도**: 총 **{obs_count}회**의 관찰일지 기록 보유 (진행 상태: `{status}`)

---

#### 2. 기술적/전술적 강점 (Technical & Tactical Strengths)
{pros_formatted}

- **피지컬 & 전술 메커니즘**:
  {foot}을 주로 활용하며, {pos} 포지션에서 요구되는 빌드업 및 대면 경합 상황에 강점을 보입니다.

---

#### 3. 개선 과제 및 위험 요인 (Areas for Development)
{cons_formatted}

- **체크 포인트**:
  고강도 압박 상황이나 경기 템포 유지 측면에서 상위 리그 적응을 위한 모니터링이 추가로 요구됩니다.

---

#### 4. 스카우터 최종 평가 및 액션 플랜
- **종합 코멘트 요약**: 
  "{overall if overall else '현재 지속적인 폼 체크가 필요한 상태입니다.'}"
- **추천 방향**:
  **[{status}]** 단계를 유지하면서, 차기 관찰 경기에서는 특히 약점 영역으로 지적된 부분의 개선 여부와 전술적 이행 능력을 중점 검증할 것을 권장합니다.
"""
    return summary

df = load_data()

st.title("⚽ 선수 스카우팅 관리 시스템")

menu = st.sidebar.radio("메뉴 선택", ["선수 등록", "🔍 선수 검색 및 리포트 조회", "✏️ 선수 정보/일지 수정 및 추가", "🗑️ 데이터 삭제", "📊 엑셀 다운로드"])

# ----------------------------------------------------
# 1. 선수 등록
# ----------------------------------------------------
if menu == "선수 등록":
    st.header("📋 신규 관찰 선수 등록")
    
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("선수명*", key="reg_name_input")
        team = st.text_input("소속팀", key="reg_team_input")
        position = st.text_input("포지션 (예: FW, CAM, CB)", key="reg_pos_input")
        status = st.selectbox("진행 상태", STATUS_OPTIONS)
        
        back_num_options = [""] + [str(i) for i in range(1, 100)]
        back_num_val = st.selectbox("등번호", options=back_num_options, index=0, placeholder="등번호 선택")

    with col2:
        birth_date = st.date_input("생년월일 선택*", value=datetime(2005, 1, 1), min_value=datetime(1980, 1, 1), max_value=datetime.today())
        age_full_str, age_year_str = calculate_age(birth_date)
        st.info(f"💡 **자동 계산 나이**: {age_full_str} (연 {age_year_str})")
        foot = st.selectbox("주발", ["오른발", "왼발", "양발"])
        date = st.date_input("관찰/작성일자", value=datetime.today())
        
        st.write("---")
        height_val = st.selectbox("신장 (cm)", options=[str(h) for h in range(150, 205)] + [""], index=25, placeholder="신장 선택")
        weight_val = st.selectbox("체중 (kg)", options=[""] + [str(w) for w in range(50, 105)], index=0, placeholder="체중 선택")

    st.subheader("📝 관찰 리포트 / 첫 메모")
    pros = st.text_area("장점 및 주요 특기")
    cons = st.text_area("보완점 및 약점")
    overall = st.text_area("종합 평가 / 코멘트")
    
    if st.button("💾 선수 데이터 저장", type="primary", use_container_width=True):
        if not name.strip():
            st.error("선수명은 필수 입력 항목입니다.")
        else:
            with st.spinner("구글 시트에 데이터를 안전하게 저장하는 중..."):
                new_data = {
                    "선수명": name.strip(), "소속팀": team.strip(), "등번호": str(back_num_val),
                    "포지션": position.strip(), "생년월일": str(birth_date),
                    "만 나이": age_full_str, "연 나이": age_year_str, "주발": foot,
                    "신장(cm)": str(height_val), "체중(kg)": str(weight_val),
                    "진행 상태": status, "장점/특기": pros.strip(), "보완점/단점": cons.strip(),
                    "종합 평가": overall.strip(), "작성일자": str(date)
                }
                updated_df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                if save_data_to_sheet(updated_df):
                    st.success(f"🎉 '{name}' 선수의 데이터가 구글 시트에 성공적으로 저장되었습니다!")
                    st.balloons() # 축하 효과 애니메이션 추가

# ----------------------------------------------------
# 2. 선수 검색 및 상세 리포트 조회
# ----------------------------------------------------
elif menu == "🔍 선수 검색 및 리포트 조회":
    st.header("🔍 관찰 선수 검색 및 상세 리포트 조회")
    if df.empty:
        st.info("등록된 선수 데이터가 없습니다.")
    else:
        search_term = st.text_input("선수명, 소속팀 또는 등번호 검색", "")
        filtered_df = df.copy()
        if search_term:
            filtered_df = filtered_df[
                filtered_df["선수명"].str.contains(search_term, na=False) | 
                filtered_df["소속팀"].str.contains(search_term, na=False) |
                filtered_df["등번호"].str.contains(search_term, na=False)
            ]
        
        st.subheader("📋 선수 목록 요약")
        st.dataframe(filtered_df, use_container_width=True)
        
        st.write("---")
        st.subheader("👤 상세 리포트를 조회할 선수를 선택하세요")
        
        player_list = [f"{idx}번 | [{row.get('진행 상태', '')}] {row.get('선수명', '')} ({row.get('소속팀', '')})" for idx, row in filtered_df.iterrows()]
        selected_player = st.selectbox("선수를 선택하면 상세 프로필과 접이식 리포트가 열립니다.", ["선택하세요..."] + player_list)
        
        if selected_player != "선택하세요...":
            target_idx = int(selected_player.split("번 |")[0])
            p = df.loc[target_idx]
            
            st.markdown(f"### ⚽ [{p.get('진행 상태', '')}] {p.get('선수명', '')} 프로필")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("소속팀 / 등번호", f"{p.get('소속팀', '-')} / {p.get('등번호', '-')}번")
            c2.metric("포지션 / 주발", f"{p.get('포지션', '-')} / {p.get('주발', '-')}")
            c3.metric("나이 (만/연)", f"{p.get('만 나이', '-')} ({p.get('연 나이', '-')})")
            
            weight_display = f"{p.get('체중(kg)')}kg" if p.get('체중(kg)') else "미입력"
            c4.metric("피지컬", f"{p.get('신장(cm)', '-')}cm / {weight_display}")
            
            st.write(f"• **생년월일**: {p.get('생년월일', '-')} | **최근 업데이트**: {p.get('작성일자', '-')}")
            
            st.markdown("---")
            
            if st.button("🤖 AI 팩트 기반 스카우팅 심화 리포트 생성", type="primary", use_container_width=True):
                with st.spinner("누적 관찰 일지 및 피지컬 데이터 분석 중..."):
                    ai_report = generate_ai_scouting_summary(p)
                    st.success("심화 스카우팅 분석 완료!")
                    st.markdown(ai_report)

            st.subheader("📚 관찰 리포트 및 평가 일지 (클릭해서 펼치기)")
            
            with st.expander("🌟 장점 및 주요 특기 보기", expanded=True):
                pros_text = p.get('장점/특기', '')
                if pd.notna(pros_text) and str(pros_text).strip():
                    st.info(pros_text)
                else:
                    st.write("등록된 내용이 없습니다.")
                    
            with st.expander("⚠️ 보완점 및 약점 보기", expanded=False):
                cons_text = p.get('보완점/단점', '')
                if pd.notna(cons_text) and str(cons_text).strip():
                    st.warning(cons_text)
                else:
                    st.write("등록된 내용이 없습니다.")
                    
            with st.expander("📋 종합 평가 및 코멘트 보기", expanded=False):
                overall_text = p.get('종합 평가', '')
                if pd.notna(overall_text) and str(overall_text).strip():
                    st.success(overall_text)
                else:
                    st.write("등록된 내용이 없습니다.")

# ----------------------------------------------------
# 3. 선수 정보 수정 및 관찰 일지 누적
# ----------------------------------------------------
elif menu == "✏️ 선수 정보/일지 수정 및 추가":
    st.header("✏️ 기존 선수 정보 수정 및 추가 관찰 일지 작성")
    if df.empty:
        st.info("수정할 선수 데이터가 없습니다.")
    else:
        player_options = [f"{idx}번 | [{row.get('진행 상태', '')}] {row.get('선수명', '')} ({row.get('소속팀', '')})" for idx, row in df.iterrows()]
        selected_option = st.selectbox("수정할 선수를 선택하세요", player_options)
        
        if selected_option:
            target_idx = int(selected_option.split("번 |")[0])
            target_row = df.loc[target_idx]
            
            with st.expander("📖 현재까지 누적된 전체 관찰 기록 펼쳐보기", expanded=False):
                st.markdown(f"**[장점/특기]**\n{target_row.get('장점/특기', '(없음)')}")
                st.write("---")
                st.markdown(f"**[보완점/단점]**\n{target_row.get('보완점/단점', '(없음)')}")
                st.write("---")
                st.markdown(f"**[종합 평가]**\n{target_row.get('종합 평가', '(없음)')}")

            col1, col2 = st.columns(2)
            with col1:
                edit_name = st.text_input("선수명", value=str(target_row.get("선수명", "")), key=f"edit_name_{target_idx}")
                edit_team = st.text_input("소속팀", value=str(target_row.get("소속팀", "")), key=f"edit_team_{target_idx}")
                edit_position = st.text_input("포지션", value=str(target_row.get("포지션", "")), key=f"edit_pos_{target_idx}")
                
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
                        old_pros = str(target_row.get("장점/특기", ""))
                        old_cons = str(target_row.get("보완점/단점", ""))
                        old_overall = str(target_row.get("종합 평가", ""))
                        
                        today_str = str(edit_date)
                        updated_pros = f"{old_pros}\n\n[{today_str} 관찰]\n{new_pros.strip()}".strip() if new_pros.strip() else old_pros
                        updated_cons = f"{old_cons}\n\n[{today_str} 관찰]\n{new_cons.strip()}".strip() if new_cons.strip() else old_cons
                        updated_overall = f"{old_overall}\n\n[{today_str} 관찰]\n{new_overall.strip()}".strip() if new_overall.strip() else old_overall

                        records = df.to_dict('records')
                        records[target_idx] = {
                            "선수명": str(edit_name).strip(), "소속팀": str(edit_team).strip(),
                            "등번호": str(edit_back_num), "포지션": str(edit_position).strip(),
                            "생년월일": str(edit_birth_date), "만 나이": str(age_full_str),
                            "연 나이": str(age_year_str), "주발": str(edit_foot),
                            "신장(cm)": str(edit_height), "체중(kg)": str(edit_weight),
                            "진행 상태": str(edit_status), "장점/특기": str(updated_pros),
                            "보완점/단점": str(updated_cons), "종합 평가": str(updated_overall),
                            "작성일자": str(today_str)
                        }
                        updated_df = pd.DataFrame(records).astype(str)
                        if save_data_to_sheet(updated_df):
                            st.success("🎉 선수 정보와 추가 관찰 일지가 성공적으로 수정·저장되었습니다!")

# ----------------------------------------------------
# 4. 데이터 삭제
# ----------------------------------------------------
elif menu == "🗑️ 데이터 삭제":
    st.header("🗑️ 선수 데이터 삭제")
    if df.empty:
        st.info("삭제할 데이터가 없습니다.")
    else:
        player_options = [f"{idx}번 | {row.get('선수명', '')}" for idx, row in df.iterrows()]
        selected_option = st.selectbox("삭제할 선수 선택", player_options)
        if selected_option and st.button("영구 삭제", type="primary"):
            target_idx = int(selected_option.split("번 |")[0])
            updated_df = df.drop(target_idx).reset_index(drop=True)
            if save_data_to_sheet(updated_df):
                st.success("선수 데이터가 영구 삭제되었습니다.")
                st.rerun()

# ----------------------------------------------------
# 5. 엑셀 다운로드
# ----------------------------------------------------
elif menu == "📊 엑셀 다운로드":
    st.header("📊 엑셀 다운로드")
    if not df.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='스카우팅DB')
        st.download_button("📥 다운로드", data=output.getvalue(), file_name='scouting_database.xlsx')
