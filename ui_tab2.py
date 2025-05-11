# ui_tab2.py
import streamlit as st
import math

# Import necessary custom modules
try:
    import data
    import callbacks # Import the callbacks module
except ImportError as e:
    st.error(f"UI Tab 2: 필수 모듈 로딩 실패 - {e}")
    st.stop()
except Exception as e:
    st.error(f"UI Tab 2: 모듈 로딩 중 예외 발생 - {e}")
    st.stop()


def render_tab2():
    """Renders the UI for Tab 2: Item Selection."""

    st.header("📋 이사 품목 선택 ")
    st.caption(f"현재 선택된 기본 이사 유형: **{st.session_state.get("base_move_type", "N/A")}**")

    # --- Item Quantity Inputs ---
    with st.container(border=True):
        st.subheader("품목별 수량 입력")
        current_move_type = st.session_state.get("base_move_type")
        if not current_move_type:
            st.warning("이사 유형이 선택되지 않았습니다.")
            return # Stop rendering if no move type

        # Ensure callbacks.handle_item_update is available
        handle_item_update_callback = getattr(callbacks, "handle_item_update", None)
        if not callable(handle_item_update_callback):
            st.error("오류: 실시간 업데이트 콜백 함수(handle_item_update)를 찾을 수 없습니다. callbacks.py를 확인하세요.")
            # Optionally, disable on_change or stop if critical
            # return

        item_category_to_display = data.item_definitions.get(current_move_type, {})
        basket_section_name_check = "포장 자재 📦" # Used to identify the basket section

        for section, item_list in item_category_to_display.items():
            if section == "폐기 처리 품목 🗑️": continue # Skip waste section

            valid_items_in_section = [item for item in item_list if hasattr(data, "items") and data.items is not None and item in data.items]
            if not valid_items_in_section: continue

            expander_label = f"{section} 품목 선택"
            expanded_default = section == basket_section_name_check

            with st.expander(expander_label, expanded=expanded_default):
                if section == basket_section_name_check:
                    selected_truck_tab2 = st.session_state.get("final_selected_vehicle")
                    if selected_truck_tab2 and hasattr(data, "default_basket_quantities") and data.default_basket_quantities is not None and selected_truck_tab2 in data.default_basket_quantities:
                        defaults = data.default_basket_quantities[selected_truck_tab2]
                        basket_qty = defaults.get("바구니", 0)
                        med_box_qty = defaults.get("중박스", defaults.get("중자바구니", 0))
                        book_qty = defaults.get("책바구니", 0)
                        st.info(f"💡 **{selected_truck_tab2}** 추천 기본값: 바구니 {basket_qty}개, 중박스 {med_box_qty}개, 책바구니 {book_qty}개 (현재 값이며, 직접 수정 가능합니다)")
                    else:
                        st.info("💡 비용 탭에서 차량 선택 시 추천 기본 바구니 개수가 여기에 표시됩니다.")

                num_columns = 2
                cols = st.columns(num_columns)
                num_items = len(valid_items_in_section)
                items_per_col = math.ceil(num_items / len(cols)) if num_items > 0 and len(cols) > 0 else 1

                for idx, item in enumerate(valid_items_in_section):
                    col_index = idx // items_per_col if items_per_col > 0 else 0
                    if col_index < len(cols):
                        with cols[col_index]:
                            unit = "칸" if item == "장롱" else "개"
                            key_prefix = "qty"
                            widget_key = f"{key_prefix}_{current_move_type}_{section}_{item}"

                            if widget_key not in st.session_state:
                                st.session_state[widget_key] = 0
                                # print(f"Warning: Initialized missing item key in Tab 2: {widget_key}")

                            st.number_input(
                                label=f"{item}",
                                min_value=0,
                                step=1,
                                key=widget_key,
                                help=f"{item}의 수량 ({unit})",
                                on_change=handle_item_update_callback # Connect the callback
                            )

    st.write("---")

    with st.container(border=True):
        st.subheader("📊 선택 품목 및 예상 물량")
        move_selection_display = {}
        processed_items_summary_move = set()
        original_item_defs_move = data.item_definitions.get(current_move_type, {})

        if isinstance(original_item_defs_move, dict):
            for section_move, item_list_move in original_item_defs_move.items():
                if section_move == "폐기 처리 품목 🗑️": continue
                if isinstance(item_list_move, list):
                    for item_move in item_list_move:
                        if item_move in processed_items_summary_move or not (hasattr(data, "items") and data.items is not None and item_move in data.items): continue
                        widget_key_move = f"qty_{current_move_type}_{section_move}_{item_move}"
                        if widget_key_move in st.session_state:
                            qty = 0
                            try: qty = int(st.session_state.get(widget_key_move, 0))
                            except (ValueError, TypeError): qty = 0
                            if qty > 0:
                                unit_move = "칸" if item_move == "장롱" else "개"
                                move_selection_display[item_move] = (qty, unit_move)
                        processed_items_summary_move.add(item_move)

        if move_selection_display:
            st.markdown("**선택 품목 목록:**")
            cols_disp_m = st.columns(2)
            item_list_disp_m = list(move_selection_display.items())
            items_per_col_disp_m = math.ceil(len(item_list_disp_m)/len(cols_disp_m)) if len(item_list_disp_m)>0 and len(cols_disp_m)>0 else 1
            for i, (item_disp, (qty_disp, unit_disp)) in enumerate(item_list_disp_m):
                col_idx_disp = i // items_per_col_disp_m if items_per_col_disp_m > 0 else 0
                if col_idx_disp < len(cols_disp_m):
                    with cols_disp_m[col_idx_disp]:
                        st.write(f"- {item_disp}: {qty_disp} {unit_disp}")
            st.write("")
            st.markdown("**예상 물량 및 추천 차량:**")
            total_vol = st.session_state.get("total_volume", 0.0)
            total_wt = st.session_state.get("total_weight", 0.0)
            st.info(f"📊 **총 부피:** {total_vol:.2f} m³ | **총 무게:** {total_wt:.2f} kg")

            recommended_vehicle_display = st.session_state.get("recommended_vehicle_auto")
            final_vehicle_tab2_display = st.session_state.get("final_selected_vehicle")
            remaining_space = st.session_state.get("remaining_space", 0.0)

            if recommended_vehicle_display and "초과" not in recommended_vehicle_display:
                 rec_text = f"✅ 추천 차량: **{recommended_vehicle_display}** ({remaining_space:.1f}% 여유 공간 예상)"
                 if hasattr(data, "vehicle_specs") and data.vehicle_specs is not None:
                     spec = data.vehicle_specs.get(recommended_vehicle_display)
                     if spec: rec_text += f" (최대: {spec.get("capacity", "N/A")}m³, {spec.get("weight_capacity", "N/A"):,}kg)"
                 st.success(rec_text)
                 if final_vehicle_tab2_display and final_vehicle_tab2_display != recommended_vehicle_display:
                     st.warning(f"⚠️ 현재 비용계산 탭에서 **{final_vehicle_tab2_display}** 차량이 최종 선택되어 있습니다.")
                 elif not final_vehicle_tab2_display:
                      st.info("💡 비용계산 탭에서 차량을 최종 선택해주세요.")
            elif recommended_vehicle_display and "초과" in recommended_vehicle_display:
                 st.error(f"❌ 추천 차량: **{recommended_vehicle_display}**. 선택된 물량이 너무 많습니다. 물량을 줄이거나 더 큰 차량을 수동 선택해야 합니다.")
                 if final_vehicle_tab2_display:
                     st.info(f"ℹ️ 현재 비용계산 탭에서 **{final_vehicle_tab2_display}** 차량이 수동 선택되어 있습니다.")
            else:
                 if total_vol > 0 or total_wt > 0:
                     st.warning("⚠️ 추천 차량: 자동 추천 불가. 비용계산 탭에서 차량을 수동 선택해주세요.")
                 else:
                     st.info("ℹ️ 이사할 품목이 없습니다. 품목을 선택해주세요.")
                 if final_vehicle_tab2_display:
                      st.info(f"ℹ️ 현재 비용계산 탭에서 **{final_vehicle_tab2_display}** 차량이 수동 선택되어 있습니다.")
        else:
            st.info("ℹ️ 선택된 이사 품목이 없습니다. 위에서 품목을 선택해주세요.")

