# AI-Powered IoT Anomaly Detection System 

This project offers an HTTP based IoT anomaly detection system.

## 🚀 How to Run

You can run this project using either Docker Compose for local development or on a Kubernetes cluster for a more advanced setup.

This is the quickest way to get the system running on your local machine.

### Prerequisites:

- Docker
- Docker Compose

### Instructions:

Clone the repository:

```
git clone <your-repo-link>
cd <repo-directory>
```

Define your devices:
Open the `docker-compose.yml` file and edit the `client-xx` services at the bottom to define as many devices as you need, each with a unique DEVICE_ID.
Build and run the services:
```
    docker-compose up --build
```
## Access the Dashboard:

Open your web browser and navigate to `http://localhost`. You will see the device cards appear and start updating live.