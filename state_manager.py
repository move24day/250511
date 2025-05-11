# state_manager.py
import streamlit as st
from datetime import datetime, date
import pytz
import json

# Import necessary custom modules
try:
    import data
    import utils
except ImportError as e:
    st.error(f"State Manager: 필수 모듈 로딩 실패 - {e}")
    st.stop()
except Exception as e:
    st.error(f"State Manager: 모듈 로딩 중 오류 - {e}")
    st.stop()

# --- Constants ---
try:
    MOVE_TYPE_OPTIONS = list(data.item_definitions.keys()) if hasattr(data, 'item_definitions') and data.item_definitions else ["가정 이사 🏠", "사무실 이사 🏢"]
except Exception as e:
    MOVE_TYPE_OPTIONS = ["가정 이사 🏠", "사무실 이사 🏢"]
    st.warning(f"data.py에서 이사 유형 로딩 중 오류 발생: {e}. 기본값을 사용합니다.")

STATE_KEYS_TO_SAVE = [
    "base_move_type", "is_storage_move", "storage_type", "apply_long_distance",
    "customer_name", "customer_phone", "customer_email",
    "from_location", "to_location", "moving_date", "arrival_date",
    "from_floor", "from_method", "to_floor", "to_method", "special_notes",
    "storage_duration", "storage_use_electricity",
    "long_distance_selector", "vehicle_select_radio",
    "manual_vehicle_select_value", "final_selected_vehicle", "sky_hours_from",
    "sky_hours_final",
    "add_men", "add_women",
    "has_waste_check", "waste_tons_input",
    "date_opt_0_widget", "date_opt_1_widget", "date_opt_2_widget",
    "date_opt_3_widget", "date_opt_4_widget",
    "tab3_deposit_amount",
    "tab3_adjustment_amount",
    "tab3_regional_ladder_surcharge",
    "tab3_date_opt_0_widget", "tab3_date_opt_1_widget", "tab3_date_opt_2_widget",
    "tab3_date_opt_3_widget", "tab3_date_opt_4_widget",
    "remove_base_housewife", # 기본 여성 인원 제외
    "issue_tax_invoice",   # 세금계산서 발행
    "card_payment",        # 카드 결제
    "prev_final_selected_vehicle",
    "dispatched_1t", "dispatched_2_5t", "dispatched_3_5t", "dispatched_5t",
    "has_via_point", "via_point_location", "via_point_method", "via_point_surcharge",
    "uploaded_image_paths",
]

def initialize_session_state(update_basket_callback=None):
    try: kst = pytz.timezone("Asia/Seoul"); default_date = datetime.now(kst).date()
    except Exception: default_date = datetime.now().date()

    defaults = {
        "base_move_type": MOVE_TYPE_OPTIONS[0] if MOVE_TYPE_OPTIONS else "가정 이사 🏠",
        "is_storage_move": False,
        "storage_type": data.DEFAULT_STORAGE_TYPE if hasattr(data, 'DEFAULT_STORAGE_TYPE') else "컨테이너 보관 📦",
        "apply_long_distance": False, "customer_name": "", "customer_phone": "",
        "customer_email": "",
        "from_location": "", "to_location": "", "moving_date": default_date,
        "arrival_date": default_date,
        "from_floor": "",
        "from_method": data.METHOD_OPTIONS[0] if hasattr(data, 'METHOD_OPTIONS') and data.METHOD_OPTIONS else "사다리차 🪜",
        "to_floor": "",
        "to_method": data.METHOD_OPTIONS[0] if hasattr(data, 'METHOD_OPTIONS') and data.METHOD_OPTIONS else "사다리차 🪜",
        "special_notes": "", "storage_duration": 1,
        "storage_use_electricity": False,
        "long_distance_selector": data.long_distance_options[0] if hasattr(data, 'long_distance_options') and data.long_distance_options else "선택 안 함",
        "vehicle_select_radio": "자동 추천 차량 사용",
        "manual_vehicle_select_value": None,
        "final_selected_vehicle": None,
        "recommended_vehicle_auto": None,
        "sky_hours_from": 1, "sky_hours_final": 1,
        "add_men": 0, "add_women": 0, "has_waste_check": False, "waste_tons_input": 0.5,
        "date_opt_0_widget": False, "date_opt_1_widget": False, "date_opt_2_widget": False,
        "date_opt_3_widget": False, "date_opt_4_widget": False,
        "tab3_date_opt_0_widget": False, "tab3_date_opt_1_widget": False, "tab3_date_opt_2_widget": False,
        "tab3_date_opt_3_widget": False, "tab3_date_opt_4_widget": False,
        "total_volume": 0.0, "total_weight": 0.0,
        'pdf_data_customer': None, 'final_excel_data': None,
        "deposit_amount": 0,
        "adjustment_amount": 0,
        "regional_ladder_surcharge": 0,
        "via_point_surcharge": 0,
        "tab3_deposit_amount": 0,
        "tab3_adjustment_amount": 0,
        "tab3_regional_ladder_surcharge": 0,
        "remove_base_housewife": False,
        "issue_tax_invoice": False,
        "card_payment": False,
        "prev_final_selected_vehicle": None,
        "dispatched_1t": 0, "dispatched_2_5t": 0, "dispatched_3_5t": 0, "dispatched_5t": 0,
        "gdrive_search_term": "", "gdrive_search_results": [],
        "gdrive_file_options_map": {}, "gdrive_selected_filename": None,
        "gdrive_selected_file_id": None,
        "base_move_type_widget_tab1": MOVE_TYPE_OPTIONS[0] if MOVE_TYPE_OPTIONS else "가정 이사 🏠",
        "base_move_type_widget_tab3": MOVE_TYPE_OPTIONS[0] if MOVE_TYPE_OPTIONS else "가정 이사 🏠",
        "has_via_point": False,
        "via_point_location": "",
        "via_point_method": data.METHOD_OPTIONS[0] if hasattr(data, 'METHOD_OPTIONS') and data.METHOD_OPTIONS else "사다리차 🪜",
        "uploaded_image_paths": [],
        "_app_initialized": True
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if st.session_state.base_move_type_widget_tab1 != st.session_state.base_move_type: st.session_state.base_move_type_widget_tab1 = st.session_state.base_move_type
    if st.session_state.base_move_type_widget_tab3 != st.session_state.base_move_type: st.session_state.base_move_type_widget_tab3 = st.session_state.base_move_type

    int_keys = ["storage_duration", "sky_hours_from", "sky_hours_final", "add_men", "add_women",
                "deposit_amount", "adjustment_amount", "regional_ladder_surcharge",
                "via_point_surcharge",
                "tab3_deposit_amount", "tab3_adjustment_amount", "tab3_regional_ladder_surcharge",
                "dispatched_1t", "dispatched_2_5t", "dispatched_3_5t", "dispatched_5t"]
    float_keys = ["waste_tons_input"]
    allow_negative_keys = ["adjustment_amount", "tab3_adjustment_amount"]
    bool_keys = ["is_storage_move", "apply_long_distance", "has_waste_check",
                 "remove_base_housewife", "issue_tax_invoice", "card_payment",
                 "storage_use_electricity",
                 "date_opt_0_widget", "date_opt_1_widget", "date_opt_2_widget", "date_opt_3_widget", "date_opt_4_widget",
                 "tab3_date_opt_0_widget", "tab3_date_opt_1_widget", "tab3_date_opt_2_widget",
                 "tab3_date_opt_3_widget", "tab3_date_opt_4_widget",
                 "has_via_point"]
    list_keys = ["uploaded_image_paths"]

    for k in int_keys + float_keys + bool_keys + list_keys:
        default_val_k = defaults.get(k)
        if k not in st.session_state: st.session_state[k] = default_val_k

        try:
            val = st.session_state.get(k)
            if val is None: st.session_state[k] = default_val_k; continue

            if k in bool_keys:
                 if isinstance(val, str): st.session_state[k] = val.lower() in ["true", "yes", "1", "on"]
                 else: st.session_state[k] = bool(val)
            elif k in int_keys:
                 if isinstance(val, str) and val.strip() == "": st.session_state[k] = default_val_k; continue
                 converted_val = int(val)
                 if k in allow_negative_keys: st.session_state[k] = converted_val
                 else: st.session_state[k] = max(0, converted_val)
                 if k == "storage_duration": st.session_state[k] = max(1, st.session_state[k])
            elif k in float_keys:
                 if isinstance(val, str) and val.strip() == "": st.session_state[k] = default_val_k; continue
                 converted_val = float(val)
                 st.session_state[k] = max(0.0, converted_val)
            elif k in list_keys:
                if not isinstance(val, list): st.session_state[k] = default_val_k
        except (ValueError, TypeError): st.session_state[k] = default_val_k
        except KeyError: # Should not happen if defaults are comprehensive
             if k in int_keys: st.session_state[k] = defaults.get(k, 0)
             elif k in float_keys: st.session_state[k] = defaults.get(k, 0.0)
             elif k in bool_keys: st.session_state[k] = defaults.get(k, False)
             elif k in list_keys: st.session_state[k] = defaults.get(k, [])

    # Ensure all item quantity keys are initialized
    global STATE_KEYS_TO_SAVE # Make sure we are using the global one
    processed_init_keys = set()
    item_keys_to_save = [] # This will hold dynamically generated item keys
    if hasattr(data, "item_definitions") and data.item_definitions:
        for move_type, sections in data.item_definitions.items():
            if isinstance(sections, dict):
                for section, item_list in sections.items():
                    if section == "폐기 처리 품목 🗑️": continue # Skip waste items
                    if isinstance(item_list, list):
                        for item in item_list:
                            if hasattr(data, "items") and item in data.items: # Check if item is valid
                                key = f"qty_{move_type}_{section}_{item}"
                                item_keys_to_save.append(key)
                                if key not in st.session_state and key not in processed_init_keys:
                                    st.session_state[key] = 0 # Default to 0
                                processed_init_keys.add(key)
    # Add dynamically generated item keys to STATE_KEYS_TO_SAVE if they are not already there
    # This step ensures that when saving state, these dynamic keys are included.
    for item_key in item_keys_to_save:
        if item_key not in STATE_KEYS_TO_SAVE:
            STATE_KEYS_TO_SAVE.append(item_key)


    if "prev_final_selected_vehicle" not in st.session_state: st.session_state["prev_final_selected_vehicle"] = st.session_state.get("final_selected_vehicle")

    if callable(update_basket_callback):
        update_basket_callback()


def prepare_state_for_save():
    state_to_save = {}
    keys_to_exclude = {
        "_app_initialized", "base_move_type_widget_tab1", "base_move_type_widget_tab3",
        "gdrive_selected_filename_widget", "pdf_data_customer", "final_excel_data",
        "gdrive_search_results", "gdrive_file_options_map",
        # UI-specific input fields that are mapped to tab3_ counterparts for saving
        "deposit_amount", "adjustment_amount", "regional_ladder_surcharge",
        # via_point_surcharge is directly saved via STATE_KEYS_TO_SAVE
        "date_opt_0_widget", "date_opt_1_widget", "date_opt_2_widget",
        "date_opt_3_widget", "date_opt_4_widget",
    }
    # Ensure mapping from UI keys to saveable keys
    st.session_state.tab3_deposit_amount = st.session_state.get("deposit_amount", 0)
    st.session_state.tab3_adjustment_amount = st.session_state.get("adjustment_amount", 0)
    st.session_state.tab3_regional_ladder_surcharge = st.session_state.get("regional_ladder_surcharge", 0)
    for i in range(5):
        st.session_state[f"tab3_date_opt_{i}_widget"] = st.session_state.get(f"date_opt_{i}_widget", False)

    # Use the global STATE_KEYS_TO_SAVE which now includes dynamic item keys
    actual_keys_to_save = [key for key in STATE_KEYS_TO_SAVE if key not in keys_to_exclude]

    for key in actual_keys_to_save:
        if key in st.session_state:
            value = st.session_state[key]
            if isinstance(value, date):
                try: state_to_save[key] = value.isoformat()
                except Exception: print(f"Warning: Could not serialize date key '{key}' for saving.")
            elif isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                 state_to_save[key] = value
            else: # Attempt to convert other types to string, log if problematic
                 try: state_to_save[key] = str(value)
                 except Exception: print(f"Warning: Skipping non-serializable key '{key}' of type {type(value)} during save.")
    # Ensure uploaded_image_paths is always a list, even if empty
    if "uploaded_image_paths" not in state_to_save or not isinstance(state_to_save.get("uploaded_image_paths"), list):
        state_to_save["uploaded_image_paths"] = st.session_state.get("uploaded_image_paths", [])
    return state_to_save

def load_state_from_data(loaded_data, update_basket_callback):
    if not isinstance(loaded_data, dict):
        st.error("잘못된 형식의 파일입니다 (딕셔셔리가 아님).")
        return False

    try: kst = pytz.timezone("Asia/Seoul"); default_date = datetime.now(kst).date()
    except Exception: default_date = datetime.now().date()
    current_move_type_options = globals().get("MOVE_TYPE_OPTIONS")
    
    # Re-initialize defaults here to ensure all keys are covered, especially dynamic ones
    # This defaults_for_recovery should mirror the structure in initialize_session_state
    defaults_for_recovery = {
        "base_move_type": current_move_type_options[0] if current_move_type_options else "가정 이사 🏠",
        "is_storage_move": False, "storage_type": data.DEFAULT_STORAGE_TYPE if hasattr(data, "DEFAULT_STORAGE_TYPE") else "컨테이너 보관 📦",
        "apply_long_distance": False, "customer_name": "", "customer_phone": "", "customer_email": "",
        "from_location": "", "to_location": "", "moving_date": default_date, "arrival_date": default_date,
        "from_floor": "", "from_method": data.METHOD_OPTIONS[0] if hasattr(data, "METHOD_OPTIONS") else "사다리차 🪜",
        "to_floor": "", "to_method": data.METHOD_OPTIONS[0] if hasattr(data, "METHOD_OPTIONS") else "사다리차 🪜",
        "special_notes": "", "storage_duration": 1, "storage_use_electricity": False,
        "long_distance_selector": data.long_distance_options[0] if hasattr(data, "long_distance_options") else "선택 안 함",
        "vehicle_select_radio": "자동 추천 차량 사용", "manual_vehicle_select_value": None,
        "final_selected_vehicle": None, "prev_final_selected_vehicle": None,
        "sky_hours_from": 1, "sky_hours_final": 1, "add_men": 0, "add_women": 0,
        "has_waste_check": False, "waste_tons_input": 0.5,
        "tab3_date_opt_0_widget": False, "tab3_date_opt_1_widget": False, "tab3_date_opt_2_widget": False,
        "tab3_date_opt_3_widget": False, "tab3_date_opt_4_widget": False,
        "tab3_deposit_amount": 0, "tab3_adjustment_amount": 0, "tab3_regional_ladder_surcharge": 0,
        "remove_base_housewife": False, "issue_tax_invoice": False, "card_payment": False,
        "dispatched_1t": 0, "dispatched_2_5t": 0, "dispatched_3_5t": 0, "dispatched_5t": 0,
        "has_via_point": False, "via_point_location": "",
        "via_point_method": data.METHOD_OPTIONS[0] if hasattr(data, "METHOD_OPTIONS") else "사다리차 🪜",
        "via_point_surcharge": 0, "uploaded_image_paths": [],
    }
    # Add dynamic item keys to defaults_for_recovery
    if hasattr(data, "item_definitions") and data.item_definitions:
        for move_type, sections in data.item_definitions.items():
            if isinstance(sections, dict):
                for section, item_list in sections.items():
                    if section == "폐기 처리 품목 🗑️": continue
                    if isinstance(item_list, list):
                        for item in item_list:
                            if hasattr(data, "items") and item in data.items:
                                key = f"qty_{move_type}_{section}_{item}"
                                if key not in defaults_for_recovery: defaults_for_recovery[key] = 0
    
    # Define type groups again for loading
    int_keys_load = [k for k,v in defaults_for_recovery.items() if isinstance(v, int) and not isinstance(v, bool)] # Exclude bools which are ints
    float_keys_load = [k for k,v in defaults_for_recovery.items() if isinstance(v, float)]
    bool_keys_load = [k for k,v in defaults_for_recovery.items() if isinstance(v, bool)]
    list_keys_load = [k for k,v in defaults_for_recovery.items() if isinstance(v, list)]
    allow_negative_keys_load = ["tab3_adjustment_amount"] # Assuming this is the only one that can be negative int

    # Iterate over all keys expected (from defaults_for_recovery as it's more comprehensive now)
    for key in defaults_for_recovery.keys():
        if key in loaded_data:
            value = loaded_data[key]
            try:
                target_value = None
                if key in ["moving_date", "arrival_date"]:
                    if isinstance(value, str): target_value = datetime.fromisoformat(value).date()
                    elif isinstance(value, date): target_value = value
                    else: target_value = defaults_for_recovery.get(key, default_date)
                elif key in int_keys_load: # Covers qty_ keys as well
                    if isinstance(value, str) and value.strip() == "": target_value = defaults_for_recovery.get(key, 0)
                    else: target_value = int(value)
                    if key not in allow_negative_keys_load: target_value = max(0, target_value)
                    if key == "storage_duration": target_value = max(1, target_value)
                elif key in float_keys_load:
                    if isinstance(value, str) and value.strip() == "": target_value = defaults_for_recovery.get(key, 0.0)
                    else: target_value = float(value)
                    target_value = max(0.0, target_value)
                elif key in bool_keys_load:
                    if isinstance(value, str): target_value = value.lower() in ["true", "yes", "1", "on"]
                    else: target_value = bool(value)
                elif key in list_keys_load: 
                    target_value = value if isinstance(value, list) else defaults_for_recovery.get(key, [])
                else: # For other types like string, directly assign or use default
                    target_value = value if value is not None else defaults_for_recovery.get(key, "")
                st.session_state[key] = target_value
            except (ValueError, TypeError):
                st.session_state[key] = defaults_for_recovery.get(key) # Fallback to default on error
        else: # Key not in loaded_data, set to default
            st.session_state[key] = defaults_for_recovery.get(key)

    # Sync UI-specific keys from loaded 'tab3_' counterparts
    st.session_state.deposit_amount = st.session_state.get("tab3_deposit_amount", 0)
    st.session_state.adjustment_amount = st.session_state.get("tab3_adjustment_amount", 0)
    st.session_state.regional_ladder_surcharge = st.session_state.get("tab3_regional_ladder_surcharge", 0)
    for i in range(5):
        st.session_state[f"date_opt_{i}_widget"] = st.session_state.get(f"tab3_date_opt_{i}_widget", False)

    # Sync base_move_type with tab-specific widgets
    if "base_move_type" in st.session_state:
        st.session_state.base_move_type_widget_tab1 = st.session_state.base_move_type
        st.session_state.base_move_type_widget_tab3 = st.session_state.base_move_type

    # Ensure uploaded_image_paths is correctly initialized as a list
    if "uploaded_image_paths" not in st.session_state or not isinstance(st.session_state.uploaded_image_paths, list):
        st.session_state.uploaded_image_paths = []

    if callable(update_basket_callback):
        update_basket_callback()
    return True