FROM --platform=linux/amd64 python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Cài thư viện trước để tận dụng cache layer
COPY requirements.txt .
RUN pip install -r requirements.txt

# Mã nguồn (secrets bị loại bởi .dockerignore)
COPY . .

# Hệ thống chấm gọi:
#   --xlsx-dir /input/xlsx_files --queries /input/queries.json --output /output/submission.csv
#   --openrouter-key <key> --openrouter-model qwen/qwen3.7-flash --openrouter-base-url https://openrouter.ai/api/v1
ENTRYPOINT ["python", "main.py"]
