# text_to_json_gdrive.py (유연한 파싱 및 필수 필드 검증 강화)
import streamlit as st
import json
import re
from datetime import datetime, date
import pytz

try:
    import google_drive_helper as gdrive
    import data
    from state_manager import STATE_KEYS_TO_SAVE, MOVE_TYPE_OPTIONS
except ImportError as e:
    st.error(f"필수 모듈 로딩 실패: {e}. (google_drive_helper.py, data.py, state_manager.py 확인)")
    st.stop()

try:
    KST = pytz.timezone("Asia/Seoul")
except pytz.UnknownTimeZoneError:
    st.warning("Asia/Seoul 시간대를 찾을 수 없어 UTC를 사용합니다. 날짜 처리에 영향이 있을 수 있습니다.")
    KST = pytz.utc

DEFAULT_CUSTOMER_NAME = "무명"
DEFAULT_MOVE_TYPE = MOVE_TYPE_OPTIONS[0] if MOVE_TYPE_OPTIONS else "가정 이사 🏠"
DEFAULT_FROM_METHOD = data.METHOD_OPTIONS[0] if hasattr(data, 'METHOD_OPTIONS') and data.METHOD_OPTIONS else "사다리차 🪜"
DEFAULT_TO_METHOD = data.METHOD_OPTIONS[0] if hasattr(data, 'METHOD_OPTIONS') and data.METHOD_OPTIONS else "사다리차 🪜"
# 오늘 날짜를 YYYY-MM-DD 형식으로 미리 정의
TODAY_ISO_DATE = datetime.now(KST).date().isoformat()

def parse_date_flexible(date_str_input, current_year):
    """ 'MM월 DD일', 'MM/DD', 'YYYY-MM-DD' 등의 날짜 문자열을 'YYYY-MM-DD'로 변환, 실패 시 오늘 날짜 """
    if not date_str_input or str(date_str_input).strip().lower() == "미정":
        return TODAY_ISO_DATE

    date_str = str(date_str_input).strip()

    patterns = [
        (r'(\d{1,2})\s*월\s*(\d{1,2})\s*일?', lambda m: (current_year, int(m.group(1)), int(m.group(2)))), # MM월 DD일
        (r'(\d{1,2})/(\d{1,2})', lambda m: (current_year, int(m.group(1)), int(m.group(2)))),             # MM/DD
        (r'(\d{1,2})\.(\d{1,2})', lambda m: (current_year, int(m.group(1)), int(m.group(2)))),            # MM.DD
        (r'(\d{4})-(\d{1,2})-(\d{1,2})', lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)))), # YYYY-MM-DD
        (r'(\d{2})-(\d{1,2})-(\d{1,2})', lambda m: (2000 + int(m.group(1)), int(m.group(2)), int(m.group(3)))) # YY-MM-DD
    ]

    for pattern, extractor in patterns:
        match = re.fullmatch(pattern, date_str) # fullmatch로 정확히 일치하는 경우만
        if match:
            try:
                year, month, day = extractor(match)
                return datetime(year, month, day).date().isoformat()
            except ValueError:
                st.warning(f"'{date_str}'은(는) 유효한 날짜가 아닙니다 (패턴: {pattern}). 오늘 날짜로 대체합니다.")
                return TODAY_ISO_DATE
    
    st.warning(f"날짜 형식 '{date_str}'을(를) 인식할 수 없습니다. 오늘 날짜로 대체합니다.")
    return TODAY_ISO_DATE

def normalize_phone_number_for_filename(phone_str):
    if not phone_str or not isinstance(phone_str, str):
        return None
    return "".join(filter(str.isdigit, phone_str))

def parse_line_to_json_flexible(line_text, current_year):
    """
    한 줄의 텍스트를 유연하게 파싱하여 JSON 객체(딕셔너리)로 변환합니다.
    순서: 날짜, 이름, 전화번호, 이사종류(가/사), 출발지, 도착지, [특이사항]
    전화번호와 출발지는 필수입니다.
    """
    parts = [p.strip() for p in line_text.split('\t')] # 탭으로 구분, 빈 항목은 유지하여 인덱스 보존

    # 필수 항목 검사를 위한 초기 변수 설정
    customer_phone_raw = None
    from_location_raw = None
    
    # 기본 상태 객체 (자주 사용되는 키 위주로 초기화)
    state = {
        "moving_date": TODAY_ISO_DATE,
        "customer_name": DEFAULT_CUSTOMER_NAME,
        "customer_phone": "",
        "base_move_type": DEFAULT_MOVE_TYPE,
        "from_location": "",
        "to_location": "",
        "special_notes": "",
        "from_floor": "", "to_floor": "",
        "from_method": DEFAULT_FROM_METHOD, "to_method": DEFAULT_TO_METHOD,
        "is_storage_move": False, "apply_long_distance": False, "has_via_point": False,
        "deposit_amount": 0, "adjustment_amount": 0,
        "issue_tax_invoice": False, "card_payment": False,
        "remove_base_housewife": False,
        "dispatched_1t":0, "dispatched_2_5t":0, "dispatched_3_5t":0, "dispatched_5t":0,
        "uploaded_image_paths": []
    }
    # 전체 STATE_KEYS_TO_SAVE 에 있는 boolean/숫자형 기본값들도 필요시 state_manager 참조하여 추가 가능

    # 각 필드 파싱 시도
    # 0: 이사 날짜 (선택)
    if len(parts) > 0 and parts[0]:
        state["moving_date"] = parse_date_flexible(parts[0], current_year)
    
    # 1: 고객명 (선택)
    if len(parts) > 1 and parts[1] and parts[1].lower() != "미정":
        state["customer_name"] = parts[1]
    
    # 2: 전화번호 (필수)
    if len(parts) > 2 and parts[2]:
        customer_phone_raw = parts[2]
        state["customer_phone"] = customer_phone_raw
    else:
        st.error(f"처리 오류: '{line_text[:50]}...' -> 전화번호가 누락되었습니다 (필수 항목).")
        return None, None
        
    filename_phone_part = normalize_phone_number_for_filename(customer_phone_raw)
    if not filename_phone_part: # 숫자 없는 전화번호 방지
        st.error(f"처리 오류: '{line_text[:50]}...' -> 전화번호에서 유효한 숫자를 추출할 수 없습니다.")
        return None, None

    # 3: 이사 종류 (선택)
    if len(parts) > 3 and parts[3]:
        move_type_char = parts[3].strip().lower()
        if move_type_char == '가':
            state["base_move_type"] = MOVE_TYPE_OPTIONS[0] if "가정" in MOVE_TYPE_OPTIONS[0] else DEFAULT_MOVE_TYPE
        elif move_type_char == '사':
            state["base_move_type"] = MOVE_TYPE_OPTIONS[1] if len(MOVE_TYPE_OPTIONS) > 1 and "사무실" in MOVE_TYPE_OPTIONS[1] else DEFAULT_MOVE_TYPE
        # '가' 또는 '사'가 아니면 기본값 유지 (경고 없음)
    
    # 4: 출발지 주소 (필수)
    if len(parts) > 4 and parts[4]:
        from_location_raw = parts[4]
        state["from_location"] = from_location_raw
        floor_match_from = re.search(r'(\S+)\s*(\d+)\s*(층|F|f)$', from_location_raw) # 주소와 층 분리 시도 (더 간단한 패턴)
        if floor_match_from:
             # state["from_location"] = floor_match_from.group(1).strip() # 층 제외한 주소
             state["from_floor"] = floor_match_from.group(2)
        else: # 층 정보가 명시적이지 않으면 주소 전체를 사용
             simple_floor_match = re.search(r'(\d+)\s*(층|F|f)$', from_location_raw)
             if simple_floor_match:
                 state["from_floor"] = simple_floor_match.group(1)
    else:
        st.error(f"처리 오류: '{line_text[:50]}...' -> 출발지 주소가 누락되었습니다 (필수 항목).")
        return None, None

    # 5: 도착지 주소 (선택)
    if len(parts) > 5 and parts[5]:
        state["to_location"] = parts[5]
        floor_match_to = re.search(r'(\S+)\s*(\d+)\s*(층|F|f)$', parts[5])
        if floor_match_to:
            # state["to_location"] = floor_match_to.group(1).strip()
            state["to_floor"] = floor_match_to.group(2)
        else:
            simple_floor_match_to = re.search(r'(\d+)\s*(층|F|f)$', parts[5])
            if simple_floor_match_to:
                state["to_floor"] = simple_floor_match_to.group(1)


    # 6: 특이사항 (선택)
    if len(parts) > 6 and parts[6]:
        state["special_notes"] = parts[6]
    
    # 필수 필드 최종 확인
    if not state.get("customer_phone") or not state.get("from_location"):
        # 위에서 이미 오류 처리되었어야 하지만, 안전장치
        st.error(f"처리 오류: '{line_text[:50]}...' -> 전화번호 또는 출발지 주소가 최종적으로 누락되었습니다.")
        return None, None

    return state, filename_phone_part + ".json"


st.title("텍스트 이사 정보 JSON 변환 및 Google Drive 저장 (유연한 형식)")
st.write("한 줄에 하나의 이사 정보를 다음 순서대로 탭(tab)으로 구분하여 입력해주세요:")
st.markdown("`[이사날짜]` `[고객명]` `전화번호(필수)` `[이사종류(가/사)]` `출발지주소(필수) [층수]` `[도착지주소 [층수]]` `[특이사항]`")
st.markdown("""
- **대괄호 `[]` 안의 항목은 선택 사항**입니다. 순서는 지켜주세요.
- **전화번호**와 **출발지 주소**는 반드시 포함되어야 합니다.
- 날짜: "MM월 DD일", "MM/DD", "YYYY-MM-DD" 등. 생략 또는 "미정" 시 오늘 날짜.
- 고객명: 생략 또는 "미정" 시 "무명".
- 이사종류: "가" 또는 "사". 생략 시 "가정 이사".
- 주소의 층수는 주소 끝에 "2층", "3F" 등으로 포함하면 `from_floor`, `to_floor`로 파싱 시도됩니다.
""")

text_input = st.text_area("여기에 이사 정보를 한 줄씩 입력하세요:", height=200,
                          placeholder="예시1 (모든 정보): 05월 30일\t프란치스코\t010-9255-7232\t가\t동대문구 답십리로 173-4 2층\t동대문구 답십리동 101동 505호\t금 11시까지\n예시2 (일부 정보): \t\t010-1234-5678\t\t강남구 테헤란로 111\t서초구 강남대로 222\n예시3 (최소 정보): \t\t010-8765-4321\t\t용산구 한강대로 333")

if st.button("JSON 변환 및 Google Drive에 저장"):
    if not text_input:
        st.warning("입력된 텍스트가 없습니다.")
    else:
        lines = text_input.strip().split('\n')
        current_year = datetime.now(KST).year
        success_count = 0
        error_count = 0
        processed_lines = 0
        
        st.subheader("처리 결과:")
        progress_bar = st.progress(0)
        results_container = st.empty() # 결과를 표시할 컨테이너
        all_log_messages = []


        for i, line in enumerate(lines):
            line = line.strip()
            processed_lines +=1
            if not line:
                all_log_messages.append(f"⚪ 정보 없음: 빈 줄은 건너뜁니다.")
                continue

            status_obj, filename = parse_line_to_json_flexible(line, current_year)
            
            current_progress = processed_lines / len(lines)
            progress_bar.progress(current_progress)
            results_container.markdown(f"처리 중... ({processed_lines}/{len(lines)})")


            if status_obj and filename:
                try:
                    json_string = json.dumps(status_obj, indent=2, ensure_ascii=False) # ensure_ascii=False 중요
                    save_result = gdrive.save_json_file(filename, status_obj) # 딕셔너리 직접 전달

                    if save_result and save_result.get('id'):
                        log_message = f"✅ 성공: '{filename}' ({line[:30]}...) -> Drive 저장 (ID: {save_result.get('id')})"
                        all_log_messages.append(log_message)
                        success_count += 1
                    else:
                        log_message = f"❌ 실패: '{line[:30]}...' -> Drive 저장 실패 (save_json_file 결과 확인)"
                        all_log_messages.append(log_message)
                        error_count += 1
                except Exception as e:
                    log_message = f"❌ 오류: '{line[:30]}...' 처리 중 예외 발생 - {str(e)}"
                    all_log_messages.append(log_message)
                    error_count += 1
            else: # status_obj 또는 filename이 None일 경우 (파싱 실패 또는 필수 정보 누락)
                log_message = f"⚠️ 건너뜀: '{line[:30]}...' -> 파싱 실패 또는 필수 정보(전화번호/출발지) 누락."
                all_log_messages.append(log_message)
                error_count +=1
        
        results_container.empty() # "처리 중" 메시지 제거
        st.subheader("최종 요약")
        st.info(f"총 {len(lines)} 줄 중 {processed_lines} 줄 처리 시도.")
        st.info(f"성공: {success_count} 건")
        st.info(f"실패/건너뜀: {error_count} 건")

        if all_log_messages:
            with st.expander("전체 처리 로그 보기", expanded=True):
                for log_entry in all_log_messages:
                    if "성공" in log_entry:
                        st.markdown(f"<span style='color:green'>{log_entry}</span>", unsafe_allow_html=True)
                    elif "실패" in log_entry or "오류" in log_entry :
                        st.markdown(f"<span style='color:red'>{log_entry}</span>", unsafe_allow_html=True)
                    elif "건너뜀" in log_entry:
                         st.markdown(f"<span style='color:orange'>{log_entry}</span>", unsafe_allow_html=True)
                    else:
                        st.write(log_entry)