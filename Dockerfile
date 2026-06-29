FROM python:3.12-slim

WORKDIR /app

COPY packages/ packages/
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=packages/ -r requirements.txt && rm -rf packages/

COPY app/ app/
COPY run.py .

RUN mkdir -p data/images

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
