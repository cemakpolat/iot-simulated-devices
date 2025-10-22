# Scalable AI-Powered IoT Anomaly Detection System

This project demonstrates a production-grade, containerized architecture for ingesting, processing, and visualizing IoT sensor data in real-time. It uses an asynchronous pipeline to handle high-throughput data from a fleet of devices, applies AI models for anomaly detection, persists all data in a time-series database, and displays the results on a live-updating dashboard.

The entire stack is designed to be cloud-native, with deployment options for both local development with Docker Compose and a more advanced setup on a Kubernetes (K3s) cluster.

---

## ✨ Features

*   **🤖 Multi-Model AI:** A dynamic **Model Registry** applies the correct anomaly detection model (Scikit-learn's `IsolationForest`) for each sensor type (e.g., temperature, humidity).
*   **🚀 Asynchronous & Decoupled:** Uses **Redis** as a message broker and **Celery** for background processing, ensuring the data ingestion API is fast and responsive.
*   **💾 Persistent & Stateful:** All readings are stored in a **TimescaleDB** (a PostgreSQL extension for time-series data) hypertable, ensuring data survives restarts.
*   **⚙️ Automated State Management:** A scheduled task (`Celery Beat`) automatically prunes inactive devices from the database, preventing stale data from appearing on the dashboard.
*   **🖥️ Live Persistent Dashboard:** A sleek, real-time dashboard built with vanilla JavaScript and Chart.js that persists graph history across page reloads using `localStorage`.
*   **🐳 Docker Compose for Local Dev:** A simple `docker-compose up` command to run the entire stack on a local machine.
*   **☸️ Kubernetes-Ready:** Includes all necessary manifest files to deploy the entire application to a Kubernetes cluster like K3s.

---

## 🏗️ System Architecture

The system decouples data ingestion from processing using Redis, with TimescaleDB as the persistent backend, and all details are explained in Medium blog:


## 🚀 How to Run

You can run this project using either Docker Compose for local development or on a Kubernetes cluster for a more advanced setup.

### Method 1: Local Development with Docker Compose
This is the quickest way to get the system running on your local machine.

Prerequisites:

- Docker
- Docker Compose

Instructions:

Clone the repository:

```
git clone <your-repo-link>
cd <repo-directory>
```

Define your devices:

Open the `docker-compose.yml` file and edit the client-xx services at the bottom to define as many devices as you need, each with a unique DEVICE_ID.

Build and run the services:

```
docker-compose up --build
```

Access the Dashboard:

Open your web browser and navigate to http://localhost. You will see the device cards appear and start updating live.

### Method 2: Kubernetes (Local K3s Cluster)

This method deploys the application to a Kubernetes cluster, demonstrating its cloud-native capabilities.
Prerequisites:

A local Kubernetes cluster (e.g., K3s via Colima, k3d, or Docker Desktop). kubectl configured to point to your cluster. A Docker Hub account (or other container registry).

Instructions:

Build and Push Your Docker Images:
Kubernetes pulls images from a registry. You must build your custom images and push them. Replace your-dockerhub-username with your actual username.

```
# Log in to Docker Hub
docker login

# Build, tag, and push the server image
docker build -t your-dockerhub-username/iot-server:latest ./server
docker push your-dockerhub-username/iot-server:latest

# Build, tag, and push the client image
docker build -t your-dockerhub-username/iot-client:latest ./client
docker push your-dockerhub-username/iot-client:latest

```

Update Kubernetes Manifests:

Open the files in the k8s/ directory and replace the placeholder your-dockerhub-username/iot-server:latest and your-dockerhub-username/iot-client:latest with your actual image names.
Install an Ingress Controller (if needed):
A fresh K3s cluster may need an Ingress controller like Traefik.


```
helm repo add traefik https://helm.traefik.io/traefik
helm repo update
helm install traefik traefik/traefik -n kube-system
```

### Deploy the Application:

Apply all the manifest files from the k8s directory.
```
kubectl apply -f k8s/
```
Access the Dashboard:

To access the dashboard via iot.k3s.local, you must edit your local hosts file.
macOS/Linux: sudo nano /etc/hosts
Windows: Edit C:\Windows\System32\drivers\etc\hosts
Add the following line and save the file:

```
127.0.0.1   iot.k3s.local
```

Open your web browser and navigate to http://iot.k3s.local.
Scale your devices:
You can change the number of running clients at any time with the kubectl scale command.

```
# Scale up to 5 devices
kubectl scale deployment iot-client-deployment --replicas=5
```

📂 Project Structure
```
.
├── client/             # IoT Device Simulator
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
├── server/             # Backend (API, Worker, Scheduler)
│   ├── app/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── start.sh
│   └── requirements.txt
├── k8s/                # Kubernetes Manifests
│   ├── 01-persistent-volume-claim.yaml
│   ├── ...
│   └── 06-client-deployment.yaml
└── docker-compose.yml  # Local development environment
```

