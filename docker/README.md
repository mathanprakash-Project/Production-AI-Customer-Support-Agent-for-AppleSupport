# TweetSupport Docker Compose Stack

This folder contains the complete multi-container Docker Compose setup for the **TweetSupport AI Customer Support Agent** project. Running this folder boots the entire stack:
1. **Frontend**: React 18 + Vite Support Workspace on [http://localhost:5173](http://localhost:5173)
2. **Backend**: FastAPI REST service with RAG pipeline on [http://localhost:8000](http://localhost:8000)
3. **Database**: PostgreSQL 16 with `pgvector` on port `5433` (container port 5432)
4. **LLM Provider**: Ollama container running `llama3.2:3b` on port `11435` (container port 11434)

---

## How to Run

### Method 1: Double-click or run the batch file
In Windows File Explorer or Command Prompt:
* Double-click **`start.bat`** (or `run.bat`) to start all services.
* Double-click **`stop.bat`** to shut down all services.

### Method 2: PowerShell
```powershell
cd docker
.\start.ps1
```
To stop:
```powershell
.\stop.ps1
```

### Method 3: Standard Docker Compose CLI
```bash
cd docker
docker compose up -d
```
To stop:
```bash
docker compose down
```

---

## Access & Credentials

* **Frontend UI**: [http://localhost:5173](http://localhost:5173)
* **API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### Login Accounts
* **Support Agent**: `agent@tweetsupport.local` / `agent123`
* **Admin**: `admin@tweetsupport.local` / `admin123`
