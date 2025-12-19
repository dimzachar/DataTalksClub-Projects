FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Default command: run pipeline discovery
CMD ["python", "-m", "src.pipeline_runner", "--discover"]
