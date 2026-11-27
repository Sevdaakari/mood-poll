# mood-poll 😊

A small web app, "How was your day?" with three answers (good / ok / bad), deployed end to end: automated tests, a Docker image published on every release, and a one-click deployment to a server on AWS.

![CI](https://github.com/Sevdaakari/mood-poll/actions/workflows/ci.yml/badge.svg)

## Stack

- **Backend:** Python, FastAPI, SQLite
- **Frontend:** a single static page (HTML + CSS)
- **Packaging:** Docker, image published to GitHub Container Registry
- **CI/CD:** GitHub Actions
- **Hosting:** AWS EC2

## API

| Method | Path | Description |
|---|---|---|
| GET | `/` | The poll page |
| POST | `/vote` | Save a vote (`good`, `ok` or `bad`) |
| GET | `/stats` | Vote counts |
| GET | `/health` | Health check, used by the deployment |

The server validates every answer itself and rejects anything outside the three allowed values.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn main:app --reload      # http://127.0.0.1:8000
pytest                         # tests
ruff check .                   # lint
```

The database location is set by the `DB_PATH` environment variable (default: `votes.db`). Tests use FastAPI's `TestClient`, so no running server is needed.

## Run in Docker

```bash
docker build -t mood-poll .
docker run -d --name mood-poll -p 8000:8000 -v mood-poll-data:/data mood-poll
```

Votes are stored in a Docker volume mounted at `/data`, so they survive container re-creation and image updates.

## CI/CD

```
git push ──► CI (GitHub Actions)
              ├─ test:    ruff + pytest
              └─ publish: build Docker image ──► ghcr.io/sevdaakari/mood-poll
                                                          │
          Deploy workflow (manual trigger) ──► SSH ──► AWS EC2: pull image, restart container
```

**CI** (`.github/workflows/ci.yml`) runs on every push: it lints and tests the code. On `main`, once the tests pass, it builds the Docker image and publishes it with two tags: `latest` and the commit SHA.

**Deploy** (`.github/workflows/deploy.yml`) is triggered manually (Continuous Delivery). It connects to the server over SSH, pulls the latest image, recreates the container with the same volume, and calls `/health`. If the app does not respond, the job fails.

Server credentials are kept in GitHub Actions secrets (`EC2_HOST`, `EC2_USER`, `EC2_SSH_KEY`). The pipeline uses a dedicated deploy key, separate from personal access, so it can be revoked on its own.

## Infrastructure

- AWS EC2 `t3.micro`, Amazon Linux 2023, region `eu-north-1`
- Docker on the instance; the container restarts automatically after a reboot (`--restart unless-stopped`)
- Security group: SSH (22) and the application port (8000)

## Next improvements

- Domain name and HTTPS (reverse proxy)
- Elastic IP, so the server address stays the same after a restart
- Tighter SSH access, for example AWS SSM instead of an open SSH port
- A managed database instead of SQLite if the traffic grows