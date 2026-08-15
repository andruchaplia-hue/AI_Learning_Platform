# Mandatory Docker Test Runner Script
# Ensures backend container is running, then executes pytest inside Docker.

Write-Host "Ensuring Docker backend container is up..." -ForegroundColor Cyan
docker compose up -d backend

Write-Host "Executing pytest suite inside Docker container..." -ForegroundColor Green
docker compose exec -T backend pytest tests/ -v
