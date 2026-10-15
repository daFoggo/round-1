import os
import re
from datetime import datetime
import openpyxl
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional

def clean_text(val: Any) -> str:
    """Làm sạch chuỗi, xóa footnotes như (1), 2/, khoảng trắng thừa."""
    if val is None:
        return ""
    s = str(val).strip().replace('\r', ' ').replace('\n', ' ')
    s = re.sub(r'\(\d+\)', '', s)
    s = re.sub(r'\b\d+/(?=\s|$)', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def is_num_or_date(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, (int, float, datetime)):
        return True
    s = str(v).strip().replace(',', '')
    if not s or s == '-':
        return False
    try:
        float(s)
        return True
    except ValueError:
        return False

def is_note_row(c1_val: str) -> bool:
    """Nhận diện các dòng chú thích cuối bảng (Footnotes, Notes)."""
    c1_low = c1_val.lower().strip()
    return (
        c1_low.startswith('footnote') or
        c1_low.startswith('note:') or
        bool(re.match(r'^\(\d+\)\s*', c1_val)) or
        bool(re.match(r'^\d+/\s*', c1_val))
    )

def detect_table_ranges(ws: openpyxl.worksheet.worksheet.Worksheet, grid: Dict[Tuple[int, int], Any], max_row: int, max_col: int) -> List[Tuple[int, int, str]]:
    """
    Phát hiện các khối bảng độc lập trên cùng một worksheet (ví dụ Fiscal years vs Calendar years).
    Trả về danh sách [(start_row, end_row, table_title), ...].
    """
    row_info = []
    for r in range(1, max_row + 1):
        vals = [grid.get((r, c)) for c in range(1, max_col + 1)]
        non_empty = [v for v in vals if v is not None and str(v).strip() != '']
        nums = sum(1 for v in non_empty if isinstance(v, (int, float)))
        years = sum(1 for v in non_empty if isinstance(v, int) and 1900 <= v <= 2100)
        c1 = str(vals[0]).strip() if vals and vals[0] is not None else ''
        is_note = is_note_row(c1)
        row_info.append({
            'r': r,
            'non_empty': len(non_empty),
            'nums': nums,
            'years': years,
            'is_note': is_note,
            'c1': c1,
            'first_val': clean_text(non_empty[0]) if non_empty else ''
        })

    tables = []
    curr_start = 1
    had_data = False
    table_title = row_info[0]['first_val'] or "Table_1"

    for idx, info in enumerate(row_info):
        r = info['r']
        if info['is_note']:
            continue
        if info['nums'] >= 2 and info['years'] < info['nums']:
            had_data = True
        elif had_data:
            # Phát hiện nếu có bảng mới xuất hiện sau một khối dữ liệu
            if info['years'] >= 2 or (info['non_empty'] >= 2 and info['nums'] == 0 and not info['is_note']):
                next_has_years_or_data = False
                for look in row_info[idx+1:idx+4]:
                    if look['years'] >= 2 or look['nums'] >= 2:
                        next_has_years_or_data = True
                        break
                if next_has_years_or_data:
                    tables.append((curr_start, r - 1, table_title))
                    curr_start = r
                    table_title = info['first_val'] or f"Table_{len(tables)+1}"
                    had_data = False

    tables.append((curr_start, max_row, table_title))
    return tables

def parse_table_block(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    grid: Dict[Tuple[int, int], Any],
    start_row: int,
    end_row: int,
    max_col: int
) -> pd.DataFrame:
    """Parse một khối bảng cụ thể (từ start_row đến end_row) thành DataFrame phẳng."""
    # 1. Tìm data_start_row trong khối
    data_start = None
    for r in range(start_row, end_row + 1):
        c1 = grid.get((r, 1))
        if isinstance(c1, int) and c1 == 1:
            data_start = r
            break
        nums = sum(1 for c in range(2, max_col + 1) if is_num_or_date(grid.get((r, c))))
        if nums >= 2:
            r_next_strings = sum(1 for c in range(2, max_col + 1) if isinstance(grid.get((r+1, c)), str) and len(str(grid.get((r+1, c)))) > 3 and not str(grid.get((r+1, c))).replace(',','').replace('.','').isdigit())
            if r_next_strings >= 2:
                continue
            data_start = r
            break

    if data_start is None:
        data_start = min(start_row + 1, end_row)

    # 2. Tìm header_end_row
    header_end = data_start - 1
    while header_end >= start_row:
        non_empty = [c for c in range(1, max_col + 1) if grid.get((header_end, c)) is not None and str(grid.get((header_end, c))).strip() != '']
        if len(non_empty) == 0 or (len(non_empty) == 1 and non_empty[0] == 1):
            header_end -= 1
        else:
            break

    if header_end < start_row:
        header_end = start_row

    # 3. Tìm header_start_row
    header_start = start_row
    for r in range(start_row, header_end + 1):
        raw_non_empty = [c for c in range(1, max_col + 1) if ws.cell(r, c).value is not None and str(ws.cell(r, c).value).strip() != '']
        if len(raw_non_empty) <= 1 and max_col > 2:
            txt = str(ws.cell(r, raw_non_empty[0]).value).strip().upper() if raw_non_empty else ''
            if any(k in txt for k in ['HOUSEHOLD DATA', 'ANNUAL AVERAGES', 'THOUSANDS', 'TABLE']) or len(txt) > 35:
                continue
        if len(raw_non_empty) == 0:
            continue
        header_start = r
        break

    # 4. Xây dựng Header Path cho từng cột
    col_names = []
    for c in range(1, max_col + 1):
        parts = []
        for r in range(header_start, header_end + 1):
            val = clean_text(grid.get((r, c)))
            if val and (not parts or parts[-1] != val):
                parts.append(val)
        col_names.append(" | ".join(parts) if parts else f"Col_{c}")

    seen_cols = {}
    unique_col_names = []
    for c_idx, name in enumerate(col_names):
        name = name.strip() or f"Column_{c_idx+1}"
        if name in seen_cols:
            seen_cols[name] += 1
            unique_col_names.append(f"{name}_{seen_cols[name]}")
        else:
            seen_cols[name] = 1
            unique_col_names.append(name)

    # Kiểm tra xem Cột 1 có phải là Indent Level (như p4_t03) không
    c1_header = unique_col_names[0].lower() if unique_col_names else ""
    is_indent_col = 'indent' in c1_header or any(
        isinstance(grid.get((r, 1)), int) and grid.get((r, 1)) in [0, 1, 2, 3, 4]
        for r in range(data_start, min(data_start + 5, end_row + 1))
    )

    label_col_idx = 2 if is_indent_col and max_col >= 2 else 1

    # 5. Xây dựng Row_Path phân cấp
    data_rows = []
    major_section = ""
    sub_section = ""
    indent_stack: Dict[int, str] = {}

    for r in range(header_end + 1, data_start):
        s_val = clean_text(grid.get((r, label_col_idx)))
        if s_val and not is_note_row(s_val):
            major_section = s_val

    for r in range(data_start, end_row + 1):
        row_raw = [grid.get((r, c)) for c in range(1, max_col + 1)]
        if all(v is None or str(v).strip() == '' for v in row_raw):
            continue

        raw_label = clean_text(row_raw[label_col_idx - 1])
        if is_note_row(raw_label):
            continue

        other_vals = row_raw[label_col_idx:]
        num_count = sum(1 for v in other_vals if is_num_or_date(v))

        # Trường hợp 1: Dòng thuần tiêu đề nhóm chính (nums == 0)
        if raw_label != "" and num_count == 0:
            major_section = raw_label
            sub_section = ""
            continue

        # Trường hợp 2: Có cột Indent Level (cây phân cấp theo mức thụt lề số)
        if is_indent_col:
            lvl_val = row_raw[0]
            try:
                lvl = int(lvl_val) if lvl_val is not None else 0
            except (ValueError, TypeError):
                lvl = 0
            indent_stack[lvl] = raw_label
            indent_stack = {k: v for k, v in indent_stack.items() if k <= lvl}
            row_path = " | ".join(indent_stack[k] for k in sorted(indent_stack.keys()))
            current_sec = indent_stack.get(0, major_section)
        else:
            # Group parent detection (BLS demographics + general hierarchical stubs):
            is_group_parent = (
                bool(re.search(r'(Total|Men|Women|Both sexes).*?,\s*\d+\s*years and over', raw_label, re.IGNORECASE)) or
                any(raw_label.lower().startswith(race) for race in ['white', 'black', 'asian', 'hispanic']) or
                raw_label.endswith(':') or
                any(raw_label.lower().startswith(kw) for kw in ['region:', 'sector:', 'department:', 'division:'])
            )

            if is_group_parent:
                sub_section = raw_label
                path_parts = [p for p in [major_section, sub_section] if p]
                row_path = " | ".join(path_parts)
            else:
                path_parts = [p for p in [major_section, sub_section, raw_label] if p]
                row_path = " | ".join(path_parts)
            current_sec = major_section

        # Làm sạch kiểu dữ liệu các ô
        cleaned_row = []
        for val in row_raw:
            if val is None or str(val).strip() in ['', '-']:
                cleaned_row.append(None)
            elif isinstance(val, (int, float, datetime)):
                cleaned_row.append(val)
            else:
                s = str(val).strip().replace(',', '')
                try:
                    if '.' in s:
                        cleaned_row.append(float(s))
                    else:
                        cleaned_row.append(int(s))
                except ValueError:
                    cleaned_row.append(val)

        data_rows.append([row_path, current_sec, sub_section] + cleaned_row)

    final_cols = ["Row_Path", "Section", "Sub_Section"] + unique_col_names
    df = pd.DataFrame(data_rows, columns=final_cols)
    return df

def parse_workbook(file_path: str) -> Dict[str, pd.DataFrame]:
    """Parse toàn bộ workbook Excel, tự động tách các bảng độc lập trên cùng sheet."""
    wb = openpyxl.load_workbook(file_path, data_only=True)
    sheets_df = {}

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        max_row = ws.max_row
        max_col = ws.max_column
        if max_row < 1 or max_col < 1:
            continue

        # Đọc toàn bộ ô vào grid và xử lý ô gộp (unmerge cells)
        grid = {}
        for r in range(1, max_row + 1):
            for c in range(1, max_col + 1):
                grid[(r, c)] = ws.cell(r, c).value

        for rng in ws.merged_cells.ranges:
            top_left_val = ws.cell(rng.min_row, rng.min_col).value
            for r in range(rng.min_row, rng.max_row + 1):
                for c in range(rng.min_col, rng.max_col + 1):
                    grid[(r, c)] = top_left_val

        table_ranges = detect_table_ranges(ws, grid, max_row, max_col)

        if len(table_ranges) == 1:
            start_r, end_r, _ = table_ranges[0]
            df = parse_table_block(ws, grid, start_r, end_r, max_col)
            if not df.empty:
                sheets_df[sheet_name] = df
        else:
            for idx, (start_r, end_r, title) in enumerate(table_ranges):
                df = parse_table_block(ws, grid, start_r, end_r, max_col)
                if not df.empty:
                    clean_title = re.sub(r'[^\w\s-]', '', title).strip() or f"Table_{idx+1}"
                    tbl_key = f"{sheet_name} - {clean_title}"
                    sheets_df[tbl_key] = df

    return sheets_df


def generate_table_summary(sheets_df: Dict[str, pd.DataFrame]) -> str:
    """Tạo tóm tắt cấu trúc bảng chi tiết kèm danh sách Row_Path cho LLM prompt."""
    summary_lines = []
    for sheet_name, df in sheets_df.items():
        summary_lines.append(f"### Table / Sheet: '{sheet_name}' (Shape: {df.shape[0]} rows x {df.shape[1]} columns)")
        summary_lines.append("Columns:")
        for col in df.columns:
            summary_lines.append(f"  - `{col}`")

        sections = [s for s in df['Section'].dropna().unique() if str(s).strip()]
        if sections:
            summary_lines.append(f"Major Sections: {sections[:10]}")

        # Cung cấp danh mục toàn bộ Row_Paths cho LLM tra cứu chính xác
        row_paths = [str(rp) for rp in df['Row_Path'].dropna().unique() if str(rp).strip()]
        summary_lines.append(f"Available Row_Paths ({len(row_paths)} rows):")
        # In toàn bộ nếu dưới 150 rows (đủ bao quát toàn bộ t07 có 114 rows mà không bị cắt)
        if len(row_paths) <= 150:
            for rp in row_paths:
                summary_lines.append(f"  * {rp}")
        else:
            for rp in row_paths[:120]:
                summary_lines.append(f"  * {rp}")
            summary_lines.append(f"  * ... ({len(row_paths) - 120} more rows)")

        summary_lines.append("Sample Data (first 2 rows):")
        summary_lines.append(df.head(2).to_string(index=False))
        summary_lines.append("")
    return "\n".join(summary_lines)
