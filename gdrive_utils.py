# gdrive_utils.py (SCOPES 제거 및 직접 문자열 입력 방식으로 수정 + search_files + save_file + load_file 함수 추가)

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import io
import json

# Google Drive 인증 및 서비스 생성 함수
def get_gdrive_service():
    try:
        creds_json = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(
            creds_json,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        st.error(f"Google Drive 인증 실패: {e}")
        st.stop()

# 파일 목록 조회 (예시)
def list_drive_files():
    service = get_gdrive_service()
    try:
        results = service.files().list(
            pageSize=10,
            fields="files(id, name)"
        ).execute()
        return results.get("files", [])
    except Exception as e:
        st.error(f"파일 목록 조회 오류: {e}")
        return []

# JSON 파일 다운로드
def download_json_file(file_id):
    service = get_gdrive_service()
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return fh.read().decode("utf-8")
    except Exception as e:
        st.error(f"파일 다운로드 오류: {e}")
        return None

# JSON 파일 업로드 또는 덮어쓰기
def upload_or_update_json_to_drive(file_name, json_content, folder_id=None):
    service = get_gdrive_service()
    file_id = find_file_id_by_exact_name(file_name, folder_id)
    media = MediaIoBaseUpload(io.BytesIO(json_content.encode('utf-8')), mimetype="application/json", resumable=True)
    try:
        if file_id:
            updated = service.files().update(
                fileId=file_id,
                media_body=media,
                fields="id, name"
            ).execute()
            return {'id': updated.get('id'), 'status': 'updated'}
        else:
            metadata = {"name": file_name, "mimeType": "application/json"}
            if folder_id:
                metadata["parents"] = [folder_id]
            created = service.files().create(
                body=metadata,
                media_body=media,
                fields="id, name"
            ).execute()
            return {'id': created.get('id'), 'status': 'created'}
    except Exception as e:
        st.error(f"업로드/업데이트 오류: {e}")
        return None

# 정확한 파일명으로 ID 찾기
def find_file_id_by_exact_name(name, folder_id=None):
    service = get_gdrive_service()
    query = f"name = '{name}' and mimeType='application/json' and trashed = false"
    if folder_id:
        query += f" and '{folder_id}' in parents"
    try:
        result = service.files().list(q=query, spaces="drive", fields="files(id)", pageSize=1).execute()
        files = result.get("files", [])
        return files[0]['id'] if files else None
    except Exception as e:
        st.error(f"파일 검색 오류: {e}")
        return None

# 이름 포함 검색 기능 추가
def search_files(name_query, mime_type="application/json", folder_id=None):
    service = get_gdrive_service()
    escaped_query = name_query.replace("'", "\\'")
    query = f"name contains '{escaped_query}' and mimeType='{mime_type}' and trashed = false"
    if folder_id:
        query += f" and '{folder_id}' in parents"
    try:
        page_token = None
        results = []
        while True:
            response = service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name)',
                pageToken=page_token
            ).execute()
            results.extend(response.get("files", []))
            page_token = response.get("nextPageToken", None)
            if not page_token:
                break
        return results
    except Exception as e:
        st.error(f"검색 중 오류 발생: {e}")
        return []

# save_file 함수 (자동 직렬화 처리 추가)
def save_file(file_name, json_string):
    if not isinstance(json_string, str):
        json_string = json.dumps(json_string, ensure_ascii=False)
    return upload_or_update_json_to_drive(file_name, json_string)

# load_file 함수 (다운로드 후 dict 파싱)
def load_file(file_id):
    raw = download_json_file(file_id)
    if raw:
        try:
            return json.loads(raw)
        except Exception as e:
            st.error(f"불러온 파일을 JSON으로 파싱하는 데 실패했습니다: {e}")
            return None
    return None
