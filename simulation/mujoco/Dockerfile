FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MUJOCO_GL=osmesa

RUN apt-get update \
    && apt-get install -y --no-install-recommends libosmesa6 libgl1 libgl1-mesa-dri \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py world.py ./

EXPOSE 8080 8765
CMD ["python", "server.py"]
