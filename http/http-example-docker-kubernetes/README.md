# Scalable AI-Powered IoT Anomaly Detection System

This project demonstrates a production-grade, containerized architecture for ingesting, processing, and visualizing IoT sensor data in real-time. It uses an asynchronous pipeline to handle high-throughput data from a fleet of devices, applies AI models for anomaly detection, persists all data in a time-series database, and displays the results on a live-updating dashboard.

The entire stack is designed to be cloud-native, with deployment options for both local development with Docker Compose and a more advanced setup on a Kubernetes (K3s) cluster.

---

### ✨ Features

*   **🤖 Multi-Model AI:** A dynamic **Model Registry** applies the correct anomaly detection model (Scikit-learn's `IsolationForest`) for each sensor type (e.g., temperature, humidity).
*   **🚀 Asynchronous & Decoupled:** Uses **Redis** as a message broker and **Celery** for background processing, ensuring the data ingestion API is fast and responsive.
*   **💾 Persistent & Stateful:** All readings are stored in a **TimescaleDB** (a PostgreSQL extension for time-series data) hypertable, ensuring data survives restarts.
*   **⚙️ Automated State Management:** A scheduled task (`Celery Beat`) automatically prunes inactive devices from the database, preventing stale data from appearing on the dashboard.
*   **🖥️ Live Persistent Dashboard:** A sleek, real-time dashboard built with vanilla JavaScript and Chart.js that persists graph history across page reloads using `localStorage`.
*   **🐳 Docker Compose for Local Dev:** A simple `docker-compose up` command to run the entire stack on a local machine.
*   **☸️ Kubernetes-Ready:** Includes all necessary manifest files to deploy the entire application to a Kubernetes cluster like K3s.

---

### 🏗️ System Architecture

The system decouples data ingestion from processing using Redis, with TimescaleDB as the persistent backend.

```mermaid
graph TD
    subgraph "IoT Clients"
        Client[iot-client]
    end
    subgraph "Docker / Kubernetes"
        Server[iot-server (Flask/Gunicorn)]
        Worker[celery-worker]
        Scheduler[celery-beat]
        Redis[Redis Broker]
        DB[(TimescaleDB)]
    end
    subgraph "User"
        Dashboard[Browser]
    end

    Client -- 1. POST /data --> Server
    Server -- 2. LPUSH to queue --> Redis
    Worker -- 3. BRPOP from queue --> Redis
    Worker -- 4. Runs AI Inference --> Worker
    Worker -- 5. INSERT results --> DB
    Scheduler -- Schedules cleanup --> Worker
    Dashboard -- 7. GET /latest --> Server
    Server -- 6. SELECT last() from --> DB
