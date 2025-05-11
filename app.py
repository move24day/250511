# app.py (Main execution file)

# 1. Import streamlit first
import streamlit as st

# 2. Set page config early
st.set_page_config(page_title="이삿날 포장이사 견적서", layout="wide", page_icon="🚚")

# 3. Import standard libraries
import pandas as pd
from datetime import datetime, date
import pytz
import math
import traceback # For error logging
import io

# 4. Import custom utility and data modules
try:
    import data
    import utils
    import calculations
    import google_drive_helper as gdrive # google_drive_helper 사용 (gdrive_utils 대신)
    import pdf_generator
    import excel_filler
    # excel_summary_generator는 pdf_generator 또는 ui_tab3에서 직접 호출될 수 있으므로 여기서는 제외 가능
except ImportError as ie:
    st.error(f"메인 앱: 필수 유틸리티 모듈 로딩 실패 - {ie}.")
    st.stop()
except Exception as e:
    st.error(f"메인 앱: 유틸리티 모듈 로딩 중 오류 발생 - {e}")
    traceback.print_exc()
    st.stop()


# 5. Import the NEWLY CREATED modules
try:
    import state_manager
    import callbacks # callbacks must be imported before being passed
    import ui_tab1
    import ui_tab2
    import ui_tab3
    import mms_utils # ui_tab3에서 사용
    import email_utils # ui_tab3에서 사용
except ImportError as ie:
    st.error(f"메인 앱: 필수 UI/상태 모듈 로딩 실패 - {ie}.")
    # 실패한 모듈 이름 출력 (디버깅에 도움)
    if hasattr(e, 'name') and e.name:
        st.error(f"실패한 모듈: {e.name}")
    st.stop()
except Exception as e:
    st.error(f"메인 앱: UI/상태 모듈 로딩 중 예외 발생 - {e}")
    traceback.print_exc()
    st.stop()


# --- Main Application ---

st.markdown("<h1 style='text-align: center; color: #1E90FF;'>🚚 이삿날 스마트 견적 🚚</h1>", unsafe_allow_html=True)
st.write("")

# Initialize session state.
# Pass the callback function for initial basket quantity setup.
# Ensure this runs only once per session to avoid re-initializing over reruns.
if not st.session_state.get("_app_initialized", False):
    # # # print("DEBUG APP: Initializing session state for the first time.")
    # state_manager.initialize_session_state 호출 시 update_basket_quantities 콜백 전달
    if hasattr(callbacks, 'update_basket_quantities') and callable(callbacks.update_basket_quantities):
        state_manager.initialize_session_state(update_basket_callback=callbacks.update_basket_quantities)
    else:
        st.error("초기화 오류: callbacks.update_basket_quantities 함수를 찾을 수 없습니다.")
        state_manager.initialize_session_state() # 콜백 없이 초기화
    st.session_state._app_initialized = True
# # else:
    # # # print("DEBUG APP: Session state already initialized or app rerun.")


# All calculations and state updates (total volume, weight, recommended vehicle,
# final selected vehicle, basket quantities) are now handled by callbacks
# triggered by widget interactions (on_change events in ui_tab1, ui_tab2, ui_tab3).
# The app will simply re-render with the latest state after a callback execution.

# --- Define and Render Tabs ---
# Tabs will render using the most current session state, which is updated by callbacks.
tab1_title = "👤 고객 정보"
tab2_title = "📋 물품 선택"
tab3_title = "💰 견적 및 비용"

tab1, tab2, tab3 = st.tabs([tab1_title, tab2_title, tab3_title])

with tab1:
    if hasattr(ui_tab1, 'render_tab1') and callable(ui_tab1.render_tab1):
        ui_tab1.render_tab1()
    else:
        st.error("Tab 1 UI를 로드할 수 없습니다.")

with tab2:
    if hasattr(ui_tab2, 'render_tab2') and callable(ui_tab2.render_tab2):
        ui_tab2.render_tab2()
    else:
        st.error("Tab 2 UI를 로드할 수 없습니다.")

with tab3:
    if hasattr(ui_tab3, 'render_tab3') and callable(ui_tab3.render_tab3):
        ui_tab3.render_tab3()
    else:
        st.error("Tab 3 UI를 로드할 수 없습니다.")

# Optional: Footer or other elements outside tabs can go here