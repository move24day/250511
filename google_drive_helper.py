# google_drive_helper.py (이미지 저장 관련 함수 제거)

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload # MediaFileUpload 제거
import io
import json
# import mimetypes # 이미지 mime type 추측 불필요
import os # 이름 분리 등에 여전히 필요할 수 있음
# import time # 고유 파일명 찾기 지연 불필요
import traceback # 오류 로깅 위해 유지

# === Authentication and Service Object Creation ===
@st.cache_resource # Cache the service object for efficiency
def get_drive_service():
    """Connects to Google Drive API using service account credentials."""
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("Streamlit Secrets에 'gcp_service_account' 정보가 설정되지 않았습니다.")
            st.stop()
        creds_json = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(
            creds_json,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build("drive", "v3", credentials=creds)
    except KeyError:
        st.error("Streamlit Secrets에 'gcp_service_account' 정보가 설정되지 않았습니다.")
        st.stop()
    except Exception as e:
        st.error(f"Google Drive 서비스 연결 중 오류 발생: {e}")
        st.stop()

# === Download File Content (Generic Bytes) - JSON 로딩 위해 유지 ===
def download_file_bytes(file_id):
    """Downloads the content of a file from Google Drive as bytes."""
    service = get_drive_service()
    if not service: return None
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return fh.getvalue()
    except Exception as e:
        st.error(f"파일 다운로드 중 오류 발생 (ID: {file_id}): {e}")
        return None

# === Download JSON File Content (Specific helper) - 유지 ===
def download_json_file(file_id):
    """Downloads and decodes a JSON file."""
    file_bytes = download_file_bytes(file_id)
    if file_bytes:
        try:
            return file_bytes.decode("utf-8-sig") # BOM 처리 시도
        except UnicodeDecodeError:
            try:
                 return file_bytes.decode("utf-8") # 일반 utf-8 시도
            except UnicodeDecodeError:
                 st.error(f"다운로드된 파일(ID: {file_id})을 UTF-8로 디코딩하는 데 실패했습니다.")
                 return None
    return None


# === Find File ID by Exact Name (JSON 검색 위해 유지, mime type 명시 제거 고려) ===
def find_file_id_by_exact_name(exact_file_name, folder_id=None):
    """Finds a file ID by its exact name within a specific folder."""
    service = get_drive_service()
    if not service: return None

    escaped_file_name = exact_file_name.replace("'", "\\'")
    # mimeType 조건을 제거하여 모든 파일 형식을 찾도록 할 수 있음 (JSON 외 파일도 고려 시)
    # query = f"name = '{escaped_file_name}' and mimeType = 'application/json' and trashed = false" # JSON만 검색 시
    query = f"name = '{escaped_file_name}' and trashed = false" # 모든 파일 형식 검색 시

    if folder_id:
        query += f" and '{folder_id}' in parents"

    try:
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=1
        ).execute()
        items = results.get('files', [])
        return items[0].get('id') if items else None
    except Exception as e:
        st.error(f"정확한 파일 검색 오류 ('{exact_file_name}'): {e}")
        print(f"ERROR [Drive]: Exception during exact file search for '{exact_file_name}': {e}")
        traceback.print_exc()
        return None

# === find_unique_drive_filename 함수 제거 ===

# === save_image_file 함수 제거 ===

# === JSON Save/Load (기존 로직 유지) ===
def save_json_file(file_name, data_dict, folder_id=None):
    """Saves a dictionary as a JSON file on Google Drive (Overwrites if exists)."""
    service = get_drive_service()
    if not service: return None

    try:
        # JSON 파일만 대상으로 찾도록 mimeType 지정 (선택적)
        existing_file_id = find_file_id_by_exact_name(file_name, folder_id=folder_id)

        json_string = json.dumps(data_dict, ensure_ascii=False, indent=2)
        json_bytes = json_string.encode('utf-8')
        fh = io.BytesIO(json_bytes)
        # JSON 업로드는 application/json mime type 사용
        media = MediaIoBaseUpload(fh, mimetype="application/json", resumable=True)
        file_metadata = {"name": file_name} # Mime type은 여기서 지정 안해도 Drive가 추론 가능

        if folder_id: file_metadata["parents"] = [folder_id]

        if existing_file_id:
            print(f"DEBUG [Drive]: Updating existing JSON file: '{file_name}' (ID: {existing_file_id})")
            updated_file = service.files().update(
                fileId=existing_file_id,
                media_body=media,
                fields="id, name"
            ).execute()
            return {'id': existing_file_id, 'name': updated_file.get('name'), 'status': 'updated'}
        else:
            print(f"DEBUG [Drive]: Creating new JSON file: '{file_name}'")
            # 새로 생성 시에는 mimeType 명시
            file_metadata["mimeType"] = "application/json"
            created_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name"
            ).execute()
            return {'id': created_file.get("id"), 'name': created_file.get('name'), 'status': 'created'}

    except Exception as e:
         st.error(f"JSON 저장/업데이트 실패 ('{file_name}'): {e}")
         print(f"ERROR [Drive]: Failed to save/update JSON '{file_name}': {e}")
         traceback.print_exc()
         return None


def load_json_file(file_id):
    """Loads and parses a JSON file from Google Drive."""
    json_string = download_json_file(file_id)
    if json_string:
        try: return json.loads(json_string)
        except json.JSONDecodeError as e:
            st.error(f"불러온 파일(ID: {file_id})을 JSON으로 파싱하는 데 실패했습니다: {e}")
            return None
    return None

# === Find files by name contains (유지) ===
def find_files_by_name_contains(name_query, mime_types=None, folder_id=None):
    """Searches for files containing name_query, optionally filtering by mime types."""
    service = get_drive_service()
    if not service: return []

    escaped_query = name_query.replace("'", "\\'")
    query = f"name contains '{escaped_query}' and trashed = false"

    if isinstance(mime_types, str): query += f" and mimeType='{mime_types}'"
    elif isinstance(mime_types, list) and mime_types:
        mime_query_parts = [f"mimeType='{mt}'" for mt in mime_types]
        query += f" and ({' or '.join(mime_query_parts)})"
    if folder_id: query += f" and '{folder_id}' in parents"

    found_files = []
    try:
        page_token = None
        while True:
            response = service.files().list( q=query, spaces='drive', fields='nextPageToken, files(id, name, mimeType)', pageToken=page_token ).execute()
            for file in response.get('files', []): found_files.append({'id': file.get('id'), 'name': file.get('name'), 'mimeType': file.get('mimeType') })
            page_token = response.get('nextPageToken', None)
            if not page_token: break
        return found_files
    except Exception as e:
        st.error(f"파일 검색 중 오류 발생 ('{name_query}'): {e}")
        return []