#!/bin/bash
# Deployment script for Reachy Emotion Detection on Jetson Xavier NX
# Run this script on the Jetson device

set -e

echo "========================================="
echo "Reachy Emotion Detection - Deployment"
echo "========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
PROJECT_DIR="/home/reachy/reachy_emotion"
SERVICE_NAME="reachy-emotion"
GATEWAY_URL="${GATEWAY_URL:-http://10.0.4.140:8000}"
DEVICE_ID="${DEVICE_ID:-reachy-mini-01}"

echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check if running on Jetson
if ! command -v tegrastats &> /dev/null; then
    echo -e "${RED}Warning: tegrastats not found. Are you on a Jetson device?${NC}"
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found${NC}"

# Check DeepStream
if ! command -v deepstream-app &> /dev/null; then
    echo -e "${YELLOW}Warning: DeepStream not found. Install JetPack 5.1+ with DeepStream 6.2${NC}"
fi

echo -e "${YELLOW}Creating project directory...${NC}"
sudo mkdir -p "$PROJECT_DIR"
sudo chown -R reachy:reachy "$PROJECT_DIR"

echo -e "${YELLOW}Copying files...${NC}"
# In production, this would rsync from build server
# For now, assume files are already in place
if [ -d "jetson" ]; then
    cp -r jetson/* "$PROJECT_DIR/"
    echo -e "${GREEN}✓ Files copied${NC}"
fi

echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip3 install --user python-socketio aiohttp || true

echo -e "${YELLOW}Setting up systemd service...${NC}"
sudo cp "$PROJECT_DIR/systemd/${SERVICE_NAME}.service" /etc/systemd/system/
sudo systemctl daemon-reload
echo -e "${GREEN}✓ Service installed${NC}"

echo -e "${YELLOW}Configuring service...${NC}"
# Update service file with actual paths
sudo sed -i "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_DIR|g" "/etc/systemd/system/${SERVICE_NAME}.service"
sudo sed -i "s|ExecStart=.*|ExecStart=/usr/bin/python3 $PROJECT_DIR/emotion_main.py --config $PROJECT_DIR/deepstream/emotion_pipeline.txt --gateway $GATEWAY_URL --device-id $DEVICE_ID|g" "/etc/systemd/system/${SERVICE_NAME}.service"

echo -e "${YELLOW}Enabling service...${NC}"
sudo systemctl enable "$SERVICE_NAME"
echo -e "${GREEN}✓ Service enabled (will start on boot)${NC}"

echo -e "${YELLOW}Starting service...${NC}"
sudo systemctl start "$SERVICE_NAME"

# Wait a moment for service to start
sleep 2

# Check status
if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${GREEN}✓ Service is running${NC}"
else
    echo -e "${RED}✗ Service failed to start${NC}"
    echo "Check logs with: sudo journalctl -u $SERVICE_NAME -f"
    exit 1
fi

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Service Status:"
sudo systemctl status "$SERVICE_NAME" --no-pager | head -n 10
echo ""
echo "Useful Commands:"
echo "  Status:  sudo systemctl status $SERVICE_NAME"
echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
echo "  Restart: sudo systemctl restart $SERVICE_NAME"
echo ""
echo -e "${GREEN}Deployment successful!${NC}"
