# GKE Deployment Guide - Agent Development Kit

Source: https://google.github.io/adk-docs/deploy/gke/

## Overview

The Agent Development Kit supports deploying agents to Google Kubernetes Engine (GKE), Google Cloud's managed Kubernetes service. This guide covers both manual and automated deployment approaches.

## Environment Setup

Required environment variables:

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT_NUMBER=$(gcloud projects describe --format json $GOOGLE_CLOUD_PROJECT | jq -r ".projectNumber")
```

## Required APIs and Permissions

Enable these Google Cloud APIs:
- `container.googleapis.com` (Kubernetes Engine)
- `artifactregistry.googleapis.com` (Artifact Registry)
- `cloudbuild.googleapis.com` (Cloud Build)
- `aiplatform.googleapis.com` (Vertex AI)

Assign these IAM roles to the compute engine service account:
- `roles/artifactregistry.writer`
- `roles/storage.objectViewer`
- `roles/logging.viewer`
- `roles/logging.logWriter`

## Deployment Options

### Option 1: Manual Deployment

**Create GKE Cluster:**

```bash
gcloud container clusters create-auto adk-cluster \
    --location=$GOOGLE_CLOUD_LOCATION \
    --project=$GOOGLE_CLOUD_PROJECT
```

**Connect to Cluster:**

```bash
gcloud container clusters get-credentials adk-cluster \
    --location=$GOOGLE_CLOUD_LOCATION \
    --project=$GOOGLE_CLOUD_PROJECT
```

**Project Structure:**

```
your-project-directory/
├── capital_agent/
│   ├── __init__.py
│   └── agent.py
├── main.py
├── requirements.txt
└── Dockerfile
```

**Sample Agent (capital_agent/agent.py):**

```python
from google.adk.agents import LlmAgent

def get_capital_city(country: str) -> str:
  """Retrieves the capital city for a given country."""
  capitals = {"france": "Paris", "japan": "Tokyo", "canada": "Ottawa"}
  return capitals.get(country.lower(), f"Sorry, I don't know the capital of {country}.")

capital_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="capital_agent",
    description="Answers user questions about capital cities.",
    tools=[get_capital_city]
)

root_agent = capital_agent
```

**FastAPI Application (main.py):**

```python
import os
import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_SERVICE_URI = "sqlite+aiosqlite:///./sessions.db"
ALLOWED_ORIGINS = ["http://localhost", "http://localhost:8080", "*"]
SERVE_WEB_INTERFACE = True

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    session_service_uri=SESSION_SERVICE_URI,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
```

**Dependencies (requirements.txt):**

```
google-adk
```

**Container Image (Dockerfile):**

```dockerfile
FROM python:3.13-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN adduser --disabled-password --gecos "" myuser && \
    chown -R myuser:myuser /app

COPY . .

USER myuser

ENV PATH="/home/myuser/.local/bin:$PATH"

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
```

**Build Container Image:**

```bash
gcloud artifacts repositories create adk-repo \
    --repository-format=docker \
    --location=$GOOGLE_CLOUD_LOCATION \
    --description="ADK repository"

gcloud builds submit \
    --tag $GOOGLE_CLOUD_LOCATION-docker.pkg.dev/$GOOGLE_CLOUD_PROJECT/adk-repo/adk-agent:latest \
    --project=$GOOGLE_CLOUD_PROJECT \
    .
```

**Configure Kubernetes Service Account:**

```bash
kubectl create serviceaccount adk-agent-sa

gcloud projects add-iam-policy-binding projects/${GOOGLE_CLOUD_PROJECT} \
    --role=roles/aiplatform.user \
    --member=principal://iam.googleapis.com/projects/${GOOGLE_CLOUD_PROJECT_NUMBER}/locations/global/workloadIdentityPools/${GOOGLE_CLOUD_PROJECT}.svc.id.goog/subject/ns/default/sa/adk-agent-sa \
    --condition=None
```

**Kubernetes Manifest (deployment.yaml):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: adk-agent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: adk-agent
  template:
    metadata:
      labels:
        app: adk-agent
    spec:
      serviceAccount: adk-agent-sa
      containers:
      - name: adk-agent
        imagePullPolicy: Always
        image: $GOOGLE_CLOUD_LOCATION-docker.pkg.dev/$GOOGLE_CLOUD_PROJECT/adk-repo/adk-agent:latest
        resources:
          limits:
            memory: "128Mi"
            cpu: "500m"
            ephemeral-storage: "128Mi"
          requests:
            memory: "128Mi"
            cpu: "500m"
            ephemeral-storage: "128Mi"
        ports:
        - containerPort: 8080
        env:
          - name: PORT
            value: "8080"
          - name: GOOGLE_CLOUD_PROJECT
            value: $GOOGLE_CLOUD_PROJECT
          - name: GOOGLE_CLOUD_LOCATION
            value: $GOOGLE_CLOUD_LOCATION
          - name: GOOGLE_GENAI_USE_VERTEXAI
            value: "$GOOGLE_GENAI_USE_VERTEXAI"
---
apiVersion: v1
kind: Service
metadata:
  name: adk-agent
spec:
  type: LoadBalancer
  ports:
    - port: 80
      targetPort: 8080
  selector:
    app: adk-agent
```

**Deploy Application:**

```bash
kubectl apply -f deployment.yaml
kubectl get pods -l=app=adk-agent
kubectl get service adk-agent
kubectl get svc adk-agent -o=jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

### Option 2: Automated Deployment

Use the built-in ADK CLI command for streamlined deployment:

```bash
adk deploy gke \
    --project myproject \
    --cluster_name test \
    --region us-central1 \
    --with_ui \
    --log_level info \
    ~/agents/multi_tool_agent/
```

**Command Syntax:**

```
adk deploy gke [OPTIONS] AGENT_PATH
```

**Available Options:**

| Argument | Description | Required |
|----------|-------------|----------|
| AGENT_PATH | Local file path to agent root directory | Yes |
| --project | Google Cloud Project ID | Yes |
| --cluster_name | Name of GKE cluster | Yes |
| --region | Google Cloud region (e.g., us-central1) | Yes |
| --with_ui | Deploy front-end user interface | No |
| --log_level | Logging level (debug, info, warning, error) | No |

**How It Works:**

The automated process: "builds a Docker container image from your agent's source code" and "pushes it to your project's Artifact Registry." ADK then "dynamically generates the necessary Kubernetes manifest files" and deploys them to your cluster.

## Verification

**Check Deployment Status:**

```bash
kubectl get pods
kubectl get service
```

**Verify Deployment with kubectl:**

```bash
kubectl get pods
kubectl get service
```

**Get External IP:**

```bash
kubectl get service
```

## Testing

### UI Testing

Navigate to the Kubernetes service URL in a web browser to access the ADK dev UI interface.

### API Testing (curl)

**Set Application URL:**

```bash
export APP_URL=$(kubectl get service adk-agent -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
```

**List Available Apps:**

```bash
curl -X GET $APP_URL/list-apps
```

**Create or Update Session:**

```bash
curl -X POST \
    $APP_URL/apps/capital_agent/users/user_123/sessions/session_abc \
    -H "Content-Type: application/json" \
    -d '{"preferred_language": "English", "visit_count": 5}'
```

**Run the Agent:**

```bash
curl -X POST $APP_URL/run_sse \
    -H "Content-Type: application/json" \
    -d '{
    "app_name": "capital_agent",
    "user_id": "user_123",
    "session_id": "session_abc",
    "new_message": {
        "role": "user",
        "parts": [{
        "text": "What is the capital of Canada?"
        }]
    },
    "streaming": false
    }'
```

## Troubleshooting

**403 Permission Denied for Gemini 2.0 Flash:**
Verify the Kubernetes service account has the "Vertex AI User" role assigned. For AI Studio, ensure `GOOGLE_API_KEY` is set in the deployment manifest.

**404 or Not Found Response:**
Check application logs to diagnose the issue:

```bash
export POD_NAME=$(kubectl get pod -l app=adk-agent -o jsonpath='{.items[0].metadata.name}')
kubectl logs $POD_NAME
```

**Read-only Database Error:**
The SQLite database may be read-only when copied into the container. Either delete `sessions.db` before building the image or create a `.dockerignore` file:

```
sessions.db
```

**Insufficient Permission to Stream Logs:**
Check the Cloud Build page in the Google Cloud Console for build progress. Images are still pushed to Artifact Registry even if streaming fails.

**Gemini 2.0 Flash Not Supported in Live API:**
The voice functionality (Live API) is unavailable with `gemini-2.0-flash`. Only text-based chat works.

## Cleanup

**Delete GKE Cluster:**

```bash
gcloud container clusters delete adk-cluster \
    --location=$GOOGLE_CLOUD_LOCATION \
    --project=$GOOGLE_CLOUD_PROJECT
```

**Delete Artifact Registry:**

```bash
gcloud artifacts repositories delete adk-repo \
    --location=$GOOGLE_CLOUD_LOCATION \
    --project=$GOOGLE_CLOUD_PROJECT
```

**Delete Project:**

```bash
gcloud projects delete $GOOGLE_CLOUD_PROJECT
```

## Key Notes

- Workload Identity must be enabled for the Kubernetes cluster
- The deployment package includes agent code and dependencies, but not the web UI unless specified
- SQLite is used by default for session storage; consider alternative solutions for production
- The deployment creates a LoadBalancer service that provisions a public IP address
