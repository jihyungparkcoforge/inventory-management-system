FROM python:3.11.10

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV INVENTORY_DB=/data/inventory.db
RUN mkdir -p /data

CMD ["python", "main.py"]
