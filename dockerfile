FROM python:3.10-slim

WORKDIR /app

# System dependencies for geospatial Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/

# Install runtime Python dependencies directly from pyproject
RUN pip install --no-cache-dir \
    geopandas \
    pandas \
    numpy \
    scikit-learn \
    xgboost \
    streamlit \
    pydeck \
    "pandera>=0.32.1" \
    "py7zr>=1.1.3" \
    "matplotlib>=3.10.9"

# Create data and generate the synthetic MVP output
RUN mkdir -p data && \
    python src/01_synthetic_data.py && \
    python src/03_pipeline.py

ENV PORT=8080

EXPOSE 8080

CMD streamlit run src/04_app.py \
    --server.address=0.0.0.0 \
    --server.port=${PORT}
