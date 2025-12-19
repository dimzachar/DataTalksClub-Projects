"""Pytest configuration and fixtures."""

import os
import sys

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_github_files():
    """Sample GitHub repository files for testing."""
    return {
        'README.md': """# Sample Project
        
This is a data engineering project.

## Features
- Data ingestion
- Transformation
- Loading to warehouse
""",
        'docker-compose.yml': """version: '3'
services:
  app:
    build: .
    ports:
      - "8000:8000"
""",
        'requirements.txt': """pandas==2.0.0
apache-airflow==2.5.0
google-cloud-bigquery==3.0.0
""",
    }


@pytest.fixture
def sample_airflow_files():
    """Sample Airflow project files."""
    return {
        'README.md': '# Airflow Pipeline',
        'dags/pipeline.py': """
from airflow import DAG
from airflow.operators.python import PythonOperator

dag = DAG('my_pipeline', schedule_interval='@daily')
""",
        'docker-compose.yml': """
services:
  airflow:
    image: apache/airflow:2.5.0
""",
    }


@pytest.fixture
def sample_kafka_files():
    """Sample Kafka streaming project files."""
    return {
        'README.md': '# Kafka Streaming Pipeline',
        'producer.py': """
from kafka import KafkaProducer
producer = KafkaProducer(bootstrap_servers='localhost:9092')
""",
        'docker-compose.yml': """
services:
  kafka:
    image: confluentinc/cp-kafka:latest
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
""",
    }


@pytest.fixture
def sample_fastapi_files():
    """Sample FastAPI web service files."""
    return {
        'README.md': '# ML API Service',
        'app.py': """
from fastapi import FastAPI
app = FastAPI()

@app.get("/predict")
def predict():
    return {"prediction": 0.5}
""",
        'Dockerfile': """
FROM python:3.9
COPY . /app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0"]
""",
    }


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv('MY_GITHUB_TOKEN', 'test_github_token')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test_openrouter_key')
