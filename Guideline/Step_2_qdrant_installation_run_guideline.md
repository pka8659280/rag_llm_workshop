# Qdrant Installation & Run Guideline (Docker)

## Prerequisite

- Docker must be installed and running (see `Step_1_docker_installation_run_guideline.md`).

## 1. Pull the Qdrant Image

- Open PowerShell or Command Prompt and run:

```powershell
docker pull qdrant/qdrant
```

## 2. Create a Storage Directory (Optional but Recommended)

- Create a local folder to persist Qdrant data:

```powershell
# Use any folder you like, e.g. C:\qdrant_storage
mkdir <your-qdrant-folder>
```

## 3. Run the Qdrant Container

- Run Qdrant as a background container with persistent storage:

```powershell
docker run -d -p 6333:6333 -p 6334:6334 --name qdrant -v <your-qdrant-folder>:/qdrant/storage qdrant/qdrant
```

- **Ports:**
  - `6333` = HTTP REST API
  - `6334` = gRPC API

## 4. Verify the Container Is Running

- Check the container status:

```powershell
docker ps
```

- You should see the `qdrant` container with status "Up".

## 5. Open the Qdrant Dashboard

- Open your browser and go to: <http://localhost:6333/dashboard>
- You should see the Qdrant Web UI.

## 6. Test the API (Optional)

- In PowerShell, run:

```powershell
Invoke-RestMethod -Uri "http://localhost:6333"
```

- You should get a JSON response confirming Qdrant is up.

## Useful Commands

| Description   | Command               |
| ------------- | --------------------- |
| Stop Qdrant   | `docker stop qdrant`  |
| Start Qdrant  | `docker start qdrant` |
| View logs     | `docker logs qdrant`  |
| Remove Qdrant | `docker rm -f qdrant` |
