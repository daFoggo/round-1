import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

def format_answer(raw: Any, query: str) -> str:
    """
    Chuẩn hóa giá trị mộc theo yêu cầu format trong câu hỏi (Exact Match).
    """
    if raw is None:
        return ""

    q_lower = query.lower()

    if type(raw).__name__ in ("bool", "bool_"):  # kết quả so sánh -> câu hỏi Yes/No
        return "Yes" if raw else "No"

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

    # Câu hỏi không nêu số chữ số thập phân: số float có đuôi dài (3.5557715..., 134017.8888...) làm tròn half-up về 2 chữ số
    # (4 nếu |x| < 1); số nguyên và số đã gọn được giữ nguyên.
    num = _as_number(s)
    if num is not None and not float(num).is_integer() and "." in s and len(s.split(".")[-1]) > 4:
        return _fixed(num, 2 if abs(num) >= 1 else 4)

    return s


_NUM_WORDS = {
    # en
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    # vi
    "không": 0, "một": 1, "hai": 2, "ba": 3, "bốn": 4, "năm": 5,
    # fr / es / de
    "zéro": 0, "une": 1, "un": 1, "uno": 1, "deux": 2, "dos": 2, "trois": 3, "tres": 3, "quatre": 4, "cuatro": 4,
    "cinq": 5, "cinco": 5, "eine": 1, "einer": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5,
    # ko / zh / ja
    "첫째": 1, "둘째": 2, "셋째": 3, "넷째": 4, "다섯째": 5, "一": 1, "二": 2, "两": 2, "兩": 2, "三": 3, "四": 4, "五": 5,
}

# Mỗi mẫu bắt một từ/chữ số đứng trước (hoặc sau) cụm 'chữ số thập phân' của từng ngôn ngữ
_DECIMAL_PATTERNS = [
    r"(\w+)\s+decimal\s+place",                       # en
    r"(\w+)\s+chữ\s+số\s+thập\s+phân",                # vi
    r"(\w+)\s+décimales?",                            # fr
    r"(\w+)\s+(?:posiciones\s+|lugares\s+)?decimal(?:es)?\b",  # es
    r"(\w+)\s+nachkommastellen?",                     # de
    r"소수점\s*(\w+?)\s*자리",                          # ko
    r"小数点(?:后|後)?\s*(\w)\s*位",                    # zh
    r"保留\s*(\w)\s*位小数",                           # zh
    r"小数点第\s*(\w)\s*位",                           # ja
]


def _requested_decimals(q_lower: str):
    """Số chữ số thập phân mà câu hỏi yêu cầu ('exactly two decimal places', 'một chữ số thập phân', '소수점 둘째 자리'...)."""
    for pattern in _DECIMAL_PATTERNS:
        m = re.search(pattern, q_lower)
        if not m:
            continue
        tok = m.group(1)
        if tok.isdigit():
            return int(tok)
        if tok in _NUM_WORDS:
            return _NUM_WORDS[tok]
    return None


def _as_number(text: str):
    try:
        return float(text.strip().replace(",", ""))
    except ValueError:
        return None


def _fixed(n: float, d: int) -> str:
    """Làm tròn half-up (như Excel/làm tròn tay) thay vì làm tròn nhị phân của float: 97.725 -> 97.73, 4.125 -> 4.13.
    Làm tròn trước về 9 chữ số để loại nhiễu dấu phẩy động (97.72499999999999 vẫn là 97.725)."""
    try:
        q = Decimal(1).scaleb(-d)
        return str(Decimal(repr(round(n, 9))).quantize(q, rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError):
        return f"{n:.{d}f}"


def _format_decimals(s: str, d: int):
    """Chỉ định dạng phần số: toàn bộ danh sách số, hoặc số cuối của dạng 'nhóm, số' (không đụng tới số trong tên nhóm)."""
    parts = [p.strip() for p in s.split(", ")] if ", " in s else [s.strip()]
    nums = [_as_number(p) for p in parts]
    if all(n is not None for n in nums):
        return ", ".join(_fixed(n, d) for n in nums)
    if nums[-1] is not None and len(parts) >= 2:
        return ", ".join(parts[:-1] + [_fixed(nums[-1], d)])
    return None
