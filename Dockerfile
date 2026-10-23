# EarthScape – container image (local Docker, Render, Koyeb, any Docker host)
FROM python:3.12-slim
RUN useradd -m -u 1000 user
WORKDIR /home/user/earthscape
COPY --chown=user . .
RUN pip install --no-cache-dir -r app/requirements.txt
USER user
ENV EARTHSCAPE_HOST=0.0.0.0 EARTHSCAPE_PORT=7860 EARTHSCAPE_DEBUG=0 EARTHSCAPE_AUTOSTREAM=1 \
    EARTHSCAPE_RETRAIN_EVERY=100000 EARTHSCAPE_STREAM_INTERVAL=6 EARTHSCAPE_N_JOBS=1 PYTHONUNBUFFERED=1
WORKDIR /home/user/earthscape/app
# Train the ML models and load the 2016-2023 archive at build time, so the container starts in seconds
RUN rm -f earthscape.db && rm -rf ../ml/registry && EARTHSCAPE_AUTOSTREAM=0 EARTHSCAPE_N_JOBS=2 python -c "import app; print('models trained, database ready')"
EXPOSE 7860
# Render / Koyeb pass the port in $PORT
CMD ["sh", "-c", "EARTHSCAPE_PORT=${PORT:-7860} exec python app.py"]
