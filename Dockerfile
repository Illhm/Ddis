# Slowloris Checker - Docker Image
FROM python:3.11-slim

# Set metadata
LABEL maintainer="security@example.com"
LABEL description="Professional HTTP Slowloris Vulnerability Scanner"
LABEL version="2.0.0"

# Set working directory
WORKDIR /app

# Copy application files
COPY slowloris_checker/ /app/slowloris_checker/
COPY setup.py /app/
COPY README.md /app/
COPY requirements-pro.txt /app/

# Install package
RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd -m -u 1000 scanner && \
    chown -R scanner:scanner /app

# Switch to non-root user
USER scanner

# Set entry point
ENTRYPOINT ["python", "-m", "slowloris_checker"]

# Default command (show help)
CMD ["--help"]

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import slowloris_checker; print('OK')" || exit 1
