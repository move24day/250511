# ui_tab3.py (결제 옵션 UI 제거, 요약 정보 표시 수정은 유지, Excel 및 이미지 생성/다운로드 통합)
import streamlit as st
import pandas as pd
import io
import pytz
from datetime import datetime, date
import traceback
import re

# Import necessary custom modules
try:
    import data
    import utils
    import calculations
    import pdf_generator # PDF 생성 및 이미지 변환에 필요
    import excel_filler
    import email_utils
    import callbacks
    from state_manager import MOVE_TYPE_OPTIONS
    import mms_utils # MMS 발송에 필요
except ImportError as e:
    st.error(f"UI Tab 3: 필수 모듈 로딩 실패 - {e}")
    if hasattr(e, "name"):
        if e.name == "email_utils": st.warning("email_utils.py 로드 실패. 이메일 발송 비활성화.")
        elif e.name == "mms_utils": st.warning("mms_utils.py 로드 실패. MMS 발송 비활성화.")
        elif e.name == "pdf_generator": st.error("pdf_generator.py 로드 실패. PDF/이미지 생성 비활성화.")
    if "MOVE_TYPE_OPTIONS" not in globals(): MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"]
    if not all(module_name in globals() for module_name in ["data", "utils", "calculations", "callbacks", "state_manager"]):
        st.error("UI Tab 3: 핵심 데이터/유틸리티 모듈 로딩 실패.")
except Exception as e:
    st.error(f"UI Tab 3: 모듈 로딩 중 오류 - {e}")
    traceback.print_exc()
    if "MOVE_TYPE_OPTIONS" not in globals(): MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"]
    st.stop()

def render_tab3():
    st.header("💰 계산 및 옵션 ")
    update_basket_quantities_callback = getattr(callbacks, "update_basket_quantities", None)
    sync_move_type_callback = getattr(callbacks, "sync_move_type", None)
    handle_item_update_callback = getattr(callbacks, "handle_item_update", None)

    if not callable(update_basket_quantities_callback) or not callable(sync_move_type_callback):
        st.error("UI Tab 3: 콜백 함수 로드 실패.")

    st.subheader("🏢 이사 유형 ")
    current_move_type = st.session_state.get("base_move_type", MOVE_TYPE_OPTIONS[0] if MOVE_TYPE_OPTIONS else "가정 이사 🏠")
    current_index_tab3 = 0
    if MOVE_TYPE_OPTIONS:
        try: current_index_tab3 = MOVE_TYPE_OPTIONS.index(current_move_type)
        except (ValueError, TypeError):
            current_index_tab3 = 0
            if current_move_type not in MOVE_TYPE_OPTIONS:
                 st.session_state.base_move_type = MOVE_TYPE_OPTIONS[0]
                 if 'base_move_type_widget_tab1' in st.session_state:
                      st.session_state.base_move_type_widget_tab1 = MOVE_TYPE_OPTIONS[0]
                 if callable(handle_item_update_callback): handle_item_update_callback()
    else:
        st.error("이사 유형 옵션을 불러올 수 없습니다."); return

    st.radio(
        "기본 이사 유형:", options=MOVE_TYPE_OPTIONS, index=current_index_tab3, horizontal=True,
        key="base_move_type_widget_tab3", on_change=sync_move_type_callback, args=("base_move_type_widget_tab3",)
    )
    st.divider()

    with st.container(border=True): # 차량 선택
        st.subheader("🚚 차량 선택")
        col_v1_widget, col_v2_widget = st.columns([1, 2])
        with col_v1_widget:
            st.radio("차량 선택 방식:", ["자동 추천 차량 사용", "수동으로 차량 선택"], key="vehicle_select_radio", on_change=update_basket_quantities_callback)
        with col_v2_widget:
            current_move_type_widget = st.session_state.get('base_move_type')
            vehicle_prices_options_widget, available_trucks_widget = {}, []
            if current_move_type_widget and hasattr(data, 'vehicle_prices') and isinstance(data.vehicle_prices, dict):
                vehicle_prices_options_widget = data.vehicle_prices.get(current_move_type_widget, {})
            if vehicle_prices_options_widget and hasattr(data, 'vehicle_specs') and isinstance(data.vehicle_specs, dict):
                available_trucks_widget = sorted([truck for truck in vehicle_prices_options_widget.keys() if truck in data.vehicle_specs], key=lambda x: data.vehicle_specs.get(x, {}).get("capacity", 0))

            use_auto_widget = st.session_state.get('vehicle_select_radio') == "자동 추천 차량 사용"
            recommended_vehicle_auto_from_state = st.session_state.get('recommended_vehicle_auto')
            final_vehicle_from_state = st.session_state.get('final_selected_vehicle')
            current_total_volume, current_total_weight = st.session_state.get("total_volume", 0.0), st.session_state.get("total_weight", 0.0)

            if use_auto_widget:
                if final_vehicle_from_state and final_vehicle_from_state in available_trucks_widget:
                    st.success(f"✅ 자동 선택됨: **{final_vehicle_from_state}**")
                    spec = data.vehicle_specs.get(final_vehicle_from_state) if hasattr(data, "vehicle_specs") else None
                    if spec:
                        st.caption(f"선택차량 최대 용량: {spec.get('capacity', 'N/A')}m³, {spec.get('weight_capacity', 'N/A'):,}kg")
                        st.caption(f"현재 이사짐 예상: {current_total_volume:.2f}m³, {current_total_weight:.2f}kg")
                else:
                    error_msg = "⚠️ 자동 추천 불가: "
                    if recommended_vehicle_auto_from_state and "초과" in recommended_vehicle_auto_from_state: error_msg += f"물량 초과({recommended_vehicle_auto_from_state}). 수동 선택 필요."
                    elif recommended_vehicle_auto_from_state and recommended_vehicle_auto_from_state not in available_trucks_widget : error_msg += f"추천 차량({recommended_vehicle_auto_from_state})은 현재 이사 유형에 없음. 수동 선택 필요."
                    elif current_total_volume > 0 or current_total_weight > 0 : error_msg += "적합 차량 없음. 수동 선택 필요."
                    else: error_msg += "물품 미선택 또는 정보 부족."
                    st.error(error_msg)
                    if not available_trucks_widget: st.error("❌ 현재 이사 유형에 선택 가능한 차량 정보가 없습니다.")
                    else:
                        current_manual_selection_widget = st.session_state.get("manual_vehicle_select_value")
                        current_index_widget = available_trucks_widget.index(current_manual_selection_widget) if current_manual_selection_widget in available_trucks_widget else 0
                        if not current_manual_selection_widget and available_trucks_widget: st.session_state.manual_vehicle_select_value = available_trucks_widget[0]
                        st.selectbox("수동으로 차량 선택:", available_trucks_widget, index=current_index_widget, key="manual_vehicle_select_value", on_change=update_basket_quantities_callback)
                        if final_vehicle_from_state and final_vehicle_from_state in available_trucks_widget: st.info(f"ℹ️ 수동 선택됨: **{final_vehicle_from_state}**")
            else: # Manual
                if not available_trucks_widget: st.error("❌ 현재 이사 유형에 선택 가능한 차량 정보가 없습니다.")
                else:
                    current_manual_selection_widget = st.session_state.get("manual_vehicle_select_value")
                    current_index_widget = available_trucks_widget.index(current_manual_selection_widget) if current_manual_selection_widget in available_trucks_widget else 0
                    if not current_manual_selection_widget and available_trucks_widget: st.session_state.manual_vehicle_select_value = available_trucks_widget[0]
                    st.selectbox("차량 직접 선택:", available_trucks_widget, index=current_index_widget, key="manual_vehicle_select_value", on_change=update_basket_quantities_callback)
                    if final_vehicle_from_state and final_vehicle_from_state in available_trucks_widget:
                        st.info(f"ℹ️ 수동 선택됨: **{final_vehicle_from_state}**")
                        spec_manual = data.vehicle_specs.get(final_vehicle_from_state) if hasattr(data, "vehicle_specs") else None
                        if spec_manual:
                            st.caption(f"선택차량 최대 용량: {spec_manual.get('capacity', 'N/A')}m³, {spec_manual.get('weight_capacity', 'N/A'):,}kg")
                            st.caption(f"현재 이사짐 예상: {current_total_volume:.2f}m³, {current_total_weight:.2f}kg")
    st.divider()

    with st.container(border=True): # 작업 조건 및 추가 옵션
        st.subheader("🛠️ 작업 조건 및 추가 옵션")
        sky_from, sky_to = (st.session_state.get("from_method") == "스카이 🏗️"), (st.session_state.get("to_method") == "스카이 🏗️")
        if sky_from or sky_to:
            st.warning("스카이 작업 선택됨 - 시간 입력 필요", icon="🏗️")
            cols_sky = st.columns(2)
            if sky_from: cols_sky[0].number_input("출발 스카이 시간(h)", min_value=1, step=1, key="sky_hours_from")
            if sky_to: cols_sky[1].number_input("도착 스카이 시간(h)", min_value=1, step=1, key="sky_hours_final")
            st.write("")
        col_add1, col_add2 = st.columns(2)
        col_add1.number_input("추가 남성 인원 👨", min_value=0, step=1, key="add_men")
        col_add2.number_input("추가 여성 인원 👩", min_value=0, step=1, key="add_women")
        st.write("")
        st.subheader("🚚 실제 투입 차량 ")
        dispatched_cols = st.columns(4)
        dispatched_cols[0].number_input("1톤", min_value=0, step=1, key="dispatched_1t")
        dispatched_cols[1].number_input("2.5톤", min_value=0, step=1, key="dispatched_2_5t")
        dispatched_cols[2].number_input("3.5톤", min_value=0, step=1, key="dispatched_3_5t")
        dispatched_cols[3].number_input("5톤", min_value=0, step=1, key="dispatched_5t")
        st.caption("견적 계산과 별개로, 실제 현장에 투입될 차량 대수를 입력합니다.")
        st.write("")

        show_remove_housewife_option = False
        base_housewife_count_for_option = 0
        discount_amount_for_option = 0
        current_move_type_for_option = st.session_state.get("base_move_type")
        final_vehicle_for_option_display = st.session_state.get("final_selected_vehicle")

        if current_move_type_for_option == "가정 이사 🏠" and \
           final_vehicle_for_option_display and \
           hasattr(data, "vehicle_prices") and \
           isinstance(data.vehicle_prices.get(current_move_type_for_option), dict) and \
           final_vehicle_for_option_display in data.vehicle_prices[current_move_type_for_option]:
            vehicle_details = data.vehicle_prices[current_move_type_for_option][final_vehicle_for_option_display]
            base_housewife_count_for_option = vehicle_details.get("housewife", 0)
            if base_housewife_count_for_option > 0:
                show_remove_housewife_option = True
                additional_person_cost_for_option = getattr(data, "ADDITIONAL_PERSON_COST", 200000)
                discount_amount_for_option = additional_person_cost_for_option * base_housewife_count_for_option

        if show_remove_housewife_option:
            st.checkbox(
                f"기본 여성({base_housewife_count_for_option}명) 제외 (비용 할인: -{discount_amount_for_option:,.0f}원)",
                key="remove_base_housewife"
            )
        else:
            if "remove_base_housewife" in st.session_state:
                st.session_state.remove_base_housewife = False

        col_waste1, col_waste2 = st.columns([1,2])
        col_waste1.checkbox("폐기물 처리 필요 🗑️", key="has_waste_check")
        if st.session_state.get("has_waste_check"):
            waste_cost_per_ton = getattr(data, "WASTE_DISPOSAL_COST_PER_TON", 0)
            waste_cost_display = waste_cost_per_ton if isinstance(waste_cost_per_ton, (int, float)) else 0
            col_waste2.number_input("폐기물 양 (톤)", min_value=0.5, max_value=10.0, step=0.5, key="waste_tons_input", format="%.1f")
            if waste_cost_display > 0: col_waste2.caption(f"💡 1톤당 {waste_cost_display:,}원 추가 비용 발생")

        st.write("📅 **날짜 유형 선택** (중복 가능, 해당 시 할증)")
        date_options = ["이사많은날 🏠", "손없는날 ✋", "월말 📅", "공휴일 🎉", "금요일 📅"]
        date_surcharges_defined = hasattr(data, "special_day_prices") and isinstance(data.special_day_prices, dict)
        if not date_surcharges_defined: st.warning("data.py에 날짜 할증 정보가 없습니다.")
        date_keys = [f"date_opt_{i}_widget" for i in range(len(date_options))]
        cols_date = st.columns(len(date_options))
        for i, option in enumerate(date_options):
            surcharge = data.special_day_prices.get(option, 0) if date_surcharges_defined else 0
            cols_date[i].checkbox(option, key=date_keys[i], help=f"{surcharge:,}원 할증" if surcharge > 0 else "")
    st.divider()

    with st.container(border=True):
        st.subheader("💰 수기 조정 및 계약금")
        cols_adj_new = st.columns(2)
        with cols_adj_new[0]:
            st.number_input("📝 계약금", min_value=0, step=10000, key="deposit_amount", format="%d")
        with cols_adj_new[1]:
            st.number_input("💰 추가 조정 (+/-)", step=10000, key="adjustment_amount", format="%d")

        cols_extra_fees = st.columns(2)
        with cols_extra_fees[0]:
            st.number_input("🪜 사다리 추가요금", min_value=0, step=10000, key="regional_ladder_surcharge", format="%d")
        if st.session_state.get("has_via_point", False):
             with cols_extra_fees[1]:
                st.number_input("↪️ 경유지 추가요금", min_value=0, step=10000, key="via_point_surcharge", format="%d")
        else:
            with cols_extra_fees[1]:
                pass
    st.divider()

    st.header("💵 최종 견적 결과")
    final_selected_vehicle_calc = st.session_state.get("final_selected_vehicle")
    total_cost_display, cost_items_display, personnel_info_display, has_cost_error = 0, [], {}, False

    if final_selected_vehicle_calc:
        try:
            if st.session_state.get("is_storage_move"):
                m_dt, a_dt = st.session_state.get("moving_date"), st.session_state.get("arrival_date")
                st.session_state.storage_duration = max(1, (a_dt - m_dt).days + 1) if isinstance(m_dt, date) and isinstance(a_dt, date) and a_dt >= m_dt else 1

            current_state_dict = st.session_state.to_dict()
            if hasattr(calculations, "calculate_total_moving_cost") and callable(calculations.calculate_total_moving_cost):
                total_cost_display, cost_items_display, personnel_info_display = calculations.calculate_total_moving_cost(current_state_dict)
                st.session_state.update({
                    "calculated_cost_items_for_pdf": cost_items_display,
                    "total_cost_for_pdf": total_cost_display,
                    "personnel_info_for_pdf": personnel_info_display
                })
                if any(isinstance(item, (list, tuple)) and len(item) > 0 and str(item[0]) == "오류" for item in cost_items_display): has_cost_error = True
            else:
                st.error("최종 비용 계산 함수 로드 실패."); has_cost_error = True
                st.session_state.update({"calculated_cost_items_for_pdf": [], "total_cost_for_pdf": 0, "personnel_info_for_pdf": {}})

            total_cost_num = int(total_cost_display) if isinstance(total_cost_display, (int, float)) else 0
            deposit_val = st.session_state.get("deposit_amount", 0)
            deposit_amount_num = int(deposit_val) if deposit_val is not None else 0
            remaining_balance_num = total_cost_num - deposit_amount_num

            st.subheader(f"💰 총 견적 비용: {total_cost_num:,.0f} 원")
            st.subheader(f"➖ 계약금: {deposit_amount_num:,.0f} 원")
            st.subheader(f"➡️ 잔금 (총 비용 - 계약금): {remaining_balance_num:,.0f} 원")
            st.write("")

            st.subheader("📊 비용 상세 내역")
            if has_cost_error:
                err_item = next((item for item in cost_items_display if isinstance(item, (list, tuple)) and len(item)>0 and str(item[0]) == "오류"), None)
                st.error(f"비용 계산 오류: {err_item[2] if err_item and len(err_item) > 2 else '알 수 없는 오류'}")
            elif cost_items_display:
                valid_costs = [item for item in cost_items_display if not (isinstance(item, (list, tuple)) and len(item) > 0 and str(item[0]) == "오류")]
                if valid_costs:
                    st.dataframe(pd.DataFrame(valid_costs, columns=["항목", "금액", "비고"]).style.format({"금액": "{:,.0f}"}).set_properties(**{'text-align':'right'}, subset=['금액']).set_properties(**{'text-align':'left'}, subset=['항목','비고']), use_container_width=True, hide_index=True)
                else: st.info("ℹ️ 유효한 비용 항목 없음.")
            else: st.info("ℹ️ 계산된 비용 항목 없음.")
            st.write("")

            special_notes = st.session_state.get('special_notes')
            if special_notes and special_notes.strip(): st.subheader("📝 고객요구사항"); st.info(special_notes)

            st.subheader("📋 이사 정보 요약")
            summary_display_possible = bool(final_selected_vehicle_calc) and not has_cost_error

            if summary_display_possible:
                try:
                    customer_name_summary = st.session_state.get('customer_name', '')
                    phone_summary = st.session_state.get('customer_phone', '')
                    email_summary = st.session_state.get('customer_email', '')

                    vehicle_type_summary = final_selected_vehicle_calc
                    vehicle_tonnage_summary = ""
                    if isinstance(vehicle_type_summary, str):
                        match_summary = re.search(r'(\d+(\.\d+)?\s*톤)', vehicle_type_summary)
                        vehicle_tonnage_summary = match_summary.group(1).strip() if match_summary else vehicle_type_summary

                    p_info_summary = personnel_info_display
                    men_summary = p_info_summary.get('final_men', 0)
                    women_summary = p_info_summary.get('final_women', 0)

                    if women_summary > 0:
                        ppl_summary = f"{men_summary}+{women_summary}명"
                    else:
                        ppl_summary = f"{men_summary}명"

                    def get_method_full_name(method_key):
                        method_str = str(st.session_state.get(method_key, '')).strip()
                        return method_str.split(" ")[0] if method_str else "정보 없음"
                    from_method_full, to_method_full = get_method_full_name('from_method'), get_method_full_name('to_method')

                    deposit_for_summary = int(st.session_state.get("deposit_amount", 0))
                    calculated_total_for_summary = int(total_cost_display) if isinstance(total_cost_display, (int,float)) else 0
                    remaining_for_summary = calculated_total_for_summary - deposit_for_summary

                    from_addr_summary = st.session_state.get('from_location', '정보 없음')
                    to_addr_summary = st.session_state.get('to_location', '정보 없음')

                    b_name_summary, move_t_summary = "포장 자재 📦", st.session_state.get('base_move_type', '')
                    q_b_s, q_mb_s, q_book_s = 0, 0, 0
                    if move_t_summary:
                        try:
                            q_b_s = int(st.session_state.get(f"qty_{move_t_summary}_{b_name_summary}_바구니", 0))
                            q_mb_s = int(st.session_state.get(f"qty_{move_t_summary}_{b_name_summary}_중박스", st.session_state.get(f"qty_{move_t_summary}_{b_name_summary}_중자바구니", 0)))
                            q_book_s = int(st.session_state.get(f"qty_{move_t_summary}_{b_name_summary}_책바구니", 0))
                        except: pass

                    bask_display_parts = []
                    if q_b_s > 0: bask_display_parts.append(f"바구니 {q_b_s}개")
                    if q_mb_s > 0: bask_display_parts.append(f"중박스 {q_mb_s}개")
                    if q_book_s > 0: bask_display_parts.append(f"책바구니 {q_book_s}개")
                    bask_summary_str = ", ".join(bask_display_parts) if bask_display_parts else "바구니 정보 없음"

                    note_summary = st.session_state.get('special_notes', '')

                    is_storage_move = st.session_state.get('is_storage_move', False)
                    storage_prefix_text = "(보관) " if is_storage_move else ""
                    storage_details_text = ""
                    if is_storage_move:
                        storage_type = st.session_state.get('storage_type', '정보 없음')
                        storage_electric_text = "(전기사용)" if st.session_state.get('storage_use_electricity', False) else ""
                        storage_details_text = f"{storage_type} {storage_electric_text}".strip()

                    payment_option_texts = []
                    if st.session_state.get("issue_tax_invoice", False): payment_option_texts.append("세금계산서 발행 요청")
                    if st.session_state.get("card_payment", False): payment_option_texts.append("카드 결제 예정")
                    payment_options_summary = " / ".join(payment_option_texts) if payment_option_texts else ""

                    first_line_display = f"{from_addr_summary if from_addr_summary else '출발지 정보 없음'} -> {to_addr_summary if to_addr_summary else '도착지 정보 없음'} {storage_prefix_text}{vehicle_tonnage_summary if vehicle_tonnage_summary else vehicle_type_summary}".strip()
                    if email_summary and email_summary != '-': first_line_display += f" {email_summary}"
                    st.text(first_line_display)

                    if customer_name_summary: st.text(f"{customer_name_summary}")
                    if phone_summary and phone_summary != '-': st.text(f"{phone_summary}")
                    if email_summary and email_summary != '-': st.text(f"{email_summary}")
                    st.text("")
                    st.text(f"{vehicle_tonnage_summary if vehicle_tonnage_summary else vehicle_type_summary} / {ppl_summary}")
                    st.text("")
                    st.text(f"출발지: {from_method_full}")
                    st.text(f"도착지: {to_method_full}")
                    if st.session_state.get('has_via_point', False): st.text(f"경유지: {get_method_full_name('via_point_method')}")
                    st.text("")
                    st.text(f"계약금 {deposit_for_summary:,.0f}원 / 잔금 {remaining_for_summary:,.0f}원")
                    if payment_options_summary: st.text(f"({payment_options_summary})")
                    st.text("")
                    st.text(f"총 {calculated_total_for_summary:,.0f}원 중")

                    processed_for_summary = set()
                    if isinstance(cost_items_display, list):
                        for item_name_disp, item_cost_disp, _ in cost_items_display:
                            if str(item_name_disp) == "기본 운임" and item_cost_disp != 0:
                                st.text(f"이사비 {int(item_cost_disp):,}")
                                processed_for_summary.add(str(item_name_disp))
                                break
                        for item_name_disp, item_cost_disp, _ in cost_items_display:
                            name_str, cost_int = str(item_name_disp), int(item_cost_disp) if item_cost_disp is not None else 0
                            if name_str not in processed_for_summary and "사다리차" not in name_str and "스카이" not in name_str and "부가세" not in name_str and "카드" not in name_str and cost_int != 0 :
                                st.text(f"{name_str} {cost_int:,}")
                                processed_for_summary.add(name_str)
                        for item_name_disp, item_cost_disp, _ in cost_items_display:
                            name_str, cost_int = str(item_name_disp), int(item_cost_disp) if item_cost_disp is not None else 0
                            if name_str not in processed_for_summary and ("사다리차" in name_str or "스카이" in name_str) and cost_int != 0:
                                st.text(f"{name_str} {cost_int:,}")
                                processed_for_summary.add(name_str)
                        for item_name_disp, item_cost_disp, _ in cost_items_display:
                            name_str, cost_int = str(item_name_disp), int(item_cost_disp) if item_cost_disp is not None else 0
                            if name_str not in processed_for_summary and ("부가세" in name_str or "카드" in name_str) and cost_int != 0:
                                st.text(f"{name_str} {cost_int:,}")
                                processed_for_summary.add(name_str)
                    if not processed_for_summary and calculated_total_for_summary != 0 : st.text(f"기타 비용 합계 {calculated_total_for_summary:,}")
                    elif not processed_for_summary and calculated_total_for_summary == 0: st.text("세부 비용 내역 없음")
                    st.text("")

                    st.text("출발지 주소:"); st.text(from_addr_summary)
                    if is_storage_move and storage_details_text: st.text(storage_details_text)
                    st.text("")
                    st.text("도착지 주소:"); st.text(to_addr_summary)
                    st.text("")
                    if st.session_state.get('has_via_point', False):
                        st.text("경유지 주소:"); st.text(st.session_state.get('via_point_location', '정보 없음'))
                        st.text("")
                    st.text(bask_summary_str)
                    st.text("")
                    if note_summary and note_summary.strip() and note_summary != '-':
                        st.text("요구사항:")
                        for note_line in note_summary.strip().replace('\r\n', '\n').split('\n'): st.text(note_line.strip())
                except Exception as e_summary_direct:
                    st.error(f"❌ 요약 정보 생성 중 오류: {e_summary_direct}"); traceback.print_exc()
                    st.info("ℹ️ 요약 정보 표시 불가 (데이터 오류).")
            elif not final_selected_vehicle_calc: st.info("ℹ️ 차량 미선택으로 요약 정보 표시 불가.")
            else: st.info("ℹ️ 비용 계산 오류로 요약 정보 표시 불가.")
            st.divider()

            st.subheader("📄 견적서 생성, 발송 및 다운로드")
            can_generate_anything = bool(final_selected_vehicle_calc) and not has_cost_error and st.session_state.get("calculated_cost_items_for_pdf") and st.session_state.get("total_cost_for_pdf", 0) > 0
            cols_actions_main = st.columns([1, 1, 1]); cols_actions_email = st.columns(1)

            with cols_actions_main[0]: # MMS
                st.markdown("**① 이미지 견적서 (MMS)**")
                mms_possible = (hasattr(mms_utils, "send_mms_with_image") and hasattr(pdf_generator, "generate_pdf") and hasattr(pdf_generator, "generate_quote_image_from_pdf") and can_generate_anything and st.session_state.get("customer_phone"))
                if mms_possible:
                    if st.button("🖼️ MMS 발송", key="mms_send_button_main"):
                        customer_phone_mms, customer_name_mms = st.session_state.get("customer_phone"), st.session_state.get("customer_name", "고객")
                        pdf_args_mms = {"state_data": st.session_state.to_dict(), "calculated_cost_items": st.session_state.get("calculated_cost_items_for_pdf", []), "total_cost": st.session_state.get("total_cost_for_pdf", 0), "personnel_info": st.session_state.get("personnel_info_for_pdf", {})}
                        with st.spinner("견적서 PDF 생성 중..."): pdf_bytes_mms = pdf_generator.generate_pdf(**pdf_args_mms)
                        if pdf_bytes_mms:
                            with st.spinner("PDF를 이미지로 변환 중..."): image_bytes_mms = pdf_generator.generate_quote_image_from_pdf(pdf_bytes_mms, poppler_path=None)
                            if image_bytes_mms:
                                with st.spinner(f"{customer_phone_mms}으로 MMS 발송 준비 중..."):
                                    mms_filename, mms_text_message = f"견적서_{customer_name_mms}_{utils.get_current_kst_time_str('%y%m%d')}.jpg", f"{customer_name_mms}님, 요청하신 이사 견적서입니다. 감사합니다."
                                    mms_sent = mms_utils.send_mms_with_image(recipient_phone=customer_phone_mms, image_bytes=image_bytes_mms, filename=mms_filename, text_message=mms_text_message)
                                    if mms_sent: st.success(f"✅ MMS 발송 요청 완료")
                                    else: st.error("❌ MMS 발송 실패.")
                            else: st.error("❌ 견적서 이미지 생성 실패.")
                        else: st.error("❌ 견적서 PDF 생성 실패 (MMS용).")
                elif not (hasattr(mms_utils, "send_mms_with_image") and hasattr(pdf_generator, "generate_pdf") and hasattr(pdf_generator, "generate_quote_image_from_pdf")): st.caption("MMS/PDF/이미지 생성 모듈 오류")
                elif not can_generate_anything: st.caption("견적 내용 확인 필요")
                elif not st.session_state.get("customer_phone"): st.caption("고객 전화번호 필요")
                else: st.caption("MMS 발송 불가")

            with cols_actions_main[1]: # PDF
                st.markdown("**② 고객용 견적서 (PDF)**")
                pdf_possible = hasattr(pdf_generator, "generate_pdf") and can_generate_anything
                if pdf_possible:
                    if st.button("📄 PDF 생성 및 다운로드", key="pdf_customer_download_main"):
                        pdf_args_download = {"state_data": st.session_state.to_dict(), "calculated_cost_items": st.session_state.get("calculated_cost_items_for_pdf", []), "total_cost": st.session_state.get("total_cost_for_pdf", 0), "personnel_info": st.session_state.get("personnel_info_for_pdf", {})}
                        with st.spinner("PDF 생성 중..."): pdf_data_cust_download = pdf_generator.generate_pdf(**pdf_args_download)
                        if pdf_data_cust_download:
                            st.session_state['pdf_data_customer_for_download'] = pdf_data_cust_download
                            st.success("✅ PDF 생성 완료!")
                        else:
                            st.error("❌ PDF 생성 실패.")
                            if 'pdf_data_customer_for_download' in st.session_state: del st.session_state['pdf_data_customer_for_download']
                    if st.session_state.get('pdf_data_customer_for_download'):
                        fname_pdf_dl = f"견적서_{st.session_state.get('customer_name', '고객')}_{utils.get_current_kst_time_str('%y%m%d')}.pdf"
                        st.download_button(label="📥 다운로드 (PDF)", data=st.session_state['pdf_data_customer_for_download'], file_name=fname_pdf_dl, mime="application/pdf", key='dl_btn_pdf_main')
                    elif 'pdf_data_customer_for_download' not in st.session_state and pdf_possible : st.caption("생성 버튼을 눌러주세요.")
                elif not hasattr(pdf_generator, "generate_pdf"): st.caption("PDF 생성 모듈 오류")
                elif not can_generate_anything: st.caption("견적 내용 확인 필요")
                else: st.caption("PDF 생성 불가")


            # --- 수정된 "Excel 및 견적 이미지 생성" 섹션 ---
            with cols_actions_main[2]:
                st.markdown("**③ 견적서 파일 생성 (Excel, 이미지)**")

                excel_possible = hasattr(excel_filler, "fill_final_excel_template") and bool(final_selected_vehicle_calc)
                pdf_possible_for_image = hasattr(pdf_generator, "generate_pdf") and can_generate_anything
                image_conversion_possible = hasattr(pdf_generator, "generate_quote_image_from_pdf") and pdf_generator._PDF2IMAGE_AVAILABLE and pdf_generator._PILLOW_AVAILABLE

                if st.button("📊 Excel 및 견적 이미지 생성", key="generate_excel_and_image_main"):
                    actions_success_excel = False
                    actions_success_image = False

                    # 1. Excel 생성
                    if excel_possible:
                        latest_total_cost_excel, latest_cost_items_excel, latest_personnel_info_excel = calculations.calculate_total_moving_cost(st.session_state.to_dict())
                        with st.spinner("Excel 파일 생성 중..."):
                            filled_excel_data_dl = excel_filler.fill_final_excel_template(st.session_state.to_dict(), latest_cost_items_excel, latest_total_cost_excel, latest_personnel_info_excel)
                        if filled_excel_data_dl:
                            st.session_state['final_excel_data_for_download'] = filled_excel_data_dl
                            st.success("✅ Excel 생성 완료!")
                            actions_success_excel = True
                        else:
                            st.error("❌ Excel 파일 생성 실패.")
                            if 'final_excel_data_for_download' in st.session_state: del st.session_state['final_excel_data_for_download']
                    else:
                        st.warning("Excel을 생성할 수 없습니다. (조건 미충족)")

                    # 2. PDF 생성 및 이미지 변환
                    if pdf_possible_for_image and image_conversion_possible:
                        customer_name_img = st.session_state.get("customer_name", "고객")
                        pdf_args_img = {
                            "state_data": st.session_state.to_dict(),
                            "calculated_cost_items": st.session_state.get("calculated_cost_items_for_pdf", []),
                            "total_cost": st.session_state.get("total_cost_for_pdf", 0),
                            "personnel_info": st.session_state.get("personnel_info_for_pdf", {})
                        }
                        with st.spinner("견적서 PDF 생성 중 (이미지용)..."):
                            pdf_bytes_img = pdf_generator.generate_pdf(**pdf_args_img)

                        if pdf_bytes_img:
                            with st.spinner("PDF를 이미지로 변환 중..."):
                                image_bytes_converted = pdf_generator.generate_quote_image_from_pdf(pdf_bytes_img, poppler_path=None, image_format='JPEG') # JPEG 또는 PNG

                            if image_bytes_converted:
                                st.session_state['quote_image_data_for_download'] = image_bytes_converted
                                st.success("✅ 견적서 이미지 변환 완료!")
                                actions_success_image = True
                            else:
                                st.error("❌ 견적서 이미지 변환 실패.")
                                if 'quote_image_data_for_download' in st.session_state: del st.session_state['quote_image_data_for_download']
                        else:
                            st.error("❌ 견적서 PDF 생성 실패 (이미지용).")
                            if 'quote_image_data_for_download' in st.session_state: del st.session_state['quote_image_data_for_download']
                    elif not pdf_possible_for_image:
                         st.warning("견적서 이미지를 생성할 수 없습니다. (PDF 생성 조건 미충족)")
                    elif not image_conversion_possible:
                         st.warning("견적서 이미지를 생성할 수 없습니다. (이미지 변환 모듈 또는 라이브러리 문제)")

                    if not actions_success_excel and not actions_success_image :
                        st.error("Excel과 이미지 파일 생성 모두 실패했습니다.")
                    elif not actions_success_excel :
                        st.warning("Excel 파일 생성에 실패했습니다.")
                    elif not actions_success_image :
                         st.warning("견적서 이미지 생성에 실패했습니다.")


                # --- 다운로드 버튼 영역 ---
                # Excel 다운로드 버튼
                if st.session_state.get('final_excel_data_for_download') and excel_possible:
                    fname_excel_dl = f"최종견적서_{st.session_state.get('customer_name', '고객')}_{utils.get_current_kst_time_str('%y%m%d')}.xlsx"
                    st.download_button(
                        label="📥 다운로드 (Excel)",
                        data=st.session_state['final_excel_data_for_download'],
                        file_name=fname_excel_dl,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key='dl_btn_excel_final_section'
                    )
                elif excel_possible : st.caption("파일 생성 버튼을 눌러 Excel 파일을 준비하세요.")
                else: st.caption("Excel 생성 불가 (견적 내용 또는 모듈 확인)")


                # 이미지 다운로드 버튼
                if st.session_state.get('quote_image_data_for_download') and pdf_possible_for_image and image_conversion_possible:
                    image_format_ext = 'jpg' # generate_quote_image_from_pdf 에서 JPEG로 저장한 경우
                    # image_format_ext = 'png' # PNG로 저장한 경우
                    fname_image_dl = f"견적서이미지_{st.session_state.get('customer_name', '고객')}_{utils.get_current_kst_time_str('%y%m%d')}.{image_format_ext}"
                    st.download_button(
                        label=f"🖼️ 다운로드 (견적서 이미지 .{image_format_ext})",
                        data=st.session_state['quote_image_data_for_download'],
                        file_name=fname_image_dl,
                        mime=f"image/{image_format_ext.lower()}", # image/jpeg 또는 image/png
                        key='dl_btn_quote_image_final_section'
                    )
                elif pdf_possible_for_image and image_conversion_possible: st.caption("파일 생성 버튼을 눌러 견적서 이미지를 준비하세요.")
                else: st.caption("견적서 이미지 생성 불가 (견적 내용 또는 PDF/이미지 변환 모듈 확인)")
            # --- 수정된 섹션 끝 ---

            with cols_actions_email[0]: # Email
                st.markdown("**④ 견적서 이메일 발송 (PDF 첨부)**")
                email_possible = (hasattr(email_utils, "send_quote_email") and hasattr(pdf_generator, "generate_pdf") and can_generate_anything and st.session_state.get("customer_email"))
                if email_possible:
                    if st.button("📧 이메일 발송", key="email_send_button_main"):
                        recipient_email_send, customer_name_send = st.session_state.get("customer_email"), st.session_state.get("customer_name", "고객")
                        pdf_args_email = {"state_data": st.session_state.to_dict(), "calculated_cost_items": st.session_state.get("calculated_cost_items_for_pdf", []), "total_cost": st.session_state.get("total_cost_for_pdf", 0), "personnel_info": st.session_state.get("personnel_info_for_pdf", {})}
                        with st.spinner("이메일 발송용 PDF 생성 중..."): pdf_email_bytes_send = pdf_generator.generate_pdf(**pdf_args_email)
                        if pdf_email_bytes_send:
                            subject_send, body_send, pdf_filename_send = f"[{customer_name_send}님] 이삿날 이사 견적서입니다.", f"{customer_name_send}님,\n\n요청하신 이사 견적서를 첨부 파일로 보내드립니다.\n\n감사합니다.\n이삿날 드림", f"견적서_{customer_name_send}_{utils.get_current_kst_time_str('%Y%m%d')}.pdf"
                            with st.spinner(f"{recipient_email_send}(으)로 이메일 발송 중..."):
                                email_sent_status = email_utils.send_quote_email(recipient_email_send, subject_send, body_send, pdf_email_bytes_send, pdf_filename_send)
                            if email_sent_status: st.success(f"✅ 이메일 발송 성공!")
                            else: st.error("❌ 이메일 발송 실패.")
                        else: st.error("❌ 첨부 PDF 생성 실패 (이메일용).")
                elif not (hasattr(email_utils, "send_quote_email") and hasattr(pdf_generator, "generate_pdf")): st.caption("이메일/PDF 생성 모듈 오류")
                elif not can_generate_anything: st.caption("견적 내용 확인 필요")
                elif not st.session_state.get("customer_email"): st.caption("고객 이메일 필요")
                else: st.caption("이메일 발송 불가")

        except Exception as calc_err_outer_display:
            st.error(f"최종 견적 표시 중 외부 오류 발생: {calc_err_outer_display}")
            traceback.print_exc()
    else: # 차량 미선택 시
        st.warning("⚠️ **차량을 먼저 선택해주세요.** 비용 계산, 요약 정보 표시 및 다운로드는 차량 선택 후 가능합니다.")

# --- End of render_tab3 function ---