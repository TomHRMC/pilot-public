#!/bin/bash
# GPU Instance Bootstrap Script
# Runs on first boot of the g4dn.xlarge Deep Learning AMI
# Services: Whisper (faster-whisper-server CUDA) + Ollama (llama3.1:8b)
# ⚠️  llama3.1:8b pull takes 5–15 minutes (~4.7GB download)

set -euo pipefail

exec > >(tee /var/log/pilot-gpu-userdata.log) 2>&1
echo "=== Pilot GPU Bootstrap started at $(date) ==="
echo "Region: ${aws_region}"

# Mount model storage EBS volume (/dev/xvdb → /models)
if ! blkid /dev/xvdb; then
  echo "Formatting /dev/xvdb as ext4..."
  mkfs.ext4 /dev/xvdb
fi
mkdir -p /models
mount /dev/xvdb /models
echo "/dev/xvdb /models ext4 defaults,nofail 0 2" >> /etc/fstab

# Docker should be pre-installed on Deep Learning AMI
# Verify NVIDIA runtime is available
docker info | grep -i nvidia || echo "WARNING: NVIDIA runtime not detected — verify Deep Learning AMI"

# Install Docker Compose v2
# Note: Use $${COMPOSE_VERSION} — double-dollar escapes Terraform templatefile interpolation
# so bash sees the literal variable reference at runtime (not interpolated by Terraform)
COMPOSE_VERSION="2.27.0"
curl -SL "https://github.com/docker/compose/releases/download/v$${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
docker-compose version

# Create docker-compose file for AI services
mkdir -p /home/ec2-user/pilot-gpu
cat > /home/ec2-user/pilot-gpu/docker-compose.yml << 'EOF'
version: '3.8'

services:
  whisper:
    image: fedirz/faster-whisper-server:latest-cuda
    container_name: pilot-whisper
    ports:
      - "8080:8000"
    environment:
      # faster-whisper-server reads nested settings with a double underscore
      - WHISPER__MODEL=${whisper_model}
    volumes:
      - /models/whisper:/root/.cache/huggingface
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s

  ollama:
    image: ollama/ollama:latest
    container_name: pilot-ollama
    ports:
      - "11434:11434"
    volumes:
      - /models/ollama:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
EOF

chown -R ec2-user:ec2-user /home/ec2-user/pilot-gpu

# Start AI services
cd /home/ec2-user/pilot-gpu
docker-compose up -d
echo "AI services started — Whisper on :8080, Ollama on :11434"

# Pull Ollama model (async — takes 5-15 min)
# Wait for Ollama to be ready, then pull llama3.1:8b
(
  echo "Waiting for Ollama to be ready..."
  for i in $(seq 1 30); do
    if curl -sf http://localhost:11434 > /dev/null 2>&1; then
      echo "Ollama is ready — pulling llama3.1:8b..."
      docker exec pilot-ollama ollama pull llama3.1:8b
      echo "llama3.1:8b pull complete"
      break
    fi
    echo "Attempt $i/30 — Ollama not ready yet, waiting 10s..."
    sleep 10
  done
) &

# Create systemd service for auto-start on reboot
cat > /etc/systemd/system/pilot-gpu.service << 'EOF'
[Unit]
Description=Pilot GPU AI Services (Whisper + Ollama)
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ec2-user/pilot-gpu
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=ec2-user

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable pilot-gpu.service

echo "=== Pilot GPU Bootstrap complete at $(date) ==="
echo "GPU VRAM usage estimate: Whisper ~1.5GB + Ollama llama3.1:8b ~4.7GB = ~6.2GB / 16GB T4"
echo "Monitor: docker stats"
echo "Logs: docker logs pilot-whisper && docker logs pilot-ollama"
