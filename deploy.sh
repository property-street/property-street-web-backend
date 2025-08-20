#!/bin/bash
set -e

# ========== CONFIG ==========
SERVICE_NAME="backend"   # 👈 you can parameterize this later
CONTAINER_NAME="$SERVICE_NAME"

# Resolve script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Paths relative to script location
ENV_FILE="$SCRIPT_DIR/.env"

# Ensure .env exists
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ .env file not found at $ENV_FILE"
  exit 1
fi

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

set -e
trap 'log "❌ Something went wrong during deployment"' ERR

# Load all env vars (both GIT_ACTION_* and app vars)
set -o allexport
source "$ENV_FILE"
set +o allexport

# Check required GitHub Actions env vars
: "${GIT_ACTION_DOCKER_USERNAME:?Environment variable GIT_ACTION_DOCKER_USERNAME is required}"
: "${GIT_ACTION_DOCKER_PASSWORD:?Environment variable GIT_ACTION_DOCKER_PASSWORD is required}"
: "${GIT_ACTION_AWS_SERVER_USER:?Environment variable GIT_ACTION_AWS_SERVER_USER is required}"
: "${GIT_ACTION_AWS_SERVER_HOST:?Environment variable GIT_ACTION_AWS_SERVER_HOST is required}"
: "${GIT_ACTION_COMPOSE_PROJECT_DIR_NAME:?Environment variable GIT_ACTION_COMPOSE_PROJECT_DIR_NAME is required}"
: "${GIT_ACTION_AWS_SSH_KEY_PATH:?Environment variable GIT_ACTION_AWS_SSH_KEY_PATH is required}"

# Vars
IMAGES=(
  crankgig/property_street_docker_hub_fastapi_repo:latest
)

log "🚀 Starting deployment..."

# Upload docker-compose.yml + filtered env file
log "📤 Preparing env file for service '$SERVICE_NAME'..."
FILTERED_ENV_FILE="$SCRIPT_DIR/${SERVICE_NAME}.env"
grep -v '^GIT_ACTION_' "$ENV_FILE" > "$FILTERED_ENV_FILE"

log "📤 Uploading docker-compose.yml and env file to remote server..."
ssh -i "$GIT_ACTION_AWS_SSH_KEY_PATH" -o StrictHostKeyChecking=no "$GIT_ACTION_AWS_SERVER_USER@$GIT_ACTION_AWS_SERVER_HOST" "mkdir -p ~/$GIT_ACTION_COMPOSE_PROJECT_DIR_NAME"
scp -i "$GIT_ACTION_AWS_SSH_KEY_PATH" "$SCRIPT_DIR/docker-compose.yml" "$GIT_ACTION_AWS_SERVER_USER@$GIT_ACTION_AWS_SERVER_HOST:~/$GIT_ACTION_COMPOSE_PROJECT_DIR_NAME/docker-compose.yml"
scp -i "$GIT_ACTION_AWS_SSH_KEY_PATH" "$FILTERED_ENV_FILE" "$GIT_ACTION_AWS_SERVER_USER@$GIT_ACTION_AWS_SERVER_HOST:~/$GIT_ACTION_COMPOSE_PROJECT_DIR_NAME/.${SERVICE_NAME}.env"

# Remote deployment
log "🔐 Connecting to EC2 instance and deploying..."
ssh -i "$GIT_ACTION_AWS_SSH_KEY_PATH" -o StrictHostKeyChecking=no "$GIT_ACTION_AWS_SERVER_USER@$GIT_ACTION_AWS_SERVER_HOST" << EOF
  set -e
  cd "$GIT_ACTION_COMPOSE_PROJECT_DIR_NAME"

  log() { echo "[\$(date '+%Y-%m-%d %H:%M:%S')] \$1"; }

  if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
  elif docker-compose version &> /dev/null; then
    COMPOSE="docker-compose"
  else
    log "⚠️ Docker Compose not found. Installing..."
    if [ -f /etc/os-release ] && grep -qi 'amazon linux' /etc/os-release; then
      sudo dnf install -y docker-compose
    else
      log "❌ Cannot auto-install docker-compose on this OS. Install manually."
      exit 1
    fi
    COMPOSE="docker-compose"
  fi

  log "📥 Pulling latest Docker image..."
  for img in "${IMAGES[@]}"; do
    docker pull "$img"
  done

  log "🛑 Stopping old containers..."
  \$COMPOSE down || true

  log "🚀 Starting new containers with env file: ${SERVICE_NAME}.env..."
  \$COMPOSE --env-file ${SERVICE_NAME}.env up -d --force-recreate

  log "✅ Remote deployment complete. Container: $CONTAINER_NAME"
EOF

log "🎉 CI/CD deployment finished!"
