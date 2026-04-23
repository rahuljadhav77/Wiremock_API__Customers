FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV BIND_HOST=0.0.0.0
ENV PORT=5001
ENV CUSTOMER_DATA_PATH=/app/data/customers.xlsx

RUN mkdir -p /app/data

EXPOSE 5001

HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5001/health', timeout=2)"

CMD ["python", "app.py"]
