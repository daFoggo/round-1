FROM python:3.12-slim

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /workspace

# Copy dependency files first to cache layer
COPY pyproject.toml .
COPY requirements.txt .

# Install dependencies using uv
RUN uv pip install --system -r requirements.txt

# Copy source code and files
COPY . .

# Default command: chạy FastAPI server (nếu muốn dùng web/API)
# Có thể override để chạy CLI: python main.py --input_dir xlsx_files --queries queries.json --output submission.csv
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
