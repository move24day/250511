# callbacks.py
import streamlit as st
import traceback # Added for error logging

# Import necessary custom modules
try:
    import data
    import calculations # Added for recalculations
    from state_manager import MOVE_TYPE_OPTIONS # Ensure this is how MOVE_TYPE_OPTIONS is accessed
except ImportError as ie:
    st.warning(f"콜백 모듈: 필수 모듈(data, calculations, state_manager.MOVE_TYPE_OPTIONS) 로딩 실패 - {ie}. 기능이 제한될 수 있습니다.")
    if 'MOVE_TYPE_OPTIONS' not in globals(): MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"]
    if 'calculations' not in globals():
        class DummyCalculations:
            def calculate_total_volume_weight(self, s, m): return 0.0, 0.0
            def recommend_vehicle(self, v, w, m): return None, 0.0
        calculations = DummyCalculations()
    if 'data' not in globals(): data = None
except Exception as e:
    st.error(f"Callbacks: 모듈 로딩 중 예외 발생 - {e}")
    if 'MOVE_TYPE_OPTIONS' not in globals(): MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"]
    if 'calculations' not in globals():
        class DummyCalculationsOnError:
            def calculate_total_volume_weight(self, s, m): return 0.0, 0.0
            def recommend_vehicle(self, v, w, m): return None, 0.0
        calculations = DummyCalculationsOnError()
    if 'data' not in globals(): data = None

# --- Callback Functions ---

def update_basket_quantities():
    """
    Updates final_selected_vehicle based on current recommendation or manual choice,
    then updates basket item quantities.
    This function is THE TRUTH for final_selected_vehicle and basket quantities.
    """
    # # # # print("\nDEBUG CB: --- update_basket_quantities CALLED ---")

    vehicle_choice_method = st.session_state.get('vehicle_select_radio', "자동 추천 차량 사용")
    current_move_type = st.session_state.get('base_move_type', MOVE_TYPE_OPTIONS[0] if MOVE_TYPE_OPTIONS else "가정 이사 🏠")

    available_trucks_for_type = []
    if hasattr(data, 'vehicle_prices') and data and current_move_type in data.vehicle_prices:
        available_trucks_for_type = list(data.vehicle_prices[current_move_type].keys())
    # # # # print(f"DEBUG CB: vehicle_choice_method='{vehicle_choice_method}', current_move_type='{current_move_type}', available_trucks={available_trucks_for_type}")

    _determined_vehicle = None
    if vehicle_choice_method == "자동 추천 차량 사용":
        recommended_auto = st.session_state.get('recommended_vehicle_auto')
        # # # # print(f"DEBUG CB: Auto mode. recommended_vehicle_auto='{recommended_auto}'")
        if recommended_auto and "초과" not in recommended_auto and recommended_auto in available_trucks_for_type:
            _determined_vehicle = recommended_auto
            # # # # print(f"DEBUG CB: Auto - Using recommended: '{_determined_vehicle}'")
        else:
            _determined_vehicle = None
            # # # # print(f"DEBUG CB: Auto - Recommended not valid or not in available trucks, or no items. _determined_vehicle is None.")
    else: # Manual selection
        manual_choice = st.session_state.get('manual_vehicle_select_value')
        # # # # print(f"DEBUG CB: Manual mode. manual_vehicle_select_value='{manual_choice}'")
        if manual_choice and manual_choice in available_trucks_for_type:
            _determined_vehicle = manual_choice
            # # # # print(f"DEBUG CB: Manual - Using selected: '{_determined_vehicle}'")
        else: # 수동 선택값이 유효하지 않거나, 선택 가능한 차량 목록에 없는 경우
             _determined_vehicle = None
            # # # # print(f"DEBUG CB: Manual - Choice not valid or not in available trucks. _determined_vehicle is None.")


    st.session_state.final_selected_vehicle = _determined_vehicle
    # # # # print(f"DEBUG CB: final_selected_vehicle SET TO: '{st.session_state.final_selected_vehicle}'")

    # --- Update basket quantities based on the definitive final_selected_vehicle ---
    vehicle_for_baskets = st.session_state.final_selected_vehicle # 이 값을 사용
    basket_section_name = "포장 자재 📦"

    item_defs_for_move_type = {}
    if hasattr(data, 'item_definitions') and data and current_move_type in data.item_definitions:
        item_defs_for_move_type = data.item_definitions[current_move_type]

    defined_basket_items = []
    if isinstance(item_defs_for_move_type, dict):
        defined_basket_items = item_defs_for_move_type.get(basket_section_name, [])

    if not hasattr(data, 'default_basket_quantities') or not data:
        # # # # print("ERROR CB: data.default_basket_quantities not found or data module issue.")
        for item_name in defined_basket_items:
            st.session_state[f"qty_{current_move_type}_{basket_section_name}_{item_name}"] = 0
        return

    if vehicle_for_baskets and vehicle_for_baskets in data.default_basket_quantities:
        basket_defaults = data.default_basket_quantities[vehicle_for_baskets]
        # # # # print(f"DEBUG CB: Baskets - Using defaults for '{vehicle_for_baskets}': {basket_defaults}")
        for item_name, qty in basket_defaults.items():
            if item_name in defined_basket_items:
                key = f"qty_{current_move_type}_{basket_section_name}_{item_name}"
                st.session_state[key] = qty
                # # # # print(f"DEBUG CB: Baskets - Set {key} = {qty}")
        # Zero out any defined basket items not in this vehicle's defaults
        for defined_item in defined_basket_items:
            if defined_item not in basket_defaults:
                key_to_zero = f"qty_{current_move_type}_{basket_section_name}_{defined_item}"
                st.session_state[key_to_zero] = 0
                # # # # print(f"DEBUG CB: Baskets - Zeroed {key_to_zero} (not in vehicle defaults)")
    else: # 차량이 없거나, 있어도 기본 바구니 수량 정보가 없는 경우 모든 바구니 0으로
        # # # # print(f"DEBUG CB: Baskets - No valid vehicle ('{vehicle_for_baskets}') for defaults or no defaults defined. Setting all defined baskets to 0.")
        for item_name in defined_basket_items:
            key_to_zero = f"qty_{current_move_type}_{basket_section_name}_{item_name}"
            st.session_state[key_to_zero] = 0
            # # # # print(f"DEBUG CB: Baskets - Zeroed {key_to_zero}")

    # # # # print("DEBUG CB: --- update_basket_quantities END ---\n")


def handle_item_update():
    """
    Callback for item quantity changes or move type changes.
    Recalculates totals, recommends a vehicle, then calls update_basket_quantities.
    """
    # # # # print("DEBUG CB: handle_item_update CALLED")
    try:
        current_move_type = st.session_state.get('base_move_type', MOVE_TYPE_OPTIONS[0] if MOVE_TYPE_OPTIONS else "가정 이사 🏠")
        if not current_move_type or not calculations or not data:
            #st.warning("실시간 업데이트 콜백: 필수 정보(이사 유형, 계산모듈, 데이터모듈) 부족.")
            st.session_state.update({"total_volume": 0.0, "total_weight": 0.0, "recommended_vehicle_auto": None, "remaining_space": 0.0})
            if callable(update_basket_quantities): update_basket_quantities()
            return

        vol, wt = calculations.calculate_total_volume_weight(st.session_state.to_dict(), current_move_type)
        st.session_state.total_volume = vol
        st.session_state.total_weight = wt

        rec_vehicle, rem_space = calculations.recommend_vehicle(vol, wt, current_move_type)
        st.session_state.recommended_vehicle_auto = rec_vehicle
        st.session_state.remaining_space = rem_space
        # # # # print(f"DEBUG CB (handle_item_update): Recalculated: Vol={vol}, Wt={wt}, RecVehicle='{rec_vehicle}'")
    except Exception as e:
        st.error(f"실시간 업데이트 중 계산 오류: {e}")
        traceback.print_exc() # 오류 발생 시 상세 로그
        st.session_state.update({"total_volume": 0.0, "total_weight": 0.0, "recommended_vehicle_auto": None, "remaining_space": 0.0})

    if callable(update_basket_quantities):
        update_basket_quantities()
    # # # # print("DEBUG CB: handle_item_update FINISHED")


def sync_move_type(widget_key):
    """Syncs base_move_type across tabs and triggers item update for recalculations."""
    # # # # print(f"DEBUG CB: sync_move_type CALLED with widget_key='{widget_key}'")
    if not MOVE_TYPE_OPTIONS:
        #st.error("이사 유형 옵션 누락.")
        return

    if widget_key in st.session_state:
        new_value = st.session_state[widget_key]
        if new_value not in MOVE_TYPE_OPTIONS: return

        if st.session_state.get('base_move_type') != new_value:
            st.session_state.base_move_type = new_value
            # # # # print(f"DEBUG CB (sync_move_type): base_move_type changed to '{new_value}'")
            other_key = 'base_move_type_widget_tab3' if widget_key == 'base_move_type_widget_tab1' else 'base_move_type_widget_tab1'
            if other_key in st.session_state: st.session_state[other_key] = new_value

            if callable(handle_item_update):
                # # # # print("DEBUG CB (sync_move_type): Calling handle_item_update due to move type change.")
                handle_item_update()

def update_selected_gdrive_id():
    selected_name = st.session_state.get("gdrive_selected_filename_widget")
    if selected_name and 'gdrive_file_options_map' in st.session_state:
        st.session_state.gdrive_selected_file_id = st.session_state.gdrive_file_options_map.get(selected_name)
        st.session_state.gdrive_selected_filename = selected_name