FROM mcr.microsoft.com/playwright/python:v1.47.0-focal

# 設定工作目錄
WORKDIR /app

# 複製需求檔並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安裝 Playwright 瀏覽器 (Chromium, Firefox, WebKit)
RUN playwright install --with-deps

# 複製程式碼
COPY . .

# 啟動 FastAPI API 服務
CMD ["uvicorn", "test:app", "--host", "0.0.0.0", "--port", "8000"]