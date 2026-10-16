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

    decimals = _requested_decimals(q_lower)
    if decimals is not None:
        out = _format_decimals(s, decimals)
        if out is not None:
            return out

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


_NUM_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}


def _requested_decimals(q_lower: str):
    """Số chữ số thập phân mà câu hỏi yêu cầu ('exactly two decimal places', 'rounded to 3 decimal places'...)."""
    m = re.search(r"(\w+)\s+decimal\s+place", q_lower)
    if not m:
        return None
    tok = m.group(1)
    if tok.isdigit():
        return int(tok)
    return _NUM_WORDS.get(tok)


def _as_number(text: str):
    try:
        return float(text.strip().replace(",", ""))
    except ValueError:
        return None


def _format_decimals(s: str, d: int):
    """Chỉ định dạng phần số: toàn bộ danh sách số, hoặc số cuối của dạng 'nhóm, số' (không đụng tới số trong tên nhóm)."""
    parts = [p.strip() for p in s.split(", ")] if ", " in s else [s.strip()]
    nums = [_as_number(p) for p in parts]
    if all(n is not None for n in nums):
        return ", ".join(f"{n:.{d}f}" for n in nums)
    if nums[-1] is not None and len(parts) >= 2:
        return ", ".join(parts[:-1] + [f"{nums[-1]:.{d}f}"])
    return None
