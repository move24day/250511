# text_to_json_gdrive.py
import streamlit as st
import json
import re
from datetime import datetime, date
import pytz # 시간대 처리

# 필요한 프로젝트 모듈 임포트
try:
    import google_drive_helper as gdrive # 또는 gdrive_utils (프로젝트에 있는 파일명으로 변경)
    import data # 기본 이사 유형 등을 가져오기 위함
    from state_manager import STATE_KEYS_TO_SAVE, MOVE_TYPE_OPTIONS # 기본 상태 키 참조
except ImportError as e:
    st.error(f"필수 모듈 로딩 실패: {e}. (google_drive_helper.py, data.py, state_manager.py 확인)")
    st.stop()

# KST 시간대 설정
try:
    KST = pytz.timezone("Asia/Seoul")
except pytz.UnknownTimeZoneError:
    st.warning("Asia/Seoul 시간대를 찾을 수 없어 UTC를 사용합니다. 날짜 처리에 영향이 있을 수 있습니다.")
    KST = pytz.utc

# 기본값 설정
DEFAULT_CUSTOMER_NAME = "무명"
DEFAULT_MOVE_TYPE = MOVE_TYPE_OPTIONS[0] if MOVE_TYPE_OPTIONS else "가정 이사 🏠"
DEFAULT_FROM_METHOD = data.METHOD_OPTIONS[0] if hasattr(data, 'METHOD_OPTIONS') and data.METHOD_OPTIONS else "사다리차 🪜"
DEFAULT_TO_METHOD = data.METHOD_OPTIONS[0] if hasattr(data, 'METHOD_OPTIONS') and data.METHOD_OPTIONS else "사다리차 🪜"


def parse_date(date_str_input, current_year):
    """ 'MM월 DD일' 또는 'MM/DD' 형식의 날짜 문자열을 'YYYY-MM-DD'로 변환 """
    date_str_input = date_str_input.strip()
    if not date_str_input or date_str_input.lower() == "미정":
        return datetime.now(KST).date().isoformat()

    # "MM월 DD일" 형식 먼저 시도
    match_md = re.match(r'(\d{1,2})\s*월\s*(\d{1,2})\s*일?', date_str_input)
    if match_md:
        month, day = int(match_md.group(1)), int(match_md.group(2))
        try:
            return datetime(current_year, month, day).date().isoformat()
        except ValueError: # 잘못된 날짜 (예: 2월 30일)
            st.warning(f"'{date_str_input}'은 유효하지 않은 날짜입니다. 오늘 날짜로 대체합니다.")
            return datetime.now(KST).date().isoformat()

    # "MM/DD" 또는 "MM.DD" 형식 시도
    match_slash_dot = re.match(r'(\d{1,2})[/\.](\d{1,2})', date_str_input)
    if match_slash_dot:
        month, day = int(match_slash_dot.group(1)), int(match_slash_dot.group(2))
        try:
            return datetime(current_year, month, day).date().isoformat()
        except ValueError:
            st.warning(f"'{date_str_input}'은 유효하지 않은 날짜입니다. 오늘 날짜로 대체합니다.")
            return datetime.now(KST).date().isoformat()
    
    # "YYYY-MM-DD" 또는 "YY-MM-DD" 형식 그대로 사용 시도
    try:
        dt_obj = datetime.strptime(date_str_input, "%Y-%m-%d")
        return dt_obj.date().isoformat()
    except ValueError:
        try: # YY-MM-DD 처리 (2000년대로 가정)
            dt_obj = datetime.strptime(date_str_input, "%y-%m-%d")
            return dt_obj.date().isoformat()
        except ValueError:
            st.warning(f"날짜 형식 '{date_str_input}'을 인식할 수 없습니다. 오늘 날짜로 대체합니다.")
            return datetime.now(KST).date().isoformat()


def normalize_phone_number_for_filename(phone_str):
    """ 파일명으로 사용하기 위해 전화번호에서 숫자만 추출 """
    if not phone_str or not isinstance(phone_str, str):
        return None
    return "".join(filter(str.isdigit, phone_str))


def parse_line_to_json(line_text, current_year):
    """
    한 줄의 텍스트를 파싱하여 JSON 객체(딕셔너리)로 변환합니다.
    파싱 순서: 날짜, 이름, 전화번호, 이사종류(가/사), 출발지, 도착지, [선택사항: 특이사항]
    """
    parts = [p.strip() for p in line_text.split('\t') if p.strip()] # 탭으로 구분, 빈 항목 제거
    if not parts or len(parts) < 3: # 최소 날짜, 이름, 전화번호는 있어야 함 (나머지는 기본값 처리 가능)
        st.error(f"처리할 수 없는 라인 형식입니다: '{line_text}' (탭으로 구분된 항목 부족)")
        return None, None

    # 기본 상태 객체 생성 (state_manager.py의 기본값 참조)
    state = {
        "moving_date": datetime.now(KST).date().isoformat(),
        "customer_name": DEFAULT_CUSTOMER_NAME,
        "customer_phone": "",
        "base_move_type": DEFAULT_MOVE_TYPE,
        "from_location": "",
        "to_location": "",
        "special_notes": "",
        "is_storage_move": False,
        "apply_long_distance": False,
        "has_via_point": False,
        "from_floor": "", "to_floor": "",
        "from_method": DEFAULT_FROM_METHOD, "to_method": DEFAULT_TO_METHOD,
        "deposit_amount": 0, "adjustment_amount": 0,
        # 기타 STATE_KEYS_TO_SAVE에 있는 boolean/숫자 기본값들
        "issue_tax_invoice": False, "card_payment": False,
        "remove_base_housewife": False,
        "dispatched_1t":0, "dispatched_2_5t":0, "dispatched_3_5t":0, "dispatched_5t":0,
        "uploaded_image_paths": []
    }
    # data.py의 item_definitions를 기반으로 모든 품목 수량(qty_...)을 0으로 초기화할 수도 있음
    # (현재 앱의 load_state_from_data 가 없는 키는 기본값으로 처리하므로 필수 아님)

    # 1. 이사 날짜
    state["moving_date"] = parse_date(parts[0], current_year)

    # 2. 고객명
    if len(parts) > 1 and parts[1] and parts[1].lower() != "미정":
        state["customer_name"] = parts[1]
    else:
        state["customer_name"] = DEFAULT_CUSTOMER_NAME
        if len(parts) <=1 or not parts[1]: # 이름 항목이 아예 없거나 비어있는 경우
             st.warning(f"'{line_text}'에서 고객명이 누락되어 '{DEFAULT_CUSTOMER_NAME}'으로 설정합니다.")


    # 3. 전화번호 (필수)
    if len(parts) > 2 and parts[2]:
        state["customer_phone"] = parts[2]
        filename_phone = normalize_phone_number_for_filename(parts[2])
        if not filename_phone:
            st.error(f"'{line_text}'에서 유효한 전화번호를 찾을 수 없어 파일명을 생성할 수 없습니다.")
            return None, None
    else:
        st.error(f"'{line_text}'에서 전화번호를 찾을 수 없습니다. 이 항목은 필수입니다.")
        return None, None

    # 4. 이사 종류 (가/사)
    if len(parts) > 3 and parts[3]:
        move_type_char = parts[3].lower()
        if move_type_char == '가':
            state["base_move_type"] = MOVE_TYPE_OPTIONS[0] if "가정" in MOVE_TYPE_OPTIONS[0] else DEFAULT_MOVE_TYPE
        elif move_type_char == '사':
            state["base_move_type"] = MOVE_TYPE_OPTIONS[1] if len(MOVE_TYPE_OPTIONS) > 1 and "사무실" in MOVE_TYPE_OPTIONS[1] else DEFAULT_MOVE_TYPE
        else: # 인식할 수 없는 코드면 기본값 사용하고 경고
            st.warning(f"'{line_text}'의 이사 종류 코드 '{parts[3]}'를 인식할 수 없어 '{DEFAULT_MOVE_TYPE}'으로 설정합니다.")
            state["base_move_type"] = DEFAULT_MOVE_TYPE
    else: # 이사 종류 누락 시 기본값
        state["base_move_type"] = DEFAULT_MOVE_TYPE

    # 5. 출발지 주소
    if len(parts) > 4 and parts[4]:
        state["from_location"] = parts[4]
        # 출발지 층수 파싱 (주소 뒤에 "X층" 또는 "XF" 같은 패턴이 있다면)
        floor_match = re.search(r'(\d+)\s*(층|F|f)$', parts[4])
        if floor_match:
            state["from_floor"] = floor_match.group(1)
            # 주소에서 층수 정보 제거 (선택적)
            # state["from_location"] = state["from_location"].replace(floor_match.group(0), "").strip()

    # 6. 도착지 주소
    if len(parts) > 5 and parts[5]:
        state["to_location"] = parts[5]
        floor_match_to = re.search(r'(\d+)\s*(층|F|f)$', parts[5])
        if floor_match_to:
            state["to_floor"] = floor_match_to.group(1)

    # 7. (선택) 특이사항 또는 추가 텍스트 (마지막 부분)
    # 예시에서는 "금 11시-1시까지" 같은 부분이 있었음. 이를 special_notes에 추가.
    if len(parts) > 6 and parts[6]:
        state["special_notes"] = parts[6]

    # STATE_KEYS_TO_SAVE에 정의된 키들만 최종 결과에 포함 (선택적, 현재는 모든 state 반환)
    # final_state = {k: v for k, v in state.items() if k in STATE_KEYS_TO_SAVE or k.startswith("qty_")}

    return state, filename_phone + ".json"


# --- Streamlit UI ---
st.title("텍스트 기반 이사 정보 JSON 변환 및 Google Drive 저장")
st.write("한 줄에 하나의 이사 정보를 다음 순서대로 탭(tab)으로 구분하여 입력해주세요:")
st.markdown("`이사날짜` `고객명` `전화번호` `이사종류(가/사)` `출발지주소 [층수]` `도착지주소 [층수]` `[특이사항]`")
st.markdown("""
- **이사날짜**: "MM월 DD일", "MM/DD", "YYYY-MM-DD" 등. "미정" 또는 누락 시 오늘 날짜.
- **고객명**: 누락 또는 "미정" 시 "무명".
- **전화번호**: 필수. 파일명으로 사용됩니다.
- **이사종류**: "가" 또는 "사". 누락 시 "가정 이사".
- **주소**: 층수는 주소 끝에 "2층", "3F" 등으로 포함 가능 (자동으로 'from_floor', 'to_floor'로 일부 파싱 시도).
- **특이사항**: 선택 사항. 라인의 마지막 부분.
""")

text_input = st.text_area("여기에 이사 정보를 한 줄씩 입력하세요:", height=200,
                          placeholder="예시: 05월 30일\t프란치스코\t010-9255-7232\t가\t동대문구 답십리로 173-4 2층\t동대문구 답십리동\t금 11시-1시까지")

if st.button("JSON 변환 및 Google Drive에 저장"):
    if not text_input:
        st.warning("입력된 셋스트가 없습니다.")
    else:
        lines = text_input.strip().split('\n')
        current_year = datetime.now(KST).year
        success_count = 0
        error_count = 0
        results_log = []

        st.subheader("처리 결과:")
        progress_bar = st.progress(0)

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            status, filename = parse_line_to_json(line, current_year)
            progress_bar.progress((i + 1) / len(lines))

            if status and filename:
                try:
                    # 기존 파일 확인 (선택적: 덮어쓰기 전 사용자 확인)
                    # existing_file_id = gdrive.find_file_id_by_exact_name(filename) # google_drive_helper 사용 시
                    # if existing_file_id:
                    #     st.write(f"'{filename}'이 이미 존재합니다. 덮어씁니다.")

                    json_string = json.dumps(status, indent=2, ensure_ascii=False)
                    save_result = gdrive.save_json_file(filename, status) # google_drive_helper 사용 시

                    if save_result and save_result.get('id'):
                        log_message = f"✅ 성공: '{line[:30]}...' -> Google Drive에 '{filename}'으로 저장/업데이트 완료 (ID: {save_result.get('id')})"
                        st.success(log_message)
                        results_log.append(log_message)
                        success_count += 1
                    else:
                        log_message = f"❌ 실패: '{line[:30]}...' -> Google Drive 저장 실패 (save_json_file 결과 확인)"
                        st.error(log_message)
                        results_log.append(log_message)
                        error_count += 1
                except Exception as e:
                    log_message = f"❌ 오류: '{line[:30]}...' 처리 중 예외 발생 - {str(e)}"
                    st.error(log_message)
                    results_log.append(log_message)
                    error_count += 1
                    # traceback.print_exc() # 디버깅 시
            else: # status 또는 filename이 None일 경우 (파싱 실패)
                log_message = f"⚠️ 건너뜀: '{line[:30]}...' -> 파싱 실패 또는 필수 정보 누락"
                st.warning(log_message)
                results_log.append(log_message)
                error_count +=1


        st.subheader("최종 요약")
        st.info(f"총 {len(lines)} 줄 처리 시도.")
        st.info(f"성공: {success_count} 건")
        st.info(f"실패/건너뜀: {error_count} 건")

        if results_log:
            with st.expander("전체 처리 로그 보기"):
                for log_entry in results_log:
                    if "성공" in log_entry:
                        st.write(f"<span style='color:green'>{log_entry}</span>", unsafe_allow_html=True)
                    elif "실패" in log_entry or "오류" in log_entry :
                        st.write(f"<span style='color:red'>{log_entry}</span>", unsafe_allow_html=True)
                    else:
                        st.write(f"<span style='color:orange'>{log_entry}</span>", unsafe_allow_html=True)