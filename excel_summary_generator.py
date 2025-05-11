# excel_summary_generator.py (PDF 생성기에서 분리된 Excel 요약 생성 로직)

import pandas as pd
import io
import streamlit as st
import traceback
import utils # utils.py 가 필요합니다
import data # data.py 가 필요합니다
import os
from datetime import date
import openpyxl # ExcelWriter 및 형식 지정 위해 필요
import math # 컬럼 너비 계산 위해 추가

def generate_summary_excel(state_data, calculated_cost_items, personnel_info, vehicle_info, waste_info):
    """계산된 견적 정보를 바탕으로 상세 내역 Excel 파일을 생성하여 Bytes 형태로 반환합니다."""
    try:
        output = io.BytesIO()

        # --- 데이터 준비 ---

        # 1. 견적 기본 정보 DataFrame 생성
        # 실제 투입 차량/인원 정보 반영
        actual_vehicles_disp = state_data.get('actual_vehicles_override', {})
        if not any(actual_vehicles_disp.values()):
            actual_vehicles_disp = vehicle_info.get('recommended_vehicles', {})
        vehicle_str_excel = ", ".join([f"{name}({qty}대)" for name, qty in actual_vehicles_disp.items() if qty > 0])
        if not vehicle_str_excel: vehicle_str_excel = "정보 없음"

        actual_men_excel = state_data.get('actual_men', personnel_info.get('final_men', 0))
        actual_women_excel = state_data.get('actual_women', personnel_info.get('final_women', 0))

        info_data = {
            "항목": ["고객명", "연락처", "이메일", "이사일", "이사 종류",
                   "출발지 주소", "출발지 층수", "출발지 E/V",
                   "도착지 주소", "도착지 층수", "도착지 E/V",
                   "예상 총 부피(CBM)", "예상 총 무게(kg)",
                   "실제 투입 차량", "실제 투입 인원(남)", "실제 투입 인원(여)",
                   "사다리차(출발)", "사다리차(도착)", "지방 사다리 추가요금",
                   "폐기물 처리(톤)", "폐기물 처리 비용",
                   "최종 조정 금액"], # 최종 금액 추가
            "내용": [
                state_data.get('customer_name', ''), state_data.get('customer_phone', ''), state_data.get('customer_email', ''),
                state_data.get('moving_date', ''), state_data.get('base_move_type', ''),
                state_data.get('start_address', ''), state_data.get('start_floor', ''), '있음' if state_data.get('start_elevator') else '없음',
                state_data.get('end_address', ''), state_data.get('end_floor', ''), '있음' if state_data.get('end_elevator') else '없음',
                f"{state_data.get('calculated_total_volume', 0):.2f}", f"{state_data.get('calculated_total_weight', 0):.1f}",
                vehicle_str_excel, # 실제 투입 차량
                actual_men_excel, # 실제 투입 남자
                actual_women_excel, # 실제 투입 여자
                f"{state_data.get('start_ladder_preset','-')}" if state_data.get('start_ladder') else "미사용",
                f"{state_data.get('end_ladder_preset','-')}" if state_data.get('end_ladder') else "미사용",
                f"{state_data.get('regional_ladder_surcharge', 0):,.0f}",
                f"{waste_info.get('total_waste_tons', 0.0):.1f}", f"{waste_info.get('total_waste_cost', 0):,.0f}",
                f"{state_data.get('final_adjusted_cost', state_data.get('calculated_total_cost', 0)):,.0f}" # 최종 금액 표시
            ]
        }
        df_info = pd.DataFrame(info_data)

        # 2. 전체 품목 리스트 DataFrame 생성
        all_items_data = []
        move_type = state_data.get('base_move_type')
        if move_type and move_type in data.item_definitions:
            processed_items = set() # 중복 방지
            item_defs_excel = data.item_definitions[move_type]
            if isinstance(item_defs_excel, dict):
                for section, item_list in item_defs_excel.items():
                    if section == "폐기 처리 품목 🗑️": continue # 폐기 품목 제외
                    if isinstance(item_list, list):
                        for item_name in item_list:
                            if item_name in processed_items or item_name not in data.items: continue
                            widget_key = f"qty_{move_type}_{section}_{item_name}"
                            qty_raw = state_data.get(widget_key)
                            try: qty = int(qty_raw) if qty_raw is not None else 0
                            except (ValueError, TypeError): qty = 0

                            if qty > 0:
                                volume, weight = data.items.get(item_name, [0, 0])
                                all_items_data.append({
                                    "구분": section,
                                    "품목명": item_name,
                                    "수량": qty,
                                    "개당 부피(CBM)": volume,
                                    "개당 무게(kg)": weight,
                                    "총 부피(CBM)": round(volume * qty, 3),
                                    "총 무게(kg)": round(weight * qty, 1)
                                })
                            processed_items.add(item_name)

        df_all_items = pd.DataFrame(all_items_data)

        # 3. 비용 내역 DataFrame 생성 (최종 조정 금액 반영)
        cost_data_list = []
        calculated_sum_excel = 0
        final_total_excel = state_data.get('final_adjusted_cost', state_data.get('calculated_total_cost', 0))
        adjustment_added = False

        for item, cost, note in calculated_cost_items:
            cost_data_list.append({"항목": item, "금액": cost, "비고": note})
            calculated_sum_excel += cost

        # 조정 항목 추가 (필요시)
        adjustment_excel = final_total_excel - calculated_sum_excel
        if abs(adjustment_excel) > 0.1: # 부동소수점 오차 감안
             cost_data_list.append({"항목": "금액 조정", "금액": adjustment_excel, "비고": "최종 금액 맞춤"})
             adjustment_added = True

        # 합계 행 추가
        cost_data_list.append({"항목": "총 합계", "금액": final_total_excel, "비고": ""})
        df_costs_final = pd.DataFrame(cost_data_list)


        # --- 엑셀 파일 쓰기 및 서식 지정 ---
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_info.to_excel(writer, sheet_name='견적 정보', index=False)
            df_all_items.to_excel(writer, sheet_name='전체 품목 수량', index=False)
            df_costs_final.to_excel(writer, sheet_name='비용 내역 및 요약', index=False)

            # 워크북 및 워크시트 객체 가져오기
            workbook = writer.book
            ws_info = writer.sheets['견적 정보']
            ws_items = writer.sheets['전체 품목 수량']
            ws_costs = writer.sheets['비용 내역 및 요약']

            # 숫자 형식 지정 함수
            def apply_number_format(worksheet, col_letter, number_format):
                for cell in worksheet[col_letter]:
                    if isinstance(cell.value, (int, float)):
                        cell.number_format = number_format

            # 시트별 형식 지정
            apply_number_format(ws_info, 'B', '#,##0') # 견적 정보 시트의 일부 숫자
            # 품목 시트: 부피/무게는 소수점, 수량은 정수
            apply_number_format(ws_items, 'C', '#,##0') # 수량
            apply_number_format(ws_items, 'D', '0.000') # 개당 부피
            apply_number_format(ws_items, 'E', '0.0')   # 개당 무게
            apply_number_format(ws_items, 'F', '0.000') # 총 부피
            apply_number_format(ws_items, 'G', '0.0')   # 총 무게
            # 비용 시트: 금액
            apply_number_format(ws_costs, 'B', '#,##0') # 금액

            # 컬럼 너비 자동 조절 함수 (개선된 버전)
            def auto_adjust_column_width(worksheet):
                for col in worksheet.columns:
                    max_length = 0
                    column_letter = col[0].column_letter # 열 문자 얻기

                    # 헤더 길이 먼저 계산
                    header_cell = worksheet[f"{column_letter}1"]
                    if header_cell.value:
                        # 한글/영문/숫자 고려 (대략적인 가중치)
                        header_len_weighted = 0
                        for char in str(header_cell.value):
                            if '\uac00' <= char <= '\ud7a3': header_len_weighted += 1.8
                            else: header_len_weighted += 1.0
                        max_length = math.ceil(header_len_weighted)

                    # 각 셀 내용 길이 계산 (형식 적용된 숫자도 고려)
                    for cell in col:
                        if cell.row == 1: continue # 헤더는 위에서 계산
                        if cell.value is not None:
                            cell_str = ""
                            # 숫자이고 형식이 지정된 경우, 형식 적용된 문자열 길이 시뮬레이션 (근사치)
                            if isinstance(cell.value, (int, float)) and cell.number_format != 'General':
                                try:
                                    # 예: '#,##0' 형식 -> 천단위 쉼표 고려
                                    if '0.0' in cell.number_format: # 소수점 형식
                                        num_decimals = cell.number_format.count('0', cell.number_format.find('.'))
                                        cell_str = f"{cell.value:,.{num_decimals}f}"
                                    elif ',' in cell.number_format: # 천단위 쉼표 형식
                                        cell_str = f"{cell.value:,.0f}"
                                    else: cell_str = str(cell.value)
                                except: cell_str = str(cell.value) # 형식 변환 실패 시 기본 문자열
                            else:
                                cell_str = str(cell.value)

                            # 문자열 길이 계산 (가중치 적용)
                            current_len_weighted = 0
                            for char in cell_str:
                                if '\uac00' <= char <= '\ud7a3': current_len_weighted += 1.8
                                else: current_len_weighted += 1.0
                            max_length = max(max_length, math.ceil(current_len_weighted))

                    # 최종 너비 조정 (여백 추가, 최대/최소 너비 설정)
                    adjusted_width = max_length + 2 # 기본 여백
                    adjusted_width = max(adjusted_width, 8) # 최소 너비
                    adjusted_width = min(adjusted_width, 50) # 최대 너비
                    worksheet.column_dimensions[column_letter].width = adjusted_width

            # 각 시트에 너비 조절 적용
            auto_adjust_column_width(ws_info)
            auto_adjust_column_width(ws_items)
            auto_adjust_column_width(ws_costs)

        excel_data = output.getvalue()
        return excel_data
    except Exception as e:
        st.error(f"Excel 요약 파일 생성 중 오류 발생: {e}")
        traceback.print_exc()
        return None