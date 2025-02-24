# Health Data API

## Overview
This project provides a RESTful API for processing and analyzing Apple Health data exports. Users can upload Apple Health XML files, extract specific health metrics, and perform data analysis.

## Features
- Upload Apple Health data in XML format
- Extract key health metrics including:
  - Steps
  - Distance walked/runned
  - Heart rate
  - Body mass (weight)
  - Sleep analysis
  - Workout data from WHOOP
- Store extracted metrics in a database
- Generate CSV reports
- Perform data analysis using LLM-based insights
- Provide API endpoints for retrieving health data summaries

## Tech Stack
- **Backend**: Django, Django REST Framework (DRF)
- **Data Processing**: Pandas, XML parsing
- **API Documentation**: drf-yasg (Swagger)
- **LLM Integration**: OpenRouter API
- **Storage**: Django ORM, File System

## Installation

### Prerequisites
- Python 3.9+
- Virtual environment (optional but recommended)
- Django and required dependencies

### Setup
1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd <project_directory>
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\\Scripts\\activate`
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Apply migrations:
   ```bash
   python manage.py migrate
   ```
5. Start the server:
   ```bash
   python manage.py runserver
   ```

## API Endpoints

### Upload Apple Health Data
**Endpoint:** `POST /upload/`
- **Description:** Uploads an Apple Health XML file.
- **Request:** `multipart/form-data`
  ```json
  {
    "file": "export.xml"
  }
  ```
- **Response:**
  ```json
  {
    "message": "File uploaded successfully, and health metrics processed",
    "file_id": 1,
    "responses": [...]
  }
  ```

### Retrieve Health Metrics
**Endpoint:** `GET /metrics/?health_data_id=<id>`
- **Description:** Fetches health metrics for a given file ID.
- **Response:**
  ```json
  [
    {
      "metric_type": "HKQuantityTypeIdentifierStepCount",
      "csv_url": "http://example.com/health_metrics/steps_1.csv"
    }
  ]
  ```

### Analyze Health Data
**Endpoint:** `GET /analyze/?health_data_id=<id>`
- **Description:** Performs AI-driven analysis on health data.
- **Response:**
  ```json
  {
    "analysis": "You walked an average of 10,000 steps per day..."
  }
  ```

## File Structure
```
project/
│── health_data/
│   ├── views.py  # API logic
│   ├── models.py # Database models
│   ├── serializers.py # API serializers
│   ├── urls.py  # URL routing
│── health_metrics/  # Directory for storing processed CSV files
│── manage.py
```


