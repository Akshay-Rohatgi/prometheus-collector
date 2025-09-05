#!/bin/bash

# Ubuntu Development Environment Setup Script
# This script configures an Ubuntu system similar to the Dockerfile setup
# for development purposes (without appuser setup)

set -e  # Exit on any error

echo "================================================"
echo "Setting up Ubuntu Development Environment"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}


print_status "Updating package lists..."
apt-get update

print_status "Installing system dependencies..."
apt-get install -y \
    gcc \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    git \
    python3.12 \
    python3.12-dev \
    python3.12-venv \
    python3-pip \
    software-properties-common \
    nodejs \
    npm

# clone the repository
git clone https://github.com/Akshay-Rohatgi/prometheus-collector.git 

# Install kubectl
print_status "Installing kubectl..."
if ! command -v kubectl &> /dev/null; then
    KUBECTL_VERSION=$(curl -L -s https://dl.k8s.io/release/stable.txt)
    curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
    chmod +x kubectl
    mv kubectl /usr/local/bin/
    print_status "kubectl installed successfully"
else
    print_status "kubectl is already installed"
fi

# Install Helm
print_status "Installing Helm..."
if ! command -v helm &> /dev/null; then
    curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
    print_status "Helm installed successfully"
else
    print_status "Helm is already installed"
fi

# Add prometheus-community repository
print_status "Adding prometheus-community Helm repository..."
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Clone awesome-prometheus-alerts repository
print_status "Cloning awesome-prometheus-alerts repository..."
ALERTS_DIR="/opt/awesome-prometheus-alerts"
if [ ! -d "$ALERTS_DIR" ]; then
    git clone https://github.com/samber/awesome-prometheus-alerts.git "$ALERTS_DIR"
    chmod -R 755 "$ALERTS_DIR"
    print_status "awesome-prometheus-alerts cloned to $ALERTS_DIR"
else
    print_status "awesome-prometheus-alerts already exists at $ALERTS_DIR"
fi

# install az-prom-rules-converter
npm i -g https://gitpkg.now.sh/Azure/prometheus-collector/tools/az-prom-rules-converter?main

export DEBUG_MODE=true
export ENABLE_FILE_LOGGING=false

print_status "Happy coding! 🚀"
