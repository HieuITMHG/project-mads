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
    
    # Auto-fix missing closing brackets
    if open_tokens > 0:
        if is_object:
            return text[start_idx:] + ('}' * open_tokens)
        else:
            return text[start_idx:] + (']' * open_tokens)
            
    return text

text = '{"data":[{"type":"pie"}],"layout":{"template":{}'

extracted = extract_valid_json(text)
print("EXTRACTED:", extracted)
try:
    print(json.loads(extracted))
except Exception as e:
    print("ERROR:", e)
