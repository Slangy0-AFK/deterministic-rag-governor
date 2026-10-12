FROM python:3.11-slim
WORKDIR /app
ENV GOVERNOR_DB=/data/governor.db \
	CHROMA_PATH=/data/chroma_db
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
	&& useradd --create-home --uid 10001 governor \
	&& mkdir -p /data \
	&& chown governor:governor /data
COPY . .
USER governor
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
	CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2)"]
CMD ["uvicorn", "governor:app", "--host", "0.0.0.0", "--port", "8000"]