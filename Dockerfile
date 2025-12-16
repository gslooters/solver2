# Solver2 - GREEDY Planning Engine
# DRAAD 194: Explicit Dockerfile for Flask application

FROM python:3.12.7-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Verify critical imports for Solver2
RUN echo "[Dockerfile] Testing critical imports..." && \
    python -c "from flask import Flask; print('[OK] Flask imported')" && \
    python -c "from solvers.greedy_engine import GreedyPlanner; print('[OK] GreedyPlanner imported')" && \
    python -c "from solvers.solver_selector import SolverSelector; print('[OK] SolverSelector imported')" && \
    python -c "from solver2.src.main import app; print('[OK] Flask app imported')" && \
    echo "[Dockerfile] ✅ ALL IMPORTS SUCCESSFUL - SOLVER2 READY"

# Expose port
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=5000
ENV DEBUG=False

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Start application
CMD ["python", "-m", "solver2.src.main"]
