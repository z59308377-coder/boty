FROM python:3.11-slim

# تثبيت ffmpeg عشان yt-dlp يشتغل صح
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 👇 السطرين دول عشان نعدل مكتبة تلجرام ونخليها تقبل style
RUN sed -i 's/def __init__(self, text: str, url: Optional\[str\] = None,/def __init__(self, text: str, url: Optional[str] = None, style: Optional[str] = None,/' /usr/local/lib/python3.11/site-packages/telegram/_inlinekeyboardbutton.py
RUN sed -i "s/self.url = url/self.url = url\n        self.style = style/" /usr/local/lib/python3.11/site-packages/telegram/_inlinekeyboardbutton.py

COPY . .

CMD ["python", "main.py"]
