FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN python -m pip install --no-cache-dir pip==23.3.1
RUN python -m pip install --no-cache-dir .

COPY . /app

EXPOSE 8000
EXPOSE 8501

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
