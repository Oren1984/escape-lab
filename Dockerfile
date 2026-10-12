FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/tmp \
    ESCAPE_LAB_DATA_DIR=/data/runs

RUN useradd --system --uid 10001 --no-create-home lab \
    && mkdir -p /data/runs && chown -R lab /data

WORKDIR /srv/escape-lab
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY .streamlit ./.streamlit
COPY app ./app
COPY scenarios ./scenarios

USER lab
EXPOSE 8501

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3     CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=2).status == 200 else 1)"]

# 0.0.0.0 is inside the container only. compose.yaml publishes the port on 127.0.0.1.
CMD ["python", "-m", "streamlit", "run", "app/main.py",      "--server.address=0.0.0.0", "--server.port=8501",      "--browser.serverAddress=localhost", "--server.fileWatcherType=none"]
