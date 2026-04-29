FROM python:3.11-slim

# Instalar FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY main.py .

# Exponer puerto
EXPOSE 5000

# Iniciar servidor
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "300", "main:app"]
