FROM python:3.11-slim
WORKDIR /app
COPY services/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY services /app/services
ENV PYTHONPATH=/app
EXPOSE 8002
CMD ["uvicorn", "services.student_portal.main:app", "--host", "0.0.0.0", "--port", "8002"]
