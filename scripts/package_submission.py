"""Đóng gói bài nộp: dist/<team>.zip với Dockerfile ở gốc, không chứa secrets.

    python scripts/package_submission.py [team_code]   # mặc định: AI26C0062
"""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEAM_CODE = "AI26C0062"  # mã đội; tên tệp nộp phải khớp chính xác: AI26C0062.zip
MAX_BYTES = 100 * 1024 * 1024

INCLUDE = [
    "Dockerfile",
    ".dockerignore",
    "requirements.txt",
    "main.py",
    "README.md",
    "HUONG_DAN_NOP_BAI.md",
    "DE_THI.md",
    ".env.example",
    "docker-compose.yml",
    "evaluate.py",
    "unseen_evaluation.py",
    "app",
    "scripts",
]
EXCLUDE_DIRS = {"__pycache__", ".venv", ".git", "dist", "output"}
EXCLUDE_EXT = {".pyc", ".pyo"}
FORBIDDEN_NAMES = {".env"}


def iter_files():
    for entry in INCLUDE:
        path = os.path.join(ROOT, entry)
        if os.path.isfile(path):
            yield entry
        elif os.path.isdir(path):
            for dirpath, dirnames, filenames in os.walk(path):
                dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
                for fn in filenames:
                    if os.path.splitext(fn)[1] in EXCLUDE_EXT or fn in FORBIDDEN_NAMES:
                        continue
                    yield os.path.relpath(os.path.join(dirpath, fn), ROOT).replace(os.sep, "/")
        else:
            print(f"[warn] bỏ qua, không tồn tại: {entry}")


def main() -> None:
    if len(sys.argv) > 2:
        print(__doc__)
        sys.exit(2)
    team = sys.argv[1] if len(sys.argv) == 2 else TEAM_CODE
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    zip_path = os.path.join(ROOT, "dist", f"{team}.zip")

    files = sorted(set(iter_files()))
    if "Dockerfile" not in files:
        sys.exit("Thiếu Dockerfile ở thư mục gốc")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in files:
            zf.write(os.path.join(ROOT, rel), rel)

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    assert "Dockerfile" in names, "Dockerfile phải nằm ở gốc ZIP"
    leaked = [n for n in names if os.path.basename(n) in FORBIDDEN_NAMES]
    assert not leaked, f"ZIP chứa file bí mật: {leaked}"

    size = os.path.getsize(zip_path)
    print(f"Đã tạo {zip_path} ({size / 1024:.1f} KB, {len(names)} files)")
    if size > MAX_BYTES:
        sys.exit("ZIP vượt quá 100 MB!")


if __name__ == "__main__":
    main()
