import re
from typing import Any

def format_answer(raw: Any, query: str) -> str:
    """
    Chuẩn hóa giá trị mộc theo yêu cầu format trong câu hỏi (Exact Match).
    """
    if raw is None:
        return ""

    q_lower = query.lower()

    if isinstance(raw, (list, tuple)):
        if "two integer" in q_lower or "separated by a comma" in q_lower:
            cleaned_items = []
            for x in raw:
                if "two decimal places" in q_lower:
                    try:
                        cleaned_items.append(f"{float(x):.2f}")
                    except:
                        cleaned_items.append(str(x).strip())
                else:
                    try:
                        cleaned_items.append(str(int(round(float(str(x).replace(',', ''))))))
                    except:
                        cleaned_items.append(str(x).strip())
            return ", ".join(cleaned_items)
        else:
            return ", ".join(str(x).strip() for x in raw)

    s = str(raw).strip()

    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()

    if "yes or no" in q_lower:
        if "yes" in s.lower():
            return "Yes"
        elif "no" in s.lower():
            return "No"
        return s

    if "only the last name" in q_lower:
        parts = s.replace(',', ' ').split()
        return parts[-1] if parts else s

    if "two decimal places" in q_lower:
        nums = re.findall(r'-?\d+\.?\d*', s)
        if len(nums) >= 2 and ("men, women" in q_lower or "separating the values" in q_lower):
            try:
                return f"{float(nums[0]):.2f}, {float(nums[1]):.2f}"
            except:
                pass
        try:
            return f"{float(s.replace(',', '')):.2f}"
        except:
            pass

    if "two integers" in q_lower:
        nums = re.findall(r'-?\d+', s.replace(',', ''))
        if len(nums) >= 2:
            return f"{nums[0]}, {nums[1]}"

    if "only the integer" in q_lower or "integer score" in q_lower or "final sum" in q_lower:
        s_clean = s.replace(',', '')
        nums = re.findall(r'-?\d+\.?\d*', s_clean)
        if nums:
            try:
                return str(int(round(float(nums[0]))))
            except:
                return nums[0]

    return s
