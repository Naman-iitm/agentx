FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Prototype note: the app creates + seeds an SQLite database on startup.
# For the PostgreSQL target, set DATABASE_URL and run migrations as a
# controlled release step (see docs/deployment_guide.md).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
