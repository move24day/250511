# utils.py (get_item_qty 함수 추가)

import re
from datetime import datetime
import pytz # 시간대 처리를 위해 필요

# data 모듈 임포트 시도 (get_item_qty에서 필요)
try:
    import data
except ImportError:
    print("Warning [utils.py]: data.py not found, get_item_qty might not work correctly.")
    data = None

def get_current_kst_time_str(format="%Y-%m-%d %H:%M"):
    """
    현재 한국 표준시(KST) 기준의 날짜와 시간을 지정된 형식의 문자열로 반환합니다.
    pytz 라이브러리가 없거나 시간대 변환 실패 시 시스템 기본 시간 사용.
    """
    try:
        kst = pytz.timezone("Asia/Seoul")
        now_kst = datetime.now(kst)
        return now_kst.strftime(format)
    except Exception as e:
        print(f"Warning: KST 시간 변환 실패 ({e}). 시스템 시간 사용.")
        return datetime.now().strftime(format)

def extract_phone_number_part(phone_str, length=4, default="번호없음"):
    """
    전화번호 문자열에서 숫자만 추출하여 뒤에서부터 지정된 길이만큼 반환합니다.
    유효한 숫자 부분이 없거나 부족하면 default 값을 반환합니다.
    """
    if not phone_str or not isinstance(phone_str, str):
        return default
    digits = re.sub(r'\D', '', phone_str) # 숫자 외 문자 제거
    if len(digits) >= length:
        return digits[-length:] # 뒤 length 자리 반환
    elif len(digits) > 0:
        return digits # 짧으면 있는 숫자라도 반환
    else:
        return default # 숫자가 없으면 기본값 반환

# --- !!! get_item_qty 함수 정의 추가 !!! ---
def get_item_qty(state_data, item_name_to_find):
    """
    state_data에서 특정 품목명의 수량을 찾아 반환합니다.
    이사 유형별로 정의된 섹션을 검색합니다.
    """
    # data 모듈 또는 필요한 속성이 로드되지 않았으면 0 반환
    if not data or not hasattr(data, 'item_definitions') or not hasattr(data, 'items'):
        print(f"Warning [get_item_qty]: data module or definitions missing for item '{item_name_to_find}'")
        return 0

    current_move_type = state_data.get('base_move_type')
    if not current_move_type:
        # print(f"Warning [get_item_qty]: base_move_type not found in state_data for item '{item_name_to_find}'")
        return 0 # 이사 유형 없으면 검색 불가

    # 해당 이사 유형의 품목 정의 가져오기
    item_definitions_for_type = data.item_definitions.get(current_move_type, {})
    if isinstance(item_definitions_for_type, dict):
        # 정의된 모든 섹션 순회
        for section, item_list in item_definitions_for_type.items():
            # 품목 리스트가 리스트 형태이고, 찾는 품목이 리스트 안에 있으면
            if isinstance(item_list, list) and item_name_to_find in item_list:
                # 해당 품목의 state_data 키 생성
                key = f"qty_{current_move_type}_{section}_{item_name_to_find}"
                # state_data에 키가 존재하면 값 반환 시도
                if key in state_data:
                    try:
                        # state_data 값 가져오기 (None일 경우 0으로 처리)
                        value = state_data.get(key, 0)
                        # 정수로 변환하여 반환 (변환 실패 시 0 반환)
                        return int(value or 0)
                    except (ValueError, TypeError):
                        # print(f"Warning [get_item_qty]: Could not convert value for key '{key}' to int.")
                        return 0 # 변환 실패 시 0 반환
                # else: 키가 state_data에 없으면 다음 섹션 검색 계속
    else:
         print(f"Warning [get_item_qty]: item_definitions for '{current_move_type}' is not a dictionary.")


    # 모든 섹션에서 못 찾았으면 0 반환
    # print(f"Warning [get_item_qty]: Item '{item_name_to_find}' not found in any section for move type '{current_move_type}'.")
    return 0
# --- !!! 함수 추가 완료 !!! ---