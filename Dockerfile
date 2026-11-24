FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     STOCKFISH_PATH=/usr/games/stockfish     KNIGHTFORGE_DB_PATH=/app/data/knightforge.db     PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends     stockfish     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml requirements.txt README.md ./
COPY src ./src
COPY data ./data
COPY web ./web

RUN pip install --no-cache-dir -r requirements.txt &&     pip install --no-cache-dir --no-deps -e .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn knightforge_engine.server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
