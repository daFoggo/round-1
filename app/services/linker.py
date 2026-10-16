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
    'answer', 'number', 'does', 'doe', 'did', 'are', 'has', 'have', 'all', 'any', 'between', 'each', 'per', 'its', 'their',
}


def _singular(tok: str) -> str:
    """Bỏ 's' số nhiều đơn giản để 'estimates' khớp cột 'Estimate' (áp dụng đối xứng cho câu hỏi và nhãn bảng)."""
    return tok[:-1] if len(tok) > 3 and tok.endswith('s') and not tok.endswith(('ss', 'us', 'is')) else tok


def _norm(text: str) -> str:
    return ' '.join(_singular(t) for t in re.findall(r'\w+', str(text).lower()))


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


_AVG_RE = re.compile(r'\b(average|mean)\b', re.IGNORECASE)
_ALL_RE = re.compile(r'\b(all|every|across|each)\b', re.IGNORECASE)
_EXCLUDE_RE = re.compile(r'\b(exclud\w*|except|without|individual|sub-?categor\w*|subgroup\w*|leaf|only the (sub|individual|component))', re.IGNORECASE)


def _numeric_columns(df: pd.DataFrame) -> List[str]:
    """Các cột dữ liệu số của bảng (bỏ cột số thứ tự / mức thụt lề)."""
    cols = []
    for col in df.columns[3:]:
        name = str(col).lower()
        if name.startswith(('indent', 'no ')) or name == 'no':
            continue
        if pd.api.types.is_numeric_dtype(df[col]) and df[col].notna().any():
            cols.append(str(col))
    return cols


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
        parents = []
        for seg, cnt in parent_rows.items():
            score = _found_in_query(_norm(seg), query_norm, query_tokens)
            if score:
                parents.append((score, seg, cnt))
        parents.sort(key=lambda t: (-t[0], -len(t[1])))
        for score, seg, cnt in parents[:max_labels]:
            kind = 'exact phrase' if score == 2 else 'all words'
            lines.append(f"  - group label {seg!r} [{kind}] is a parent segment of {cnt} row(s) "
                         f"(Row_Path starts with {seg!r} | ...)")

        # --- Giao nhóm cha với nhãn dòng: Row_Path đầy đủ, chính xác (tránh model tự ghép chuỗi rồi dùng regex) ---
        if ranked and parents:
            combined = []
            for label, (score, paths) in ranked:
                for rp in paths:
                    segs = rp.split(' | ')[:-1]
                    hit = [seg for _, seg, _ in parents if seg in segs]
                    if hit:
                        combined.append((rp, hit, label))
            for rp, hit, label in combined[:per_label]:
                lines.append(f"  - BEST ROW (group {', '.join(map(repr, hit))} + label {label!r}): Row_Path=={rp!r}")

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

        if lines and any('row label' in ln for ln in lines) and _AVG_RE.search(query) and _ALL_RE.search(query)                 and not _EXCLUDE_RE.search(query):
            num_cols = _numeric_columns(df)
            if num_cols:
                lines.append(f"  - AVERAGE ACROSS ALL: official convention = unweighted mean over ALL {len(num_cols)} "
                             f"numeric columns of the row (subtotal/Total columns included): {num_cols}")

        if lines:
            blocks.append(f"Table '{name}':\n" + '\n'.join(lines))

    if not blocks:
        return ''
    return ("ENTITY LINKS (deterministic: labels that really exist in the tables and appear in the question; "
            "prefer these exact strings over loose substring filters):\n" + '\n'.join(blocks))
