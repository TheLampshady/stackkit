# Service Overview

This folder contains the main FastAPI backend service for the project. It provides API endpoints, static asset serving, and GCP/Firebase integration.

## Table of Contents
- [Service Overview](#service-overview)
- [Setup](#setup)
- [Running Locally](#running-locally)
  - [Service Table](#service-table)
  - [Other Commands](#other-commands)
- [Deployment](#deployment)
  - [Cloud Service Table](#cloud-service-table)
  - [Other Commands](#other-commands-1)
- [Configuration](#configuration)

## Setup

Install dependencies:
```bash
pip install -r requirements.txt
```

## Running Locally

Start the FastAPI app:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
Or use the root Makefile:
```bash
make run
```

### Service Table
| Service Name    | Command to Run         | Port  |
|-----------------|-----------------------|-------|
| FastAPI Backend | make run / uvicorn    | 8000  |

### Other Commands
| Command         | Description                          |
|-----------------|--------------------------------------|
| make build      | Build static assets                  |

## Deployment

Deploy to GCP App Engine:
```bash
make deploy
```

### Cloud Service Table
| Cloud Service Name | Command to Deploy         | When to Deploy         |
|--------------------|--------------------------|-----------------------|
| FastAPI Backend    | make deploy              | On code changes       |

### Other Commands
| Command         | Description                          |
|-----------------|--------------------------------------|
| make build      | Build static assets                  |

## Configuration
- See [app.yaml](app.yaml) for deployment config
- See [app_settings.py](app_settings.py) for runtime settings
- See [requirements.txt](requirements.txt) for dependencies

---
_This README merges existing and new information for clarity and completeness._
