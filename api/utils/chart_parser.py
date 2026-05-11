# api/utils/chart_parser.py
import re
import json

def extract_valid_json(text: str) -> str:
    start_idx = text.find('{')
    first_bracket = text.find('[')
    
    is_object = False
    if start_idx != -1 and (first_bracket == -1 or start_idx < first_bracket):
        is_object = True
    elif first_bracket != -1:
        start_idx = first_bracket
        is_object = False
    else:
        return text

    open_tokens = 0
    in_string = False
    escape_next = False
    
    for i in range(start_idx, len(text)):
        char = text[i]
        if escape_next:
            escape_next = False
            continue
        if char == '\\':
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            continue
            
        if not in_string:
            if is_object:
                if char == '{': open_tokens += 1
                elif char == '}': 
                    open_tokens -= 1
                    if open_tokens == 0: return text[start_idx:i+1]
            else:
                if char == '[': open_tokens += 1
                elif char == ']': 
                    open_tokens -= 1
                    if open_tokens == 0: return text[start_idx:i+1]
    return text

def extract_chart_metadata(content: str) -> tuple[str, dict | None]:
    pattern = r"<CHART_JSON>(.*?)</CHART_JSON>"
    match = re.search(pattern, content, flags=re.DOTALL)
    
    if match:
        json_str = match.group(1).strip()
        if json_str.startswith("```json"):
            json_str = json_str.removeprefix("```json").removesuffix("```").strip()
        elif json_str.startswith("```"):
            json_str = json_str.removeprefix("```").removesuffix("```").strip()

        json_str = extract_valid_json(json_str)

        try:
            chart_data = json.loads(json_str)
            
            data_array = chart_data.get("data", [])
            if not isinstance(data_array, list):
                data_array = []
                
            filtered_data = []
            extracted_layout = chart_data.get("layout", {})

            for item in data_array:
                if isinstance(item, dict) and item.get("type") == "layout":
                    if not extracted_layout:
                        extracted_layout = {k: v for k, v in item.items() if k != "type"}
                else:
                    filtered_data.append(item)
            
            clean_text = re.sub(pattern, "", content, flags=re.DOTALL).strip()
            
            metadata = {
                "chart": {
                    "type": "plotly",
                    "data": filtered_data,
                    "layout": extracted_layout
                }
            }
            return clean_text, metadata
        except json.JSONDecodeError as e:
            print(f"Lỗi parse JSON biểu đồ: {e}")
            pass
            
    return content, None