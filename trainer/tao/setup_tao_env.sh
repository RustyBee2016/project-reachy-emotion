#!/bin/bash
# TAO Environment Setup Script
# Sets up NVIDIA TAO Toolkit containers for EmotionNet training

set -e

echo "========================================="
echo "NVIDIA TAO Toolkit Environment Setup"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker found${NC}"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose found${NC}"

# Check NVIDIA Docker runtime
if ! docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
    echo -e "${RED}Error: NVIDIA Docker runtime not available${NC}"
    echo "Please install nvidia-container-toolkit"
    exit 1
fi
echo -e "${GREEN}✓ NVIDIA Docker runtime available${NC}"

# Check GPU
GPU_COUNT=$(nvidia-smi --query-gpu=count --format=csv,noheader | head -n 1)
if [ "$GPU_COUNT" -eq 0 ]; then
    echo -e "${RED}Error: No GPUs detected${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Found $GPU_COUNT GPU(s)${NC}"

# Create required directories
echo -e "${YELLOW}Creating directory structure...${NC}"

mkdir -p specs
mkdir -p experiments
mkdir -p ../../jetson/engines
mkdir -p ../../mlruns

echo -e "${GREEN}✓ Directories created${NC}"

# Pull TAO images
echo -e "${YELLOW}Pulling TAO Docker images (this may take a while)...${NC}"

echo "Pulling TAO 4.0.0 (training)..."
docker pull nvcr.io/nvidia/tao/tao-toolkit:4.0.0-tf2.11.0

echo "Pulling TAO 5.3.0 (export)..."
docker pull nvcr.io/nvidia/tao/tao-toolkit:5.3.0-pyt

echo -e "${GREEN}✓ TAO images pulled${NC}"

# Start containers
echo -e "${YELLOW}Starting TAO containers...${NC}"

docker-compose -f docker-compose-tao.yml up -d

# Wait for containers to be healthy
echo -e "${YELLOW}Waiting for containers to be ready...${NC}"
sleep 5

# Check container status
if docker ps | grep -q reachy-tao-train; then
    echo -e "${GREEN}✓ TAO training container running${NC}"
else
    echo -e "${RED}✗ TAO training container failed to start${NC}"
    docker-compose -f docker-compose-tao.yml logs tao-train
    exit 1
fi

if docker ps | grep -q reachy-tao-export; then
    echo -e "${GREEN}✓ TAO export container running${NC}"
else
    echo -e "${RED}✗ TAO export container failed to start${NC}"
    docker-compose -f docker-compose-tao.yml logs tao-export
    exit 1
fi

# Verify GPU access in containers
echo -e "${YELLOW}Verifying GPU access in containers...${NC}"

if docker exec reachy-tao-train nvidia-smi &> /dev/null; then
    echo -e "${GREEN}✓ GPU accessible in training container${NC}"
else
    echo -e "${RED}✗ GPU not accessible in training container${NC}"
    exit 1
fi

if docker exec reachy-tao-export nvidia-smi &> /dev/null; then
    echo -e "${GREEN}✓ GPU accessible in export container${NC}"
else
    echo -e "${RED}✗ GPU not accessible in export container${NC}"
    exit 1
fi

# Display container info
echo ""
echo "========================================="
echo "TAO Environment Ready!"
echo "========================================="
echo ""
echo "Running containers:"
docker ps --filter "name=reachy-tao" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "GPU Status:"
docker exec reachy-tao-train nvidia-smi --query-gpu=index,name,memory.total,memory.used --format=csv,noheader
echo ""
echo "Usage:"
echo "  Training:  docker exec -it reachy-tao-train bash"
echo "  Export:    docker exec -it reachy-tao-export bash"
echo "  Stop:      docker-compose -f docker-compose-tao.yml down"
echo "  Logs:      docker-compose -f docker-compose-tao.yml logs -f"
echo ""
echo -e "${GREEN}Setup complete!${NC}"
