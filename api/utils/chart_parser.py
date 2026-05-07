# api/utils/chart_parser.py
import re
import json

def extract_chart_metadata(content: str) -> tuple[str, dict | None]:
    pattern = r"<CHART_JSON>(.*?)</CHART_JSON>"
    match = re.search(pattern, content, flags=re.DOTALL)
    
    if match:
        json_str = match.group(1).strip()
        try:
            chart_data = json.loads(json_str)
            
            clean_text = re.sub(pattern, "", content, flags=re.DOTALL).strip()
            
            metadata = {
                "chart": {
                    "type": "plotly",
                    "data": chart_data.get("data", []),
                    "layout": chart_data.get("layout", {})
                }
            }
            return clean_text, metadata
        except json.JSONDecodeError as e:
            print(f"Lỗi parse JSON biểu đồ: {e}")
            pass
            
    return content, None