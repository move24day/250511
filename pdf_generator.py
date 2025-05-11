# pdf_generator.py

import pandas as pd
import io
import streamlit as st
import traceback
import utils # utils.py 필요
import data # data.py 필요
import os
from datetime import date, datetime # datetime 추가

# --- ReportLab 관련 모듈 임포트 ---
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import Paragraph # Spacer는 사용 안 함
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    _REPORTLAB_AVAILABLE = True
except ImportError as reportlab_error:
    st.error(f"ReportLab 라이브러리를 찾을 수 없습니다: {reportlab_error}")
    print(f"ERROR [PDF]: ReportLab not found. PDF generation disabled. {reportlab_error}")
    _REPORTLAB_AVAILABLE = False

# --- 이미지 변환 관련 모듈 임포트 ---
_PDF2IMAGE_AVAILABLE = False
_PILLOW_AVAILABLE = False
try:
    from pdf2image import convert_from_bytes
    # Poppler 경로 설정 (필요한 경우)
    # import platform
    # if platform.system() == "Windows":
    #     # 예: poppler_path = r"C:\path\to\poppler-xx.xx.x\bin"
    #     # os.environ["PATH"] += os.pathsep + poppler_path
    #     pass # 사용자가 환경에 맞게 설정하도록 안내
    _PDF2IMAGE_AVAILABLE = True
except ImportError:
    print("Warning [PDF_GENERATOR]: pdf2image 라이브러리를 찾을 수 없습니다. PDF를 이미지로 변환하는 기능이 비활성화됩니다.")
    st.warning("pdf2image 라이브러리가 설치되지 않았거나 Poppler 유틸리티 경로가 설정되지 않았습니다. PDF의 이미지 변환 기능이 제한됩니다.")

try:
    from PIL import Image
    _PILLOW_AVAILABLE = True
except ImportError:
    print("Warning [PDF_GENERATOR]: Pillow 라이브러리를 찾을 수 없습니다. 이미지 처리에 문제가 발생할 수 있습니다.")


# --- 회사 정보 상수 정의 ---
COMPANY_ADDRESS = "서울 은평구 가좌로10길 33-1"
COMPANY_PHONE_1 = "010-5047-1111"
COMPANY_PHONE_2 = "1577-3101"
COMPANY_EMAIL = "move24day@gmail.com"

# --- 폰트 경로 설정 ---
NANUM_GOTHIC_FONT_PATH = "NanumGothic.ttf" # 실제 폰트 파일 경로

# --- PDF 생성 함수 ---
def generate_pdf(state_data, calculated_cost_items, total_cost, personnel_info):
    """주어진 데이터를 기반으로 견적서 PDF를 생성합니다."""
    print("--- DEBUG [PDF]: Starting generate_pdf function ---")
    if not _REPORTLAB_AVAILABLE:
        st.error("PDF 생성을 위한 ReportLab 라이브러리가 없어 PDF를 생성할 수 없습니다.")
        return None

    buffer = io.BytesIO()
    try:
        # --- 폰트 파일 확인 및 등록 ---
        font_path = NANUM_GOTHIC_FONT_PATH
        if not os.path.exists(font_path):
            st.error(f"PDF 생성 오류: 폰트 파일 '{font_path}'을(를) 찾을 수 없습니다.")
            print(f"ERROR [PDF]: Font file not found at '{font_path}'")
            return None
        try:
            if 'NanumGothic' not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont('NanumGothic', font_path))
                pdfmetrics.registerFont(TTFont('NanumGothicBold', font_path)) # Bold 폰트가 별도로 없다면 일반으로 대체
                print("DEBUG [PDF]: NanumGothic font registered.")
            else:
                print("DEBUG [PDF]: NanumGothic font already registered.")
        except Exception as font_e:
            st.error(f"PDF 생성 오류: 폰트 로딩/등록 실패 ('{font_path}'). 상세: {font_e}")
            print(f"ERROR [PDF]: Failed to load/register font '{font_path}': {font_e}")
            traceback.print_exc()
            return None

        # --- Canvas 및 기본 설정 ---
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        margin_x = 1.5*cm
        margin_y = 1.5*cm
        line_height = 0.6*cm # 기본 줄 간격
        right_margin_x = width - margin_x # 오른쪽 정렬 기준
        page_number = 1

        # --- 페이지 템플릿 (상단 회사 정보) ---
        def draw_page_template(canvas_obj, page_num):
            canvas_obj.saveState()
            canvas_obj.setFont('NanumGothic', 7)
            company_info_line_height = 0.35 * cm
            company_info_y = height - margin_y
            canvas_obj.drawRightString(right_margin_x, company_info_y, f"주소: {COMPANY_ADDRESS}")
            company_info_y -= company_info_line_height
            canvas_obj.drawRightString(right_margin_x, company_info_y, f"전화: {COMPANY_PHONE_1} | {COMPANY_PHONE_2}")
            company_info_y -= company_info_line_height
            canvas_obj.drawRightString(right_margin_x, company_info_y, f"이메일: {COMPANY_EMAIL}")
            canvas_obj.restoreState()

        # --- 초기 페이지 그리기 및 제목 ---
        current_y = height - margin_y - 1*cm 
        draw_page_template(c, page_number) 
        c.setFont('NanumGothicBold', 18)
        c.drawCentredString(width / 2.0, current_y, "이삿날 견적서(계약서)")
        current_y -= line_height * 2

        # --- 안내 문구 ---
        styles = getSampleStyleSheet()
        center_style = ParagraphStyle(name='CenterStyle', fontName='NanumGothic', fontSize=10, leading=14, alignment=TA_CENTER)
        service_text = """고객님의 이사를 안전하고 신속하게 책임지는 이삿날입니다."""
        p_service = Paragraph(service_text, center_style)
        p_service_width, p_service_height = p_service.wrapOn(c, width - margin_x*2, 5*cm) 
        if current_y - p_service_height < margin_y: 
            c.showPage(); page_number += 1; draw_page_template(c, page_number); current_y = height - margin_y - 1*cm
        p_service.drawOn(c, margin_x, current_y - p_service_height)
        current_y -= (p_service_height + line_height)


        # --- 기본 정보 그리기 ---
        c.setFont('NanumGothic', 11)
        is_storage = state_data.get('is_storage_move')
        has_via_point = state_data.get('has_via_point', False) 

        kst_date_str = utils.get_current_kst_time_str("%Y-%m-%d") if utils and hasattr(utils, 'get_current_kst_time_str') else datetime.now().strftime("%Y-%m-%d")
        customer_name = state_data.get('customer_name', '-')
        customer_phone = state_data.get('customer_phone', '-')
        moving_date_val = state_data.get('moving_date', '-')
        moving_date_str = str(moving_date_val)
        if isinstance(moving_date_val, date): 
             moving_date_str = moving_date_val.strftime('%Y-%m-%d')

        from_location = state_data.get('from_location', '-')
        to_location = state_data.get('to_location', '-')
        
        p_info = personnel_info if isinstance(personnel_info, dict) else {}
        final_men = p_info.get('final_men', 0)
        final_women = p_info.get('final_women', 0)
        personnel_text = f"남성 {final_men}명" + (f", 여성 {final_women}명" if final_women > 0 else "")
        selected_vehicle = state_data.get('final_selected_vehicle', '미선택')

        info_pairs = [
            ("고 객 명:", customer_name),
            ("연 락 처:", customer_phone),
            ("이 사 일:", moving_date_str),
            ("견 적 일:", kst_date_str),
            ("출 발 지:", from_location),
            ("도 착 지:", to_location),
        ]
        
        if has_via_point:
            info_pairs.append(("경 유 지:", state_data.get('via_point_location', '-')))
            info_pairs.append(("경유 작업:", state_data.get('via_point_method', '-')))

        if is_storage:
            storage_duration_str = f"{state_data.get('storage_duration', 1)} 일"
            storage_type = state_data.get('storage_type', data.DEFAULT_STORAGE_TYPE if data and hasattr(data, 'DEFAULT_STORAGE_TYPE') else "-")
            info_pairs.append(("보관 기간:", storage_duration_str))
            info_pairs.append(("보관 유형:", storage_type))
            if state_data.get('storage_use_electricity', False):
                 info_pairs.append(("보관 중 전기사용:", "예"))

            
        info_pairs.append(("작업 인원:", personnel_text))
        info_pairs.append(("선택 차량:", selected_vehicle))

        value_style = ParagraphStyle(name='InfoValueStyle', fontName='NanumGothic', fontSize=11, leading=13)
        label_width = 3 * cm 
        value_x = margin_x + label_width
        value_max_width = width - value_x - margin_x 

        for label, value in info_pairs:
             value_para = Paragraph(str(value), value_style)
             value_para_width, value_para_height = value_para.wrapOn(c, value_max_width, line_height * 3) 
             row_height = max(line_height, value_para_height + 0.1*cm) 

             if current_y - row_height < margin_y: 
                 c.showPage(); page_number += 1; draw_page_template(c, page_number); current_y = height - margin_y - 1*cm
                 c.setFont('NanumGothic', 11) 
             
             label_y_pos = current_y - row_height + (row_height - 11) / 2 + 2 
             c.drawString(margin_x, label_y_pos, label)
             
             para_y_pos = current_y - row_height + (row_height - value_para_height) / 2
             value_para.drawOn(c, value_x, para_y_pos)
             current_y -= row_height
        current_y -= line_height * 0.5 

        # --- 비용 상세 내역 ---
        cost_start_y = current_y 
        current_y -= 0.5*cm 

        if current_y < margin_y + 5*cm : 
            c.showPage(); page_number += 1; draw_page_template(c, page_number)
            current_y = height - margin_y - 1*cm 
            c.setFont('NanumGothic', 11) 

        c.setFont('NanumGothicBold', 12)
        c.drawString(margin_x, current_y, "[ 비용 상세 내역 ]")
        current_y -= line_height * 1.2 

        c.setFont('NanumGothicBold', 10)
        cost_col1_x = margin_x          
        cost_col2_x = margin_x + 8*cm   
        cost_col3_x = margin_x + 11*cm  
        c.drawString(cost_col1_x, current_y, "항목")
        c.drawRightString(cost_col2_x + 2*cm, current_y, "금액") 
        c.drawString(cost_col3_x, current_y, "비고")
        c.setFont('NanumGothic', 10) 
        current_y -= 0.2*cm 
        c.line(cost_col1_x, current_y, right_margin_x, current_y) 
        current_y -= line_height * 0.8 

        cost_items_processed = []
        date_surcharge_amount = 0
        date_surcharge_index = -1
        temp_items = []
        if calculated_cost_items and isinstance(calculated_cost_items, list):
            temp_items = [list(item) for item in calculated_cost_items if isinstance(item, (list, tuple)) and len(item) >= 2 and "오류" not in str(item[0])]

        for i, item in enumerate(temp_items):
             if str(item[0]) == "날짜 할증":
                 try: date_surcharge_amount = int(item[1] or 0) 
                 except (ValueError, TypeError): date_surcharge_amount = 0
                 date_surcharge_index = i
                 break 

        base_fare_index = -1
        for i, item in enumerate(temp_items):
              if str(item[0]) == "기본 운임":
                 base_fare_index = i
                 if date_surcharge_index != -1 and date_surcharge_amount > 0 : 
                     try:
                         current_base_fare = int(item[1] or 0)
                         item[1] = current_base_fare + date_surcharge_amount 
                         selected_vehicle_remark = state_data.get('final_selected_vehicle', '') 
                         item[2] = f"{selected_vehicle_remark} (이사 집중일 운영 요금 적용)" 
                     except Exception as e:
                         print(f"Error merging date surcharge into base fare: {e}")
                 break 
        
        if date_surcharge_index != -1 and base_fare_index != -1 and date_surcharge_amount > 0: 
              if date_surcharge_index < len(temp_items):
                  try:
                      del temp_items[date_surcharge_index] 
                  except IndexError:
                      print(f"Warning: Could not remove date surcharge item at index {date_surcharge_index}")
              else:
                   print(f"Warning: date_surcharge_index {date_surcharge_index} out of range for temp_items")


        for item_data in temp_items:
             item_desc = str(item_data[0])
             item_cost_int = 0
             item_note = ""
             try: item_cost_int = int(item_data[1] or 0) 
             except (ValueError, TypeError): item_cost_int = 0
             if len(item_data) > 2:
                 item_note = str(item_data[2] or '') 
             cost_items_processed.append((item_desc, item_cost_int, item_note))
        
        if cost_items_processed:
            styleDesc = ParagraphStyle(name='CostDesc', fontName='NanumGothic', fontSize=9, leading=11, alignment=TA_LEFT)
            styleCost = ParagraphStyle(name='CostAmount', fontName='NanumGothic', fontSize=9, leading=11, alignment=TA_RIGHT)
            styleNote = ParagraphStyle(name='CostNote', fontName='NanumGothic', fontSize=9, leading=11, alignment=TA_LEFT)

            for item_desc, item_cost, item_note in cost_items_processed:
                cost_str = f"{item_cost:,.0f} 원" if item_cost is not None else "0 원"
                note_str = item_note if item_note else ""

                p_desc = Paragraph(item_desc, styleDesc)
                p_cost = Paragraph(cost_str, styleCost)
                p_note = Paragraph(note_str, styleNote)

                desc_width = cost_col2_x - cost_col1_x - 0.5*cm 
                cost_width = (cost_col3_x - cost_col2_x) + 1.5*cm 
                note_width = right_margin_x - cost_col3_x     
                
                desc_height = p_desc.wrap(desc_width, 1000)[1] 
                cost_height = p_cost.wrap(cost_width, 1000)[1]
                note_height = p_note.wrap(note_width, 1000)[1]
                max_row_height = max(desc_height, cost_height, note_height, line_height * 0.8) 

                if current_y - max_row_height < margin_y: 
                    c.showPage(); page_number += 1; draw_page_template(c, page_number)
                    current_y = height - margin_y - 1*cm
                    c.setFont('NanumGothicBold', 10)
                    c.drawString(cost_col1_x, current_y, "항목")
                    c.drawRightString(cost_col2_x + 2*cm, current_y, "금액")
                    c.drawString(cost_col3_x, current_y, "비고")
                    current_y -= 0.2*cm; c.line(cost_col1_x, current_y, right_margin_x, current_y); current_y -= line_height * 0.8
                    c.setFont('NanumGothic', 10) 

                y_draw_base = current_y - max_row_height 
                p_desc.drawOn(c, cost_col1_x, y_draw_base + (max_row_height - desc_height)) 
                p_cost.drawOn(c, cost_col2_x + 2*cm - cost_width, y_draw_base + (max_row_height - cost_height)) 
                p_note.drawOn(c, cost_col3_x, y_draw_base + (max_row_height - note_height))
                current_y -= (max_row_height + 0.2*cm) 
        else: 
             if current_y < margin_y + 3*cm : 
                 c.showPage(); page_number += 1; draw_page_template(c, page_number)
                 current_y = height - margin_y - 1*cm
             c.drawString(cost_col1_x, current_y, "계산된 비용 내역이 없습니다.")
             current_y -= line_height

        # --- 비용 요약 ---
        summary_start_y = current_y
        if summary_start_y < margin_y + line_height * 5 : 
            c.showPage(); page_number += 1; draw_page_template(c, page_number)
            summary_start_y = height - margin_y - 1*cm
            c.setFont('NanumGothic', 11) 
        
        current_y = summary_start_y
        c.line(cost_col1_x, current_y, right_margin_x, current_y) 
        current_y -= line_height

        total_cost_num = 0
        if isinstance(total_cost, (int, float)):
            total_cost_num = int(total_cost)
            
        deposit_amount_raw = state_data.get('deposit_amount', state_data.get('tab3_deposit_amount', 0))
        deposit_amount = 0
        try: deposit_amount = int(deposit_amount_raw or 0) 
        except (ValueError, TypeError): deposit_amount = 0
        remaining_balance = total_cost_num - deposit_amount

        c.setFont('NanumGothicBold', 12)
        c.drawString(cost_col1_x, current_y, "총 견적 비용 (VAT 별도)")
        total_cost_str = f"{total_cost_num:,.0f} 원"
        c.setFont('NanumGothicBold', 14) 
        c.drawRightString(right_margin_x, current_y, total_cost_str)
        current_y -= line_height

        c.setFont('NanumGothic', 11)
        c.drawString(cost_col1_x, current_y, "계약금 (-)")
        deposit_str = f"{deposit_amount:,.0f} 원"
        c.setFont('NanumGothic', 12)
        c.drawRightString(right_margin_x, current_y, deposit_str)
        current_y -= line_height

        c.setFont('NanumGothicBold', 12)
        c.drawString(cost_col1_x, current_y, "잔금 (VAT 별도)")
        remaining_str = f"{remaining_balance:,.0f} 원"
        c.setFont('NanumGothicBold', 14) 
        c.drawRightString(right_margin_x, current_y, remaining_str)
        current_y -= line_height

        # --- 고객요구사항 그리기 ---
        special_notes = state_data.get('special_notes', '').strip()
        if special_notes:
            notes_section_start_y = current_y
            if notes_section_start_y < margin_y + line_height * 3 : 
                c.showPage(); page_number += 1; draw_page_template(c, page_number)
                current_y = height - margin_y - 1*cm; notes_section_start_y = current_y
                c.setFont('NanumGothic', 11) 
            else:
                current_y -= line_height 

            c.setFont('NanumGothicBold', 11)
            c.drawString(margin_x, current_y, "[ 고객요구사항 ]")
            current_y -= line_height * 1.2 

            styleNotes = ParagraphStyle(name='NotesParagraph', fontName='NanumGothic', fontSize=10, leading=12, alignment=TA_LEFT)
            available_width = width - margin_x * 2 
            
            notes_parts = [part.strip().replace('\n', '<br/>') for part in special_notes.split('.') if part.strip()]

            for note_part in notes_parts:
                p_part = Paragraph(note_part, styleNotes)
                part_width, part_height = p_part.wrapOn(c, available_width, 1000) 

                if current_y - part_height < margin_y: 
                    c.showPage(); page_number += 1; draw_page_template(c, page_number)
                    current_y = height - margin_y - 1*cm 
                    c.setFont('NanumGothic', 11) 
                
                p_part.drawOn(c, margin_x, current_y - part_height)
                current_y -= (part_height + line_height * 0.2) 
        
        c.save()
        buffer.seek(0)
        print("--- DEBUG [PDF]: PDF generation successful ---")
        return buffer.getvalue()

    except Exception as e:
        st.error(f"PDF 생성 중 예외 발생: {e}")
        print(f"Error during PDF generation: {e}")
        traceback.print_exc() 
        return None

# --- PDF를 이미지로 변환하는 함수 ---
def generate_quote_image_from_pdf(pdf_bytes, image_format='JPEG', poppler_path=None):
    """
    PDF 바이트를 이미지 바이트로 변환합니다.
    첫 번째 페이지만 이미지로 변환합니다.
    poppler_path: Windows에서 Poppler 바이너리 경로 (선택 사항)
    """
    if not _PDF2IMAGE_AVAILABLE:
        st.error("pdf2image 라이브러리가 없어 PDF를 이미지로 변환할 수 없습니다. Poppler 설치 및 경로 설정을 확인하세요.")
        return None
    if not _PILLOW_AVAILABLE:
        st.error("Pillow 라이브러리가 없어 이미지를 처리할 수 없습니다.")
        return None
    if not pdf_bytes:
        st.error("이미지로 변환할 PDF 데이터가 없습니다.")
        return None

    try:
        # convert_from_bytes에 poppler_path 인자 전달 (필요한 경우)
        if poppler_path:
             images = convert_from_bytes(pdf_bytes, fmt=image_format.lower(), first_page=1, last_page=1, poppler_path=poppler_path)
        else:
             images = convert_from_bytes(pdf_bytes, fmt=image_format.lower(), first_page=1, last_page=1)


        if images:
            img_byte_arr = io.BytesIO()
            # RGBA 이미지를 RGB로 변환 (JPEG는 알파 채널 미지원)
            img_to_save = images[0]
            if img_to_save.mode == 'RGBA' and image_format.upper() == 'JPEG':
                img_to_save = img_to_save.convert('RGB')
            
            img_to_save.save(img_byte_arr, format=image_format)
            img_byte_arr = img_byte_arr.getvalue()
            print(f"--- DEBUG [PDF_TO_IMAGE]: PDF converted to {image_format} successfully ---")
            return img_byte_arr
        else:
            st.error("PDF에서 이미지를 추출하지 못했습니다.")
            return None
    except Exception as e:
        st.error(f"PDF를 이미지로 변환하는 중 오류 발생: {e}")
        print(f"Error converting PDF to image: {e}")
        traceback.print_exc()
        st.info("Poppler가 시스템에 설치되어 있고 PATH에 등록되었는지 확인해주세요. Windows의 경우 Poppler 바이너리 경로를 직접 지정해야 할 수 있습니다.")
        return None


# --- 엑셀 생성 함수 (generate_excel) ---
# (기존 generate_excel 함수 내용은 변경 없이 유지됩니다)
def generate_excel(state_data, calculated_cost_items, total_cost, personnel_info):
    """
    주어진 데이터를 기반으로 요약 정보를 Excel 형식으로 생성합니다.
    (ui_tab3.py의 요약 표시에 사용됨, utils.get_item_qty 호출)
    경유지 정보 추가
    """
    print("--- DEBUG [Excel Summary]: Starting generate_excel function ---")
    output = io.BytesIO()
    try:
        # --- 기본 정보 준비 ---
        is_storage = state_data.get('is_storage_move', False)
        is_long_distance = state_data.get('apply_long_distance', False)
        is_waste = state_data.get('has_waste_check', False)
        has_via = state_data.get('has_via_point', False) # 경유지 유무

        from_method = state_data.get('from_method', '-')
        to_method = state_data.get('to_method', '-')
        to_floor = state_data.get('to_floor', '-') 
        use_sky_from = (from_method == "스카이 🏗️")
        use_sky_to = (to_method == "스카이 🏗️")
        
        p_info = personnel_info if isinstance(personnel_info, dict) else {}
        final_men = p_info.get('final_men', 0)
        final_women = p_info.get('final_women', 0)
        personnel_text = f"남성 {final_men}명" + (f", 여성 {final_women}명" if final_women > 0 else "")
        dest_address = state_data.get('to_location', '-')
        
        kst_excel_date = ''
        if utils and hasattr(utils, 'get_current_kst_time_str'):
            try: kst_excel_date = utils.get_current_kst_time_str("%Y-%m-%d")
            except Exception as e_time: print(f"Warning: Error calling utils.get_current_kst_time_str: {e_time}"); kst_excel_date = datetime.now().strftime("%Y-%m-%d")
        else: print("Warning: utils module or get_current_kst_time_str not available."); kst_excel_date = datetime.now().strftime("%Y-%m-%d")

        # 1. '견적 정보' 시트 데이터 생성 (경유지 정보 추가)
        ALL_INFO_LABELS = [
            "회사명", "주소", "연락처", "이메일", "", 
            "고객명", "고객 연락처", "견적일", "이사 종류", "",
            "이사일", "출발지", "도착지", "출발층", "도착층", "출발 작업", "도착 작업", "",
            "경유지 이사", "경유지 주소", "경유지 작업방법", "", 
            "보관 이사", "보관 기간", "보관 유형", "보관 중 전기사용", "", # 전기사용 추가
            "장거리 적용", "장거리 구간", "",
            "스카이 사용 시간", "", "폐기물 처리(톤)", "", "날짜 할증 선택", "",
            "총 작업 인원", "", "선택 차량", "자동 추천 차량",
            "이사짐 총 부피", "이사짐 총 무게", "", "고객요구사항"
        ]
        info_data_list = []
        for label in ALL_INFO_LABELS:
            value = '-' 
            if not label: 
                info_data_list.append(("", ""))
                continue
            
            if label == "회사명": value = "(주)이사데이"
            elif label == "주소": value = COMPANY_ADDRESS
            elif label == "연락처": value = f"{COMPANY_PHONE_1} | {COMPANY_PHONE_2}"
            elif label == "이메일": value = COMPANY_EMAIL
            elif label == "고객명": value = state_data.get('customer_name', '-')
            elif label == "고객 연락처": value = state_data.get('customer_phone', '-')
            elif label == "견적일": value = kst_excel_date
            elif label == "이사 종류": value = state_data.get('base_move_type', '-')
            elif label == "이사일": value = str(state_data.get('moving_date', '-'))
            elif label == "출발지": value = state_data.get('from_location', '-')
            elif label == "도착지": value = dest_address
            elif label == "출발층": value = state_data.get('from_floor', '-')
            elif label == "도착층": value = to_floor
            elif label == "출발 작업": value = from_method
            elif label == "도착 작업": value = to_method
            elif label == "경유지 이사": value = '예' if has_via else '아니오' 
            elif label == "경유지 주소": value = state_data.get('via_point_location', '-') if has_via else '-' 
            elif label == "경유지 작업방법": value = state_data.get('via_point_method', '-') if has_via else '-' 
            elif label == "보관 이사": value = '예' if is_storage else '아니오'
            elif label == "보관 기간": 
                duration = state_data.get('storage_duration', '-')
                value = f"{duration} 일" if is_storage and duration != '-' else '-'
            elif label == "보관 유형": value = state_data.get('storage_type', '-') if is_storage else '-'
            elif label == "보관 중 전기사용": value = '예' if is_storage and state_data.get('storage_use_electricity', False) else ('아니오' if is_storage else '-')
            elif label == "장거리 적용": value = '예' if is_long_distance else '아니오'
            elif label == "장거리 구간": value = state_data.get('long_distance_selector', '-') if is_long_distance else '-'
            elif label == "스카이 사용 시간":
                 sky_details = []
                 if use_sky_from: sky_details.append(f"출발지 {state_data.get('sky_hours_from', 1)}시간")
                 if use_sky_to: sky_details.append(f"도착지 {state_data.get('sky_hours_final', 1)}시간")
                 value = ", ".join(sky_details) if sky_details else '-'
            elif label == "폐기물 처리(톤)": value = f"예 ({state_data.get('waste_tons_input', 0.5):.1f} 톤)" if is_waste else '아니오'
            elif label == "날짜 할증 선택":
                 date_options_list = ["이사많은날 🏠", "손없는날 ✋", "월말 📅", "공휴일 🎉", "금요일 📅"]
                 date_keys = [f"date_opt_{i}_widget" for i in range(len(date_options_list))]
                 selected_dates_excel = [date_options_list[i] for i, key in enumerate(date_keys) if state_data.get(key, False)]
                 value = ", ".join(selected_dates_excel) if selected_dates_excel else '없음'
            elif label == "총 작업 인원": value = personnel_text
            elif label == "선택 차량": value = state_data.get('final_selected_vehicle', '미선택')
            elif label == "자동 추천 차량": value = state_data.get('recommended_vehicle_auto', '-')
            elif label == "이사짐 총 부피": value = f"{state_data.get('total_volume', 0.0):.2f} m³"
            elif label == "이사짐 총 무게": value = f"{state_data.get('total_weight', 0.0):.2f} kg"
            elif label == "고객요구사항": value = state_data.get('special_notes', '').strip() or '-'
            info_data_list.append((label, value))
        df_info = pd.DataFrame(info_data_list, columns=["항목", "내용"])

        # 2. '전체 품목 수량' 시트 데이터 생성 (utils.get_item_qty 사용)
        all_items_data = []
        current_move_type = state_data.get('base_move_type', '')
        item_defs = data.item_definitions.get(current_move_type, {}) if data and hasattr(data, 'item_definitions') else {}
        processed_all_items = set() 
        if isinstance(item_defs, dict):
            for section, item_list in item_defs.items():
                if section == "폐기 처리 품목 🗑️": continue
                if isinstance(item_list, list):
                    for item_name in item_list:
                         if item_name in processed_all_items: continue
                         if data and hasattr(data, 'items') and item_name in data.items:
                              qty = 0
                              if utils and hasattr(utils, 'get_item_qty'):
                                   try: qty = utils.get_item_qty(state_data, item_name)
                                   except Exception as e_get_qty: print(f"Error calling utils.get_item_qty for {item_name}: {e_get_qty}")
                              else: print(f"Warning: utils module or get_item_qty not available.")
                              all_items_data.append({"품목명": item_name, "수량": qty})
                              processed_all_items.add(item_name)
        
        if all_items_data:
            df_all_items = pd.DataFrame(all_items_data, columns=["품목명", "수량"])
        else: 
            df_all_items = pd.DataFrame({"정보": ["정의된 품목 없음"]})


        # 3. '비용 내역 및 요약' 시트 데이터 생성 (경유지 추가요금 포함)
        cost_details_excel = []
        if calculated_cost_items and isinstance(calculated_cost_items, list):
            for item in calculated_cost_items: 
                 if isinstance(item, (list, tuple)) and len(item) >= 2:
                    item_desc = str(item[0])
                    item_cost = 0
                    item_note = ""
                    try: item_cost = int(item[1] or 0) 
                    except (ValueError, TypeError): item_cost = 0
                    if len(item) > 2:
                         try: item_note = str(item[2] or '') 
                         except Exception: item_note = ''
                    
                    if "오류" not in item_desc: 
                        cost_details_excel.append({"항목": item_desc, "금액": item_cost, "비고": item_note})

        if cost_details_excel:
            df_costs = pd.DataFrame(cost_details_excel, columns=["항목", "금액", "비고"])
        else: 
            df_costs = pd.DataFrame([{"항목": "계산된 비용 없음", "금액": 0, "비고": ""}])

        num_total = total_cost if isinstance(total_cost,(int,float)) else 0
        deposit_raw = state_data.get('deposit_amount', state_data.get('tab3_deposit_amount',0))
        try: deposit_amount = int(deposit_raw or 0)
        except (ValueError, TypeError): deposit_amount = 0

        remaining_balance = num_total - deposit_amount
        summary_data = [
            {"항목": "--- 비용 요약 ---", "금액": "", "비고": ""}, 
            {"항목": "총 견적 비용 (VAT 별도)", "금액": num_total, "비고": "모든 항목 합계"},
            {"항목": "계약금 (-)", "금액": deposit_amount, "비고": ""},
            {"항목": "잔금 (VAT 별도)", "금액": remaining_balance, "비고": "총 견적 비용 - 계약금"}
        ]
        df_summary = pd.DataFrame(summary_data, columns=["항목", "금액", "비고"])
        df_costs_final = pd.concat([df_costs, df_summary], ignore_index=True)


        # 4. 엑셀 파일 쓰기 및 서식 지정 (컬럼 너비 계산 수정됨)
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_info.to_excel(writer, sheet_name='견적 정보', index=False)
            df_all_items.to_excel(writer, sheet_name='전체 품목 수량', index=False)
            df_costs_final.to_excel(writer, sheet_name='비용 내역 및 요약', index=False)

            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for col in worksheet.columns:
                    max_length = 0
                    column = col[0].column_letter 
                    
                    try:
                        header_value = worksheet[f"{column}1"].value 
                        header_len = len(str(header_value)) if header_value is not None else 0
                    except Exception:
                        header_len = 0 
                    max_length = header_len

                    for cell in col:
                        try:
                            if cell.value is not None:
                                cell_value_str = str(cell.value)
                                lines = cell_value_str.split('\n') 
                                cell_len = 0
                                if lines:
                                     try:
                                          line_lengths = [len(str(line or '')) for line in lines]
                                          if line_lengths: cell_len = max(line_lengths)
                                     except Exception as max_err:
                                          print(f"Warning: Error calculating max line length for cell {cell.coordinate}: {max_err}")
                                          cell_len = len(lines[0]) if lines else 0 
                                if cell_len > max_length:
                                    max_length = cell_len
                        except Exception as cell_proc_err:
                             print(f"Warning: Error processing cell {cell.coordinate} for width calculation: {cell_proc_err}")
                    
                    adjusted_width = (max_length + 2) * 1.2 
                    adjusted_width = min(adjusted_width, 60) 
                    adjusted_width = max(adjusted_width, header_len + 2) 
                    worksheet.column_dimensions[column].width = adjusted_width

        excel_data = output.getvalue()
        print("--- DEBUG [Excel Summary]: generate_excel function finished successfully ---")
        return excel_data
    except Exception as e:
        st.error(f"엑셀 파일 생성 중 오류: {e}")
        print(f"Error during Excel generation: {e}")
        traceback.print_exc()
        return None
    finally:
        if 'output' in locals() and output is not None:
             try: output.close()
             except Exception as close_e: print(f"Error closing Excel buffer: {close_e}")

# pdf_generator.py 파일 끝
