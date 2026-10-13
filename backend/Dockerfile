FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RICEAI_TORCH_THREADS=2

WORKDIR /srv/riceai

COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir \
      torch==2.2.1 torchvision==0.17.1 \
      --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY app ./app
RUN mkdir -p /srv/riceai/uploads /data

EXPOSE 8015
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8015", "--workers", "1"]
