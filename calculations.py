# calculations.py (VAT, 카드 수수료, 기본 여성 인원 제외 로직 수정)
import data
import math

# --- 이사짐 부피/무게 계산 ---
def calculate_total_volume_weight(state_data, move_type):
    total_volume = 0.0
    total_weight = 0.0
    if not hasattr(data, 'item_definitions') or not data.item_definitions:
        return 0.0, 0.0
    item_defs = data.item_definitions.get(move_type, {})
    processed_items = set() 
    if isinstance(item_defs, dict):
        for section, item_list in item_defs.items():
            if section == "폐기 처리 품목 🗑️": continue
            if isinstance(item_list, list):
                for item_name in item_list:
                    if item_name in processed_items or not hasattr(data, 'items') or not data.items or item_name not in data.items:
                        continue
                    widget_key = f"qty_{move_type}_{section}_{item_name}"
                    qty_raw = state_data.get(widget_key)
                    qty = int(qty_raw) if qty_raw is not None else 0
                    if qty > 0:
                        try:
                            volume, weight = data.items[item_name] 
                            total_volume += volume * qty
                            total_weight += weight * qty
                        except KeyError: pass
                        except Exception: pass 
                    processed_items.add(item_name)
    return round(total_volume, 2), round(total_weight, 2)

# --- 차량 추천 ---
def recommend_vehicle(total_volume, total_weight, current_move_type):
    recommended_vehicle, remaining_space_percent = None, 0.0
    if not hasattr(data, 'vehicle_specs') or not data.vehicle_specs: return None, 0
    priced_trucks_for_move_type = list(data.vehicle_prices.get(current_move_type, {}).keys()) if hasattr(data, 'vehicle_prices') and data.vehicle_prices else []
    if not priced_trucks_for_move_type: return None, 0
    relevant_vehicle_specs = {truck: specs for truck, specs in data.vehicle_specs.items() if truck in priced_trucks_for_move_type}
    if not relevant_vehicle_specs: return None, 0
    sorted_trucks = sorted(relevant_vehicle_specs.items(), key=lambda item: item[1].get('capacity', 0))
    if total_volume <= 0 and total_weight <= 0: return None, 0 
    loading_efficiency = getattr(data, 'LOADING_EFFICIENCY', 1.0) 
    for truck_name, specs in sorted_trucks:
        usable_capacity, usable_weight = specs.get('capacity', 0) * loading_efficiency, specs.get('weight_capacity', 0)
        if usable_capacity > 0 and total_volume <= usable_capacity and total_weight <= usable_weight:
            recommended_vehicle, remaining_space_percent = truck_name, (1 - (total_volume / usable_capacity)) * 100 if usable_capacity > 0 else 0
            break 
    if recommended_vehicle: return recommended_vehicle, round(remaining_space_percent, 1)
    elif (total_volume > 0 or total_weight > 0) and sorted_trucks: return f"{sorted_trucks[-1][0]} 용량 초과", 0 
    else: return None, 0

# --- 층수 숫자 추출 ---
def get_floor_num(floor_str):
    try:
        if floor_str is None: return 0
        cleaned = str(floor_str).strip()
        if not cleaned: return 0 
        num_part = ''.join(filter(str.isdigit, cleaned[1:] if cleaned.startswith('-') else cleaned))
        return -int(num_part) if cleaned.startswith('-') and num_part else (int(num_part) if num_part else 0)
    except: return 0 

# --- 사다리차 비용 계산 ---
def get_ladder_cost(floor_num, vehicle_name):
    cost, note = 0, ""
    if floor_num < 2: return 0, "1층 이하"
    floor_range_key = next((rng_str for (min_f, max_f), rng_str in getattr(data, 'ladder_price_floor_ranges', {}).items() if min_f <= floor_num <= max_f), None)
    if not floor_range_key: return 0, f"{floor_num}층 해당 가격 없음"
    vehicle_spec = getattr(data, 'vehicle_specs', {}).get(vehicle_name)
    if not vehicle_spec or 'weight_capacity' not in vehicle_spec: return 0, "선택 차량 정보 없음"
    vehicle_ton_num = vehicle_spec['weight_capacity'] / 1000.0
    tonnage_key = next((data.ladder_tonnage_map[ton_n] for ton_n in sorted(getattr(data, 'ladder_tonnage_map', {}).keys(), reverse=True) if vehicle_ton_num >= ton_n), getattr(data, 'default_ladder_size', None))
    if not tonnage_key: return 0, "사다리차 톤수 기준 없음"
    try:
        floor_prices = getattr(data, 'ladder_prices', {}).get(floor_range_key, {})
        cost = floor_prices.get(tonnage_key, 0)
        if cost > 0: note = f"{floor_range_key}, {tonnage_key} 기준"
        else:
            def_size = getattr(data, 'default_ladder_size', None)
            if def_size and def_size != tonnage_key:
                 cost = floor_prices.get(def_size, 0)
                 note = f"{floor_range_key}, 기본({def_size}) 적용" if cost > 0 else f"{floor_range_key}, {tonnage_key}(기본 {def_size}) 가격 없음"
            else: note = f"{floor_range_key}, {tonnage_key} 가격 정보 없음"
    except Exception as e: note, cost = f"가격 조회 오류: {e}", 0
    return cost, note

# --- 총 이사 비용 계산 ---
def calculate_total_moving_cost(state_data):
    cost_before_add_charges = 0 
    cost_items = [] 
    personnel_info = {} 

    current_move_type = state_data.get('base_move_type')
    selected_vehicle = state_data.get('final_selected_vehicle') 
    is_storage, has_via_point = state_data.get('is_storage_move', False), state_data.get('has_via_point', False)

    if not selected_vehicle:
        return 0, [("오류", 0, "차량 선택 필요")], {}

    base_price, base_men, base_women = 0, 0, 0
    vehicle_prices_options = getattr(data, 'vehicle_prices', {}).get(current_move_type, {})
    if selected_vehicle in vehicle_prices_options:
        v_info = vehicle_prices_options[selected_vehicle]
        base_price, base_men, base_women = v_info.get('price', 0), v_info.get('men', 0), v_info.get('housewife', 0)
        actual_base_price = base_price * 2 if is_storage else base_price
        cost_items.append(("기본 운임", actual_base_price, f"{selected_vehicle} 기준" + (" (보관 x2)" if is_storage else "")))
        cost_before_add_charges += actual_base_price
    else:
        return 0, [("오류", 0, f"차량({selected_vehicle}) 가격 정보 없음")], {}

    for loc_type, floor_key, method_key, sky_hours_key in [
        ("출발지", 'from_floor', 'from_method', 'sky_hours_from'),
        ("도착지", 'to_floor', 'to_method', 'sky_hours_final')]:
        floor_num, method = get_floor_num(state_data.get(floor_key)), state_data.get(method_key)
        if method == "사다리차 🪜":
            l_cost, l_note = get_ladder_cost(floor_num, selected_vehicle)
            if l_cost > 0 or (l_cost == 0 and l_note != "1층 이하"): cost_items.append((f"{loc_type} 사다리차", l_cost, l_note)); cost_before_add_charges += l_cost
        elif method == "스카이 🏗️":
            sky_h = max(1, int(state_data.get(sky_hours_key, 1) or 1))
            s_base, s_extra = getattr(data, 'SKY_BASE_PRICE',0), getattr(data, 'SKY_EXTRA_HOUR_PRICE',0)
            s_cost = s_base + s_extra * (sky_h - 1)
            s_note = f"{loc_type}({sky_h}h): 기본 {s_base:,.0f}" + (f" + 추가 {s_extra*(sky_h-1):,.0f}" if sky_h > 1 else "")
            cost_items.append((f"{loc_type} 스카이 장비", s_cost, s_note)); cost_before_add_charges += s_cost
    
    add_m, add_w = int(state_data.get('add_men',0) or 0), int(state_data.get('add_women',0) or 0)
    add_person_cost_unit = getattr(data, 'ADDITIONAL_PERSON_COST', 0)
    
    actual_removed_hw = False
    if current_move_type == "가정 이사 🏠" and state_data.get('remove_base_housewife', False) and base_women > 0:
        discount = -add_person_cost_unit * base_women
        cost_items.append(("기본 여성 인원 제외 할인", discount, f"여 {base_women}명 제외"))
        cost_before_add_charges += discount
        actual_removed_hw = True
        
    manual_added_total_cost = (add_m + add_w) * add_person_cost_unit
    if manual_added_total_cost > 0:
        cost_items.append(("추가 인력", manual_added_total_cost, f"남{add_m}, 여{add_w}"))
        cost_before_add_charges += manual_added_total_cost

    adj_amount = int(state_data.get('adjustment_amount',0) or 0)
    if adj_amount != 0: cost_items.append((f"{'할증' if adj_amount > 0 else '할인'} 조정 금액", adj_amount, "수동입력")); cost_before_add_charges += adj_amount

    if is_storage:
        s_dur, s_type = max(1, int(state_data.get('storage_duration',1) or 1)), state_data.get('storage_type', getattr(data,'DEFAULT_STORAGE_TYPE',"정보없음"))
        s_daily_rate = getattr(data,'STORAGE_RATES_PER_DAY',{}).get(s_type,0)
        if s_daily_rate > 0:
            s_base_cost, s_elec_surcharge = s_daily_rate * s_dur, 0
            s_note = f"{s_type}, {s_dur}일"
            if state_data.get('storage_use_electricity', False):
                s_elec_surcharge = getattr(data,'STORAGE_ELECTRICITY_SURCHARGE_PER_DAY',3000) * s_dur
                s_note += ", 전기사용"
            s_final_cost = s_base_cost + s_elec_surcharge
            cost_items.append(("보관료", s_final_cost, s_note)); cost_before_add_charges += s_final_cost
        else: cost_items.append(("오류", 0, f"보관유형({s_type}) 요금정보 없음"))

    if state_data.get('apply_long_distance', False):
        ld_sel = state_data.get('long_distance_selector')
        if ld_sel and ld_sel != "선택 안 함":
            ld_cost = getattr(data,'long_distance_prices',{}).get(ld_sel,0)
            if ld_cost > 0: cost_items.append(("장거리 운송료", ld_cost, ld_sel)); cost_before_add_charges += ld_cost
            
    if state_data.get('has_waste_check', False):
        w_tons = max(0.5, float(state_data.get('waste_tons_input',0.5) or 0.5))
        w_cost_ton = getattr(data,'WASTE_DISPOSAL_COST_PER_TON',0)
        w_cost = w_cost_ton * w_tons
        cost_items.append(("폐기물 처리", w_cost, f"{w_tons:.1f}톤 기준")); cost_before_add_charges += w_cost

    dt_surcharge, dt_notes = 0, []
    dt_opts, dt_prices = ["이사많은날 🏠","손없는날 ✋","월말 📅","공휴일 🎉","금요일 📅"], getattr(data,'special_day_prices',{})
    for i, opt in enumerate(dt_opts):
        if state_data.get(f"date_opt_{i}_widget", False):
            s = dt_prices.get(opt,0); 
            if s > 0: dt_surcharge += s; dt_notes.append(opt.split(" ")[0])
    if dt_surcharge > 0: cost_items.append(("날짜 할증", dt_surcharge, ", ".join(dt_notes))); cost_before_add_charges += dt_surcharge
    
    reg_ladder_surcharge = int(state_data.get('regional_ladder_surcharge',0) or 0)
    if reg_ladder_surcharge > 0: cost_items.append(("지방 사다리 추가요금", reg_ladder_surcharge, "수동입력")); cost_before_add_charges += reg_ladder_surcharge
    
    if has_via_point:
        via_s = int(state_data.get('via_point_surcharge',0) or 0)
        if via_s > 0: cost_items.append(("경유지 추가요금", via_s, "수동입력")); cost_before_add_charges += via_s

    # --- VAT 및 카드 수수료 계산 ---
    current_total_cost = cost_before_add_charges # 순수 비용 합계로 시작

    if state_data.get('issue_tax_invoice', False):
        vat = math.ceil(cost_before_add_charges * 0.1) # 원금 기준 VAT
        cost_items.append(("부가세 (10%)", vat, "세금계산서 발행 요청"))
        current_total_cost += vat
    
    if state_data.get('card_payment', False):
        # 카드수수료는 (원금 + VAT가 이미 적용된) 금액에 대해 부과
        card_fee = math.ceil(current_total_cost * 0.13) 
        cost_items.append(("카드결제 수수료 (13%)", card_fee, "카드 결제 요청"))
        current_total_cost += card_fee
    # --- VAT 및 카드 수수료 계산 완료 ---

    final_men = base_men + add_m
    final_women = add_w if actual_removed_hw else (base_women + add_w)

    personnel_info = {
        'base_men': base_men, 'base_women': base_women,
        'manual_added_men': add_m, 'manual_added_women': add_w,
        'final_men': final_men, 'final_women': final_women,
        'removed_base_housewife': actual_removed_hw 
    }
    return max(0, round(current_total_cost)), cost_items, personnel_info