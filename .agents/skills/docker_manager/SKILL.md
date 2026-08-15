---
name: docker_manager
description: Skill for configuring Dockerfiles, updating docker-compose setups, and managing container environments.
---

# Skill: Docker Manager

Use this skill whenever changes are made to requirements, filesystems, database mounts, or container configuration.

## Key Rules & Constraints

1. **Volume & Code Copy Alignment**:
   - If a new configuration directory, database file, or static asset folder is added to the workspace root, verify that `docker/Dockerfile.backend` and `docker/Dockerfile.frontend` are updated to include them if they need to be packaged.
2. **Live Code & Mount Validation**:
   - Ensure `docker-compose.yml` mounts active development code and test directories:
     - `- ./backend:/app/backend`
     - `- ./tests:/app/tests`
     - `- ./configs:/app/configs`
     - `- ./data:/app/data`
   - Live mounts guarantee that edits to Python code or prompt files on host are instantly reflected inside container memory when force-recreated.


---

## Playbook 1: Updating Docker on Dependency Change

When new Python libraries are added to `requirements.txt`:

1. Rebuild and restart the container stack in detached mode:
   ```powershell
   docker compose up --build -d
   ```
2. Verify container logs to make sure no import or startup errors occur:
   ```powershell
   docker compose logs backend
   docker compose logs frontend
   ```
3. Check containers health:
   ```powershell
   docker compose ps
   ```

---

## Playbook 2: Docker Environment Verification

1. Ensure the frontend container gets the correct `BACKEND_URL`:
   - Environment variables must specify `BACKEND_URL=http://backend:8001` inside the compose service definition.
2. Check that the backend healthcheck is passing:
   - Command: `docker compose ps` (should show `(healthy)` next to the backend status).
