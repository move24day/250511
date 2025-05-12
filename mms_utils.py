# mms_utils.py
import streamlit as st
import requests
import traceback
import re

def normalize_phone_number(phone_number_str):
    if not phone_number_str or not isinstance(phone_number_str, str):
        return None
    digits = re.sub(r'\D', '', phone_number_str)
    if digits.startswith('010') and len(digits) == 11:
        return digits
    elif digits.startswith('10') and len(digits) == 10:
        return '0' + digits
    # 아래 st.warning 라인을 주석 처리하여 불필요한 경고 방지
    # st.warning(f"전화번호({phone_number_str})가 표준 형식에 맞지 않을 수 있습니다. MMS 게이트웨이 요구사항을 확인하세요.")
    return digits

def send_mms_with_image(recipient_phone, image_bytes, filename="견적서.jpg", text_message="견적서가 도착했습니다."):
    st.info(f"MMS 발송 시도: 수신자={recipient_phone}, 파일명={filename}")
    if not recipient_phone:
        st.error("수신자 전화번호가 없습니다.")
        return False
    normalized_phone = normalize_phone_number(recipient_phone)
    if not normalized_phone:
        st.error(f"유효하지 않은 전화번호 형식입니다: {recipient_phone}")
        return False
    if not image_bytes:
        st.error("이미지 데이터가 없습니다.")
        return False
    try:
        mms_creds = st.secrets.get("mms_credentials", {})
        api_key = mms_creds.get("api_key")
        aligo_id = mms_creds.get("userid")
        sender_number = mms_creds.get("sender_number")
        gateway_url = mms_creds.get("gateway_url", "https://apis.aligo.in/send/")

        if not all([api_key, aligo_id, sender_number]):
            st.error("secrets.toml 파일에 api_key, userid, sender_number가 설정되어 있어야 합니다.")
            return False

        payload = {
            "key": api_key,
            "userid": aligo_id,
            "sender": sender_number,
            "receiver": normalized_phone,
            "msg": text_message,
            "msg_type": "MMS",
            "title": "견적서",
            "destination": f"{normalized_phone}|고객"
        }
        files = {
            "image": (filename, image_bytes, "image/jpeg")
        }

        response = requests.post(gateway_url, data=payload, files=files)
        result = response.json()
        if result.get("result_code") == "1":
            st.success("MMS 발송 성공")
            return True
        else:
            st.error(f"MMS 발송 실패: {result.get('message')}")
            return False

    except Exception as e:
        st.error(f"예외 발생: {e}")
        traceback.print_exc()
        return False

# from pathlib import Path
# # Save the modified `mms_utils.py` to disk to give the user
# output_path = Path("/mnt/data/mms_utils_aligo.py") # 이 부분은 제거하거나 주석 처리합니다.
# output_path.write_text(...) # 이 부분은 제거하거나 주석 처리합니다.
# output_path # 이 부분은 제거하거나 주석 처리합니다.