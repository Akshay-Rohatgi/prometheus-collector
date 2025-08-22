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

# Set up Python virtual environment
print_status "Setting up Python virtual environment..."
VENV_DIR="./env"
if [ ! -d "$VENV_DIR" ]; then
    python3.12 -m venv "$VENV_DIR"
    print_status "Virtual environment created at $VENV_DIR"
else
    print_status "Virtual environment already exists at $VENV_DIR"
fi

# Activate virtual environment and install Python dependencies
print_status "Activating virtual environment and installing Python packages..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
pip install --upgrade pip

# Install requirements if requirements.txt exists
if [ -f "requirements.txt" ]; then
    print_status "Installing Python packages from requirements.txt..."
    pip install --no-cache-dir -r requirements.txt
    print_status "Python packages installed successfully"
else
    print_warning "requirements.txt not found in current directory"
fi

# Set environment variables for development
print_status "Setting up environment variables..."
cat > .env << EOF
DEBUG_MODE=true
ENABLE_FILE_LOGGING=false
EOF

print_status "Created .env file with development settings"

# Create a simple activation script for convenience
cat > activate_dev_env.sh << 'EOF'
#!/bin/bash
# Activate the development environment
source ./env/bin/activate
export DEBUG_MODE=true
export ENABLE_FILE_LOGGING=false
echo "Development environment activated!"
echo "Python version: $(python --version)"
echo "Virtual environment: $VIRTUAL_ENV"
EOF

chmod +x activate_dev_env.sh

print_status "Created activation script: activate_dev_env.sh"

echo ""
echo "================================================"
print_status "Development environment setup complete!"
echo "================================================"
echo ""
echo "To activate your development environment, run:"
echo "  source ./activate_dev_env.sh"
echo ""
echo "Or manually activate the virtual environment:"
echo "  source ./env/bin/activate"
echo ""
echo "Installed tools:"
echo "  - Python 3.12 with virtual environment"
echo "  - kubectl (latest stable)"
echo "  - Helm 3"
echo "  - All Python packages from requirements.txt"
echo "  - awesome-prometheus-alerts repository at /opt/awesome-prometheus-alerts"
echo ""
echo "Environment variables set:"
echo "  - DEBUG_MODE=true"
echo "  - ENABLE_FILE_LOGGING=false"
echo ""
print_status "Happy coding! 🚀"
