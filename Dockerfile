FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY faultlab ./faultlab
COPY demo ./demo
COPY migrations ./migrations
COPY alembic.ini ./
RUN pip install --no-cache-dir .
RUN useradd -r -u 10001 faultlab
USER faultlab
CMD ["uvicorn", "faultlab.api:app", "--host", "0.0.0.0", "--port", "8000"]
