# ui_tab1.py (결제 옵션 UI 추가 및 전화번호 정규화 로직 수정)
import streamlit as st
from datetime import datetime, date
import pytz
import json
import os
import traceback
import re # re 모듈 임포트 (직접 사용할 경우 대비)

# Import necessary custom modules
try:
    import data
    import utils # utils 모듈 임포트
    import google_drive_helper as gdrive
    from state_manager import (
        MOVE_TYPE_OPTIONS,
        prepare_state_for_save,
        load_state_from_data
    )
    import callbacks
except ImportError as ie:
    st.error(f"UI Tab 1: 필수 모듈 로딩 실패 - {ie}")
    st.stop()
except Exception as e:
    st.error(f"UI Tab 1: 모듈 로딩 중 오류 - {e}")
    traceback.print_exc()
    st.stop()

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "images")
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)
        print(f"INFO: Created UPLOAD_DIR at {UPLOAD_DIR}")
except PermissionError:
    st.error(f"권한 오류: 업로드 디렉토리({UPLOAD_DIR}) 생성 권한이 없습니다.")
    UPLOAD_DIR = None
except Exception as e_path:
    st.error(f"오류: UPLOAD_DIR 경로 설정 중 문제 발생: {e_path}")
    UPLOAD_DIR = None

def render_tab1():
    if UPLOAD_DIR is None:
        st.warning("이미지 업로드 디렉토리 설정에 문제가 있어 이미지 관련 기능이 제한될 수 있습니다.")

    # Initialize session state for keys used in this tab if not already present
    if 'image_uploader_key_counter' not in st.session_state:
        st.session_state.image_uploader_key_counter = 0
    if 'issue_tax_invoice' not in st.session_state:
        st.session_state.issue_tax_invoice = False
    if 'card_payment' not in st.session_state:
        st.session_state.card_payment = False


    with st.container(border=True): # Google Drive Section
        st.subheader("☁️ Google Drive 연동")
        st.caption("Google Drive의 지정된 폴더에 견적(JSON) 파일을 저장하고 불러옵니다.")
        col_load, col_save = st.columns(2)

        with col_load:
            st.markdown("**견적 불러오기**")
            search_term = st.text_input("검색 (전화번호 전체 또는 끝 4자리)", key="gdrive_search_term_tab1", help="전체 전화번호 또는 전화번호 끝 4자리를 입력하세요.")
            if st.button("🔍 견적 검색", key="gdrive_search_button_tab1"):
                st.session_state.gdrive_search_results = []
                st.session_state.gdrive_file_options_map = {}
                st.session_state.gdrive_selected_file_id = None
                st.session_state.gdrive_selected_filename = None
                search_term_strip = search_term.strip()
                if search_term_strip:
                    with st.spinner("🔄 Google Drive에서 JSON 검색 중..."):
                        all_gdrive_results = gdrive.find_files_by_name_contains(search_term_strip, mime_types="application/json")
                    processed_results = []
                    if all_gdrive_results:
                        if len(search_term_strip) == 4 and search_term_strip.isdigit():
                            for r_item in all_gdrive_results:
                                file_name_stem = os.path.splitext(r_item['name'])[0]
                                if file_name_stem.endswith(search_term_strip):
                                    processed_results.append(r_item)
                        else: # 전체 번호 검색 또는 기타 검색어
                            # 저장 시 파일명이 항상 숫자이므로, 검색어도 숫자인지 확인 후 정확히 일치하는 것만 필터링 가능
                            # 또는 gdrive.find_files_by_name_contains 결과 그대로 사용 (기존 로직)
                            processed_results = all_gdrive_results
                    if processed_results:
                        st.session_state.gdrive_search_results = processed_results
                        st.session_state.gdrive_file_options_map = {pr_item['name']: pr_item['id'] for pr_item in processed_results}
                        if processed_results:
                            st.session_state.gdrive_selected_filename = processed_results[0].get('name')
                            st.session_state.gdrive_selected_file_id = processed_results[0].get('id')
                        st.success(f"✅ {len(processed_results)}개 검색 완료.")
                    else: st.warning("⚠️ 해당 파일 없음.")
                else: st.warning("⚠️ 검색어를 입력하세요.")

            if st.session_state.get('gdrive_search_results'):
                file_options_display = list(st.session_state.gdrive_file_options_map.keys())
                current_selection_index = 0
                if st.session_state.get('gdrive_selected_filename') in file_options_display:
                    try: current_selection_index = file_options_display.index(st.session_state.gdrive_selected_filename)
                    except ValueError: current_selection_index = 0
                elif file_options_display :
                     st.session_state.gdrive_selected_filename = file_options_display[0]
                     st.session_state.gdrive_selected_file_id = st.session_state.gdrive_file_options_map.get(file_options_display[0])
                     current_selection_index = 0
                on_change_callback_gdrive = getattr(callbacks, 'update_selected_gdrive_id', None)
                st.selectbox(
                    "불러올 JSON 파일 선택:", file_options_display,
                    key="gdrive_selected_filename_widget_tab1", index=current_selection_index,
                    on_change=on_change_callback_gdrive if callable(on_change_callback_gdrive) else None
                )
                if callable(on_change_callback_gdrive) and \
                   st.session_state.get("gdrive_selected_filename_widget_tab1") != st.session_state.get('gdrive_selected_filename'):
                    on_change_callback_gdrive()

            load_button_disabled = not bool(st.session_state.get('gdrive_selected_file_id'))
            if st.button("📂 선택 견적 불러오기", disabled=load_button_disabled, key="load_gdrive_btn_tab1"):
                json_file_id = st.session_state.gdrive_selected_file_id
                if json_file_id:
                    with st.spinner(f"🔄 '{st.session_state.gdrive_selected_filename}' 로딩 중..."):
                        loaded_content = gdrive.load_json_file(json_file_id)
                    if loaded_content:
                        update_basket_callback_ref = getattr(callbacks, 'update_basket_quantities', lambda: None)
                        if 'uploaded_image_paths' not in loaded_content or \
                           not isinstance(loaded_content.get('uploaded_image_paths'), list):
                            loaded_content['uploaded_image_paths'] = []
                        load_success = load_state_from_data(loaded_content, update_basket_callback_ref)
                        if load_success:
                            st.session_state.image_uploader_key_counter +=1
                            st.success("✅ 견적 데이터 로딩 완료.")
                            st.rerun()
                        else: st.error("❌ 저장된 데이터 형식 오류로 로딩 실패.")
                    else: st.error(f"❌ '{st.session_state.gdrive_selected_filename}' 파일 로딩 또는 JSON 파싱 실패.")
                else: st.warning("⚠️ 불러올 파일을 선택해주세요.")

        with col_save:
            st.markdown("**현재 견적 저장**")
            with st.form(key="save_quote_form_tab1"):
                # 표시용 예시 파일명
                raw_phone_for_display = st.session_state.get('customer_phone', '').strip()
                # utils.sanitize_phone_number가 로드되었다고 가정 (app.py에서 utils를 먼저 임포트)
                example_sanitized_phone = utils.sanitize_phone_number(raw_phone_for_display)
                example_json_fname = f"{example_sanitized_phone}.json" if example_sanitized_phone else "전화번호입력후생성.json"

                st.caption(f"JSON 파일명 예시: `{example_json_fname}` (같은 번호로 저장 시 덮어쓰기)")
                submitted = st.form_submit_button("💾 Google Drive에 저장")
                if submitted:
                    raw_customer_phone = st.session_state.get('customer_phone', '').strip()

                    # 전화번호 정규화 (utils.py의 함수 사용)
                    sanitized_customer_phone = ""
                    if hasattr(utils, 'sanitize_phone_number'):
                        sanitized_customer_phone = utils.sanitize_phone_number(raw_customer_phone)
                    else: # utils.py 또는 함수 접근 불가 시 대체 로직
                        st.error("전화번호 처리 유틸리티를 로드할 수 없습니다. 전화번호를 숫자만으로 입력해주세요.")
                        # 직접 re 사용 (utils 임포트 실패 대비) - 이 경우 re 임포트 필요
                        # sanitized_customer_phone = re.sub(r'\D', '', raw_customer_phone)

                    # 정규화된 전화번호로 세션 상태 업데이트 (중요!)
                    st.session_state.customer_phone = sanitized_customer_phone

                    # 유효성 검사 (정규화된 번호 기준)
                    # 예: 최소 길이 검사 (필요에 따라 로직 수정)
                    if not sanitized_customer_phone or not sanitized_customer_phone.isdigit() or len(sanitized_customer_phone) < 9: # 예시: 국내 유효번호 최소길이 감안
                        st.error("⚠️ 저장 실패: 유효한 고객 전화번호를 입력해주세요 (예: 01012345678 또는 021234567).")
                    else:
                        json_filename = f"{sanitized_customer_phone}.json" # 정규화된 번호로 파일명 생성

                        # prepare_state_for_save는 이제 정규화된 st.session_state.customer_phone을 사용
                        state_data_to_save = prepare_state_for_save()

                        if 'uploaded_image_paths' not in state_data_to_save or \
                           not isinstance(state_data_to_save.get('uploaded_image_paths'), list):
                             state_data_to_save['uploaded_image_paths'] = st.session_state.get('uploaded_image_paths', [])
                        try:
                            with st.spinner(f"🔄 '{json_filename}' 저장 중..."):
                                save_json_result = gdrive.save_json_file(json_filename, state_data_to_save)
                            if save_json_result and save_json_result.get('id'):
                                st.success(f"✅ '{json_filename}' 저장 완료.")
                            else: st.error(f"❌ '{json_filename}' 저장 실패.")
                        except Exception as save_err:
                            st.error(f"❌ '{json_filename}' 저장 중 예외 발생: {save_err}")
    st.divider()

    st.header("📝 고객 기본 정보")
    move_type_options_tab1 = MOVE_TYPE_OPTIONS
    sync_move_type_callback_ref = getattr(callbacks, 'sync_move_type', None)
    if move_type_options_tab1:
        current_base_move_type = st.session_state.get('base_move_type', move_type_options_tab1[0] if move_type_options_tab1 else None)
        try: current_index_tab1 = move_type_options_tab1.index(current_base_move_type)
        except ValueError: current_index_tab1 = 0
        st.radio(
            "🏢 **기본 이사 유형**", options=move_type_options_tab1, index=current_index_tab1, horizontal=True,
            key="base_move_type_widget_tab1",
            on_change=sync_move_type_callback_ref if callable(sync_move_type_callback_ref) else None,
            args=("base_move_type_widget_tab1",) if callable(sync_move_type_callback_ref) else None
        )
    else: st.warning("이사 유형 옵션을 로드할 수 없습니다.")

    col_opts1, col_opts2, col_opts3 = st.columns(3)
    with col_opts1: st.checkbox("📦 보관이사 여부", key="is_storage_move")
    with col_opts2: st.checkbox("🛣️ 장거리 이사 적용", key="apply_long_distance")
    with col_opts3: st.checkbox("↪️ 경유지 이사 여부", key="has_via_point")

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("👤 고객명", key="customer_name")
        st.text_input("📍 출발지 주소", key="from_location")
        if st.session_state.get('apply_long_distance'):
            ld_options = data.long_distance_options if hasattr(data,'long_distance_options') else []
            st.selectbox("🛣️ 장거리 구간 선택", ld_options, key="long_distance_selector")
        st.text_input("🔼 출발지 층수", key="from_floor", placeholder="예: 3, B1, -1")
        method_options = data.METHOD_OPTIONS if hasattr(data,'METHOD_OPTIONS') else []
        st.selectbox("🛠️ 출발지 작업 방법", method_options, key="from_method")
        current_moving_date_val = st.session_state.get('moving_date')
        if not isinstance(current_moving_date_val, date):
             try: kst_def = pytz.timezone("Asia/Seoul"); default_date_def = datetime.now(kst_def).date()
             except Exception: default_date_def = datetime.now().date()
             st.session_state.moving_date = default_date_def
        st.date_input("🗓️ 이사 예정일 (출발일)", key="moving_date")
    with col2:
        # 전화번호 입력 시, st.session_state.customer_phone이 저장 로직에서 정규화될 것임
        st.text_input("📞 전화번호", key="customer_phone", placeholder="010-1234-5678 또는 01012345678")
        st.text_input("📧 이메일", key="customer_email", placeholder="email@example.com")
        st.text_input("📍 도착지 주소", key="to_location")
        st.text_input("🔽 도착지 층수", key="to_floor", placeholder="예: 5, B2, -2")
        method_options_to = data.METHOD_OPTIONS if hasattr(data,'METHOD_OPTIONS') else []
        st.selectbox("🛠️ 도착지 작업 방법", method_options_to, key="to_method")

    # --- *** 결제 옵션 UI 추가 *** ---
    with st.container(border=True):
        st.subheader("💳 결제 관련 옵션")
        col_pay_opt_tab1_1, col_pay_opt_tab1_2 = st.columns(2)
        with col_pay_opt_tab1_1:
            st.checkbox("세금계산서 발행 (견적가에 VAT 10% 추가)", key="issue_tax_invoice")
        with col_pay_opt_tab1_2:
            st.checkbox("카드 결제 (견적가에 수수료 13% 추가)", key="card_payment")
            st.caption("카드 수수료는 VAT 포함 금액에 부과될 수 있습니다.") # 이 문구는 정책에 따라 조정
    # --- *** 결제 옵션 UI 추가 완료 *** ---
    st.divider()


    if UPLOAD_DIR: # 이미지 업로드 섹션
        st.subheader("🖼️ 관련 이미지 업로드")
        uploader_widget_key = f"image_uploader_tab1_instance_{st.session_state.image_uploader_key_counter}"
        uploaded_files = st.file_uploader(
            "이미지 파일을 선택해주세요 (여러 파일 가능)", type=["png", "jpg", "jpeg"],
            accept_multiple_files=True, key=uploader_widget_key,
            help="파일을 선택하거나 여기에 드래그앤드롭 하세요."
        )
        if uploaded_files:
            newly_saved_paths_this_run = []
            current_tracked_filenames = {os.path.basename(p) for p in st.session_state.get('uploaded_image_paths', [])} # 안전하게 get 사용

            # 이미지 파일명에 사용할 전화번호 (정규화된 번호 사용)
            img_phone_prefix = st.session_state.get('customer_phone', 'unknown_phone').strip() # 이미 정규화된 번호가 customer_phone에 있어야 함
            if not img_phone_prefix: img_phone_prefix = 'no_phone_img' # 정규화 후에도 비어있다면 대체 문자열

            for uploaded_file_obj in uploaded_files:
                original_filename_sanitized = "".join(c if c.isalnum() or c in ['.', '_'] else '_' for c in uploaded_file_obj.name)
                # img_phone_prefix는 이미 숫자만 있어야 함
                base_filename = f"{img_phone_prefix}_{original_filename_sanitized}"
                counter = 1
                filename_to_save = base_filename
                prospective_save_path = os.path.join(UPLOAD_DIR, filename_to_save)
                while os.path.exists(prospective_save_path):
                    name_part, ext_part = os.path.splitext(base_filename)
                    filename_to_save = f"{name_part}_{counter}{ext_part}"
                    prospective_save_path = os.path.join(UPLOAD_DIR, filename_to_save)
                    counter += 1
                final_save_path = prospective_save_path
                final_filename_to_save = os.path.basename(final_save_path)
                if final_filename_to_save not in current_tracked_filenames and final_save_path not in newly_saved_paths_this_run :
                    try:
                        with open(final_save_path, "wb") as f: f.write(uploaded_file_obj.getbuffer())
                        newly_saved_paths_this_run.append(final_save_path)
                        st.success(f"'{uploaded_file_obj.name}' 저장 완료: {final_filename_to_save}")
                    except Exception as e: st.error(f"'{uploaded_file_obj.name}' 저장 실패: {e}")

            if newly_saved_paths_this_run:
                current_paths = st.session_state.get('uploaded_image_paths', [])
                current_paths.extend(newly_saved_paths_this_run)
                st.session_state.uploaded_image_paths = sorted(list(set(current_paths)))
                st.session_state.image_uploader_key_counter += 1
                st.rerun()
            elif uploaded_files and not newly_saved_paths_this_run: # 파일은 있었으나 새로 저장된게 없을 때 (중복 등)
                st.session_state.image_uploader_key_counter += 1 # 업로더 리프레시
                st.rerun()

        current_image_paths = st.session_state.get('uploaded_image_paths', [])
        if current_image_paths:
            st.markdown("**업로드된 이미지:**")
            def delete_image_action(image_path_to_delete):
                try:
                    if os.path.exists(image_path_to_delete): os.remove(image_path_to_delete); st.toast(f"삭제 성공: {os.path.basename(image_path_to_delete)}", icon="🗑️")
                    else: st.toast(f"파일 없음: {os.path.basename(image_path_to_delete)}", icon="⚠️")
                except Exception as e_del: st.error(f"파일 삭제 오류 ({os.path.basename(image_path_to_delete)}): {e_del}")

                current_paths_on_delete = st.session_state.get('uploaded_image_paths', [])
                if image_path_to_delete in current_paths_on_delete:
                    current_paths_on_delete.remove(image_path_to_delete)
                    st.session_state.uploaded_image_paths = current_paths_on_delete # 업데이트된 리스트로 세션 상태 갱신
                st.session_state.image_uploader_key_counter += 1
                st.rerun()

            paths_to_display_and_delete = list(current_image_paths) # 복사본 사용
            valid_display_paths = [p for p in paths_to_display_and_delete if isinstance(p, str) and os.path.exists(p)]

            if len(valid_display_paths) != len(paths_to_display_and_delete): # 유효하지 않은 경로가 있다면 세션 상태 정리
                st.session_state.uploaded_image_paths = valid_display_paths
                if paths_to_display_and_delete: st.rerun() # 변경사항 반영 위해 재실행

            if valid_display_paths:
                cols_per_row_display = 3
                for i in range(0, len(valid_display_paths), cols_per_row_display):
                    image_paths_in_row = valid_display_paths[i:i+cols_per_row_display]
                    cols_display = st.columns(cols_per_row_display)
                    for col_idx, img_path_display in enumerate(image_paths_in_row):
                        with cols_display[col_idx]:
                            st.image(img_path_display, caption=os.path.basename(img_path_display), use_container_width=True)
                            delete_btn_key = f"del_btn_{img_path_display.replace('/', '_').replace('.', '_').replace(' ', '_')}_{i}_{col_idx}"
                            if st.button(f"삭제", key=delete_btn_key, type="secondary", help=f"{os.path.basename(img_path_display)} 삭제하기"):
                                delete_image_action(img_path_display)
            elif not current_image_paths : st.caption("업로드된 이미지가 없습니다.") # uploaded_image_paths가 비어있을 때
            elif paths_to_display_and_delete and not valid_display_paths: st.caption("표시할 유효한 이미지가 없습니다. (경로 오류)") # 리스트는 있으나 유효 경로 없을 때

    else:
        st.warning("이미지 업로드 디렉토리 설정 오류로 이미지 업로드 기능이 비활성화되었습니다.")

    kst_time_str = utils.get_current_kst_time_str() if hasattr(utils, 'get_current_kst_time_str') else ''
    st.caption(f"⏱️ 견적 생성일: {kst_time_str}")
    st.divider()

    if st.session_state.get('has_via_point'):
        with st.container(border=True):
            st.subheader("↪️ 경유지 정보")
            st.text_input("📍 경유지 주소", key="via_point_location")
            method_options_via = data.METHOD_OPTIONS if hasattr(data,'METHOD_OPTIONS') else []
            st.selectbox("🛠️ 경유지 작업 방법", method_options_via, key="via_point_method")
        st.divider()

    if st.session_state.get('is_storage_move'):
        with st.container(border=True):
            st.subheader("📦 보관이사 추가 정보")
            storage_options = data.STORAGE_TYPE_OPTIONS if hasattr(data,'STORAGE_TYPE_OPTIONS') else []
            st.radio("보관 유형 선택:", storage_options, key="storage_type", horizontal=True)
            st.checkbox("🔌 보관 중 전기사용", key="storage_use_electricity")
            min_arrival_date = st.session_state.get('moving_date', date.today())
            if not isinstance(min_arrival_date, date): min_arrival_date = date.today()
            current_arrival_date = st.session_state.get('arrival_date')
            if not isinstance(current_arrival_date, date) or current_arrival_date < min_arrival_date:
                st.session_state.arrival_date = min_arrival_date
            st.date_input("🚚 도착 예정일 (보관 후)", key="arrival_date", min_value=min_arrival_date)
            moving_dt, arrival_dt = st.session_state.get('moving_date'), st.session_state.get('arrival_date')
            calculated_duration = max(1, (arrival_dt - moving_dt).days + 1) if isinstance(moving_dt,date) and isinstance(arrival_dt,date) and arrival_dt >= moving_dt else 1
            st.session_state.storage_duration = calculated_duration
            st.markdown(f"**계산된 보관 기간:** **`{calculated_duration}`** 일")
        st.divider()

    with st.container(border=True):
        st.header("🗒️ 고객 요구사항")
        st.text_area("기타 특이사항이나 요청사항을 입력해주세요.", height=100, key="special_notes")

# --- End of render_tab1 function ---