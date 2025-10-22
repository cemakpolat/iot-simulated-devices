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
🚀 How to Run
You can run this project using either Docker Compose for local development or on a Kubernetes cluster for a more advanced setup.
Method 1: Local Development with Docker Compose
This is the quickest way to get the system running on your local machine.
Prerequisites:
Docker
Docker Compose
Instructions:
Clone the repository:
code
Bash
git clone <your-repo-link>
cd <repo-directory>
Define your devices:
Open the docker-compose.yml file and edit the client-xx services at the bottom to define as many devices as you need, each with a unique DEVICE_ID.
Build and run the services:
code
Bash
docker-compose up --build
Access the Dashboard:
Open your web browser and navigate to http://localhost. You will see the device cards appear and start updating live.
Method 2: Kubernetes (Local K3s Cluster)
This method deploys the application to a Kubernetes cluster, demonstrating its cloud-native capabilities.
Prerequisites:
A local Kubernetes cluster (e.g., K3s via Colima, k3d, or Docker Desktop).
kubectl configured to point to your cluster.
A Docker Hub account (or other container registry).
Instructions:
Build and Push Your Docker Images:
Kubernetes pulls images from a registry. You must build your custom images and push them. Replace your-dockerhub-username with your actual username.
code
Bash
# Log in to Docker Hub
docker login

# Build, tag, and push the server image
docker build -t your-dockerhub-username/iot-server:latest ./server
docker push your-dockerhub-username/iot-server:latest

# Build, tag, and push the client image
docker build -t your-dockerhub-username/iot-client:latest ./client
docker push your-dockerhub-username/iot-client:latest
Update Kubernetes Manifests:
Open the files in the k8s/ directory and replace the placeholder your-dockerhub-username/iot-server:latest and your-dockerhub-username/iot-client:latest with your actual image names.
Install an Ingress Controller (if needed):
A fresh K3s cluster may need an Ingress controller like Traefik.
code
Bash
helm repo add traefik https://helm.traefik.io/traefik
helm repo update
helm install traefik traefik/traefik -n kube-system
Deploy the Application:
Apply all the manifest files from the k8s directory.
code
Bash
kubectl apply -f k8s/
Access the Dashboard:
To access the dashboard via iot.k3s.local, you must edit your local hosts file.
macOS/Linux: sudo nano /etc/hosts
Windows: Edit C:\Windows\System32\drivers\etc\hosts
Add the following line and save the file:
code
Code
127.0.0.1   iot.k3s.local
Open your web browser and navigate to http://iot.k3s.local.
Scale your devices:
You can change the number of running clients at any time with the kubectl scale command.
code
Bash
# Scale up to 5 devices
kubectl scale deployment iot-client-deployment --replicas=5
📂 Project Structure
code
Code
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
code
Code
---

### ✍️ Final Medium Blog Post

# The Path to Production: Architecting a Resilient IoT Fleet on HTTP

Every great idea starts with a simple prototype. For an IoT project, that's often a single device sending data to a web server. It works, you show your team, and everyone is impressed. But then, the inevitable question arrives:

> *"This is great. Can it handle 10,000 devices, survive a server crash, and run for months without intervention?"*

Suddenly, your elegant prototype feels fragile. This is the story of that journey—from a brittle script to a resilient, scalable, and persistent architecture. It’s the path to production, and it’s paved with smart design patterns, even on a technology as ubiquitous as HTTP.

### Chapter 1: The Brittle Prototype

Our first version was a classic Flask app: an IoT device sends an HTTP `POST` to an `/infer` endpoint. The server runs an AI model and sends the result back. Simple, but it has fatal flaws:

1.  **The Synchronous Bottleneck:** The device has to wait for the AI model to finish. This doesn't scale.
2.  **The Gunicorn State Problem:** When run with a production server like Gunicorn, multiple worker processes are created, each with its own memory. Data sent to Worker #1 is invisible to Worker #2, leading to inconsistent or missing data.
3.  **No Persistence:** If the server restarts, all data is gone.

This architecture doesn't just scale poorly; it fundamentally breaks under real-world conditions.

### Chapter 2: The Architectural Leap - Asynchronous, Decoupled, and Persistent

To build a resilient system, we embraced three core principles of data engineering.

*(The final architecture diagram from the README)*

**1. Decouple Ingestion from Processing with Redis:**
We replaced the synchronous endpoint with a lightning-fast `/data` endpoint. Its only job is to validate the data and push it into a **Redis** list, which acts as a robust message queue. It immediately returns `202 Accepted` and moves on. This decouples the system and allows us to handle massive bursts of traffic.

**2. Asynchronous Processing with Celery:**
A dedicated **Celery Worker** runs as a separate process (or container). Its life is simple: constantly watch the Redis queue for new data. When a new message appears, it pulls it off and performs the computationally expensive AI inference. This isolates the heavy lifting from the web server.

**3. Achieve Persistence with TimescaleDB:**
After processing, the Celery worker doesn't just discard the result; it writes it to a **TimescaleDB** database. TimescaleDB is a PostgreSQL extension optimized for time-series data, making it perfect for IoT. By using a persistent Docker volume, we guarantee that our data survives any crash or restart.

### Chapter 3: Taming the Fleet - State Management and Automation

Our system was now robust, but not yet smart. We needed to manage the lifecycle of our devices.

**1. From Volatility to Stability: Managed Device IDs**
We stopped using dynamic container hostnames and moved to explicitly defining each device in our `docker-compose.yml` (or Kubernetes manifests), giving each one a stable, predictable ID like `device-01`. Our fleet was no longer an anonymous crowd; it was a list of named assets.

**2. Solving the "Ghost Device" Problem with Celery Beat**
When a device went offline, its data remained in the database forever, creating a dashboard full of zombies. We introduced a **Celery Beat** service—a scheduler that runs a cleanup task every minute. This task queries the database for any device that has been silent for a configured timeout period and deletes all of its historical data. The system is now self-healing and self-managing.

**3. Persistent Frontend State with `localStorage`**
To complete the user experience, we made one final change to the dashboard. The JavaScript now saves the history of graph measurements to the browser's `localStorage`. When you reload the page, the graphs repopulate with their history, providing a seamless and stateful experience.

### Chapter 4: The Final Frontier - Deploying to Kubernetes

With a production-grade architecture defined, the final step was to prove its cloud-native capabilities by deploying it to Kubernetes. We translated our Docker Compose services into Kubernetes manifest files:
*   **Deployments** for our server, workers, and clients.
*   **Services** to handle internal networking.
*   A **PersistentVolumeClaim** for the database.
*   An **Ingress** to expose the dashboard to the outside world.

After building and pushing our images to Docker Hub, we deployed the entire stack to a local K3s cluster with a single command: `kubectl apply -f k8s/`. We then used `kubectl scale` to effortlessly scale our fleet of simulated devices, proving the architecture was truly elastic.

*(A screenshot of `kubectl get pods` showing all the components running)*

### Conclusion: The Blueprint is Complete

We successfully navigated the path from a simple script to a resilient, manageable, and scalable IoT system running on Kubernetes. We didn't need a niche IoT protocol; we needed the right architecture.

This project is a blueprint. It's the 90% of the architectural work that allows you to confidently begin the final hardening phase for a real-world deployment, such as adding security layers and observability. The foundation is solid, and the path to production is clear.
