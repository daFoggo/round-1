"""Entity linking tất định giữa câu hỏi và bảng (không gọi LLM).

Ý tưởng lấy từ các hệ thống Table-QA/Text-to-SQL mạnh (CHESS: entity retrieval; TableZoomer: column selection +
entity linking): thay vì để model tự đoán chuỗi con để lọc dòng, ta tìm *các nhãn dòng/cột có thật trong bảng* xuất hiện
trong câu hỏi và liệt kê đúng `Row_Path` / tên cột tương ứng. Cách làm đảo ngược (duyệt nhãn của bảng, kiểm tra có nằm
trong câu hỏi không) hoạt động cho mọi ngôn ngữ, kể cả chữ Hán/Hàn/Nhật không có khoảng trắng.
"""
import re
from typing import Dict, List, Tuple

import pandas as pd

_CJK = re.compile(r'[぀-ヿ㐀-䶿一-鿿가-힯]')
_STOP = {
    'the', 'and', 'for', 'was', 'were', 'what', 'which', 'how', 'many', 'much', 'with', 'that', 'than', 'from', 'only',
    'answer', 'number', 'does', 'did', 'are', 'has', 'have', 'all', 'any', 'between', 'each', 'per', 'its', 'their',
}


def _norm(text: str) -> str:
    return ' '.join(re.findall(r'\w+', str(text).lower()))


def _min_len(norm: str) -> int:
    return 2 if _CJK.search(norm) else 3


def _found_in_query(label_norm: str, query_norm: str, query_tokens: set) -> int:
    """2 = cụm nhãn xuất hiện nguyên vẹn trong câu hỏi; 1 = mọi từ của nhãn (>=2 từ) đều có trong câu hỏi; 0 = không."""
    if not label_norm or len(label_norm) < _min_len(label_norm):
        return 0
    if label_norm.isdigit() and len(label_norm) < 4:
        return 0
    if _CJK.search(label_norm):
        return 2 if label_norm in query_norm else 0
    if f' {label_norm} ' in f' {query_norm} ':
        return 2
    toks = [t for t in label_norm.split() if t not in _STOP]
    if len(toks) >= 2 and all(t in query_tokens for t in toks):
        return 1
    return 0


def link_entities(query: str, dfs: Dict[str, pd.DataFrame], max_labels: int = 10, per_label: int = 6,
                  max_cols: int = 8) -> str:
    """Trả về khối văn bản liệt kê nhãn dòng/cột của bảng xuất hiện trong câu hỏi ('' nếu không có)."""
    query_norm = _norm(query)
    query_tokens = set(query_norm.split())
    blocks: List[str] = []

    for name, df in dfs.items():
        lines: List[str] = []

        # --- Nhãn dòng: đoạn cuối của Row_Path là nhãn riêng của dòng ---
        by_label: Dict[str, Tuple[int, List[str]]] = {}
        for rp in df['Row_Path'].dropna().astype(str).unique():
            label = rp.split(' | ')[-1]
            ln = _norm(label)
            score = _found_in_query(ln, query_norm, query_tokens)
            if score:
                cur = by_label.setdefault(label, (score, []))
                cur[1].append(rp)
        # nhãn dài/cụ thể trước; bỏ nhãn chỉ là chuỗi con của một nhãn dài hơn cũng đã khớp (vd. 'Services' vs 'Medical care services' khi cả hai khớp)
        ranked = sorted(by_label.items(), key=lambda kv: (-kv[1][0], -len(kv[0])))[:max_labels]
        for label, (score, paths) in ranked:
            kind = 'exact phrase' if score == 2 else 'all words'
            shown = '; '.join(f"Row_Path={p!r}" for p in paths[:per_label])
            more = f" (+{len(paths) - per_label} more)" if len(paths) > per_label else ''
            lines.append(f"  - row label {label!r} [{kind}, {len(paths)} row(s)]: {shown}{more}")

        # --- Nhóm cha: các đoạn không phải đoạn cuối của Row_Path (vd. 'White', 'Women' là nhóm chứa nhiều dòng) ---
        parent_rows: Dict[str, int] = {}
        for rp in df['Row_Path'].dropna().astype(str):
            for seg in rp.split(' | ')[:-1]:
                if seg not in by_label:
                    parent_rows[seg] = parent_rows.get(seg, 0) + 1
        parents = [(seg, cnt) for seg, cnt in parent_rows.items()
                   if _found_in_query(_norm(seg), query_norm, query_tokens) == 2]
        parents.sort(key=lambda t: -len(t[0]))
        for seg, cnt in parents[:max_labels]:
            lines.append(f"  - group label {seg!r} is a parent segment of {cnt} row(s) "
                         f"(rows whose Row_Path contains it as a segment, e.g. Row_Path starting with {seg!r} | ...)")

        # --- Tên cột: các đoạn của tên cột xuất hiện trong câu hỏi ---
        col_hits: List[Tuple[int, str, List[str]]] = []
        for col in df.columns[3:]:
            parts = [p.strip() for p in str(col).split(' | ')]
            hit = [p for p in parts if _found_in_query(_norm(p), query_norm, query_tokens) == 2]
            if hit:
                col_hits.append((len(hit), str(col), hit))
        col_hits.sort(key=lambda t: (-t[0], t[1]))
        for n, col, hit in col_hits[:max_cols]:
            lines.append(f"  - column {col!r} (matches: {', '.join(hit)})")

        if lines:
            blocks.append(f"Table '{name}':\n" + '\n'.join(lines))

    if not blocks:
        return ''
    return ("ENTITY LINKS (deterministic: labels that really exist in the tables and appear in the question; "
            "prefer these exact strings over loose substring filters):\n" + '\n'.join(blocks))
