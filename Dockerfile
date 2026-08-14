FROM python:3.12-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Bind-Adresse/Port des Containers. HOST bleibt 0.0.0.0, damit die App
# durch das Docker-Port-Mapping erreichbar ist. Die Beschraenkung auf die
# Server-IP erfolgt beim "docker run" ueber -p SERVER_IP:8085:8085.
ENV HOST=0.0.0.0 \
    PORT=8085

EXPOSE 8085

CMD ["sh", "-c", "uvicorn app.main:app --host \"$HOST\" --port \"$PORT\""]
