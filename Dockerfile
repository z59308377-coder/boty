FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 👇 السطرين دول عشان نعدل المكتبة وتقبل الألوان
COPY patch_telegram.py .
RUN python patch_telegram.py

COPY . .

CMD ["python", "main.py"]
