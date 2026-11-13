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
            st.info("💡 위 선수 목록 표에서 조회하고 싶은 **선수 행을 클릭**하시면 관찰일지와 수정/삭제 폼이 나타납니다.")

# ----------------------------------------------------
# 6. 데이터 삭제
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
