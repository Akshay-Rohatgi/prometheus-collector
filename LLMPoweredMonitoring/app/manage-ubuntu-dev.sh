#!/bin/bash

# Ubuntu Dev Container Management Script
# This script helps deploy and manage the Ubuntu development container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_header() {
    echo -e "${BLUE}[HEADER]${NC} $1"
}

NAMESPACE="llm-powered-monitoring-dev"
DEPLOYMENT_NAME="ubuntu-dev-container"

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy    - Deploy the Ubuntu dev container"
    echo "  delete    - Delete the Ubuntu dev container"
    echo "  exec      - Exec into the Ubuntu container as root"
    echo "  logs      - Show container logs"
    echo "  status    - Show deployment status"
    echo "  restart   - Restart the deployment"
    echo "  help      - Show this help message"
}

# Function to deploy the container
deploy_container() {
    print_header "Deploying Ubuntu Development Container"
    
    print_status "Creating namespace..."
    kubectl apply -f manifests/dev/namespace.yaml
    
    print_status "Creating service account and RBAC..."
    kubectl apply -f manifests/dev/serviceaccount.yaml
    
    print_status "Deploying Ubuntu container..."
    kubectl apply -f manifests/dev/ubuntu-deployment.yaml
    
    print_status "Waiting for deployment to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/$DEPLOYMENT_NAME -n $NAMESPACE
    
    print_status "Ubuntu development container deployed successfully!"
    print_status "To exec into the container, run: $0 exec"
}

# Function to delete the container
delete_container() {
    print_header "Deleting Ubuntu Development Container"
    
    print_status "Deleting deployment..."
    kubectl delete -f manifests/dev/ubuntu-deployment.yaml --ignore-not-found=true
    
    print_status "Deleting service account and RBAC..."
    kubectl delete -f manifests/dev/serviceaccount.yaml --ignore-not-found=true
    
    print_status "Deleting namespace..."
    kubectl delete -f manifests/dev/namespace.yaml --ignore-not-found=true
    
    print_status "Ubuntu development container deleted successfully!"
}

# Function to exec into the container
exec_container() {
    print_header "Exec into Ubuntu Development Container"
    
    # Get the pod name
    POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT_NAME -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [ -z "$POD_NAME" ]; then
        print_error "No running pod found. Please deploy the container first."
        exit 1
    fi
    
    print_status "Exec into pod: $POD_NAME"
    print_status "You will be logged in as root user"
    kubectl exec -it $POD_NAME -n $NAMESPACE -- /bin/bash
}

# Function to show logs
show_logs() {
    print_header "Ubuntu Development Container Logs"
    
    POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT_NAME -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [ -z "$POD_NAME" ]; then
        print_error "No running pod found. Please deploy the container first."
        exit 1
    fi
    
    print_status "Showing logs for pod: $POD_NAME"
    kubectl logs -f $POD_NAME -n $NAMESPACE
}

# Function to show status
show_status() {
    print_header "Ubuntu Development Container Status"
    
    print_status "Namespace status:"
    kubectl get namespace $NAMESPACE 2>/dev/null || print_warning "Namespace not found"
    
    echo ""
    print_status "Deployment status:"
    kubectl get deployment $DEPLOYMENT_NAME -n $NAMESPACE 2>/dev/null || print_warning "Deployment not found"
    
    echo ""
    print_status "Pod status:"
    kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT_NAME 2>/dev/null || print_warning "No pods found"
    
    echo ""
    print_status "Service status:"
    kubectl get service ubuntu-dev-service -n $NAMESPACE 2>/dev/null || print_warning "Service not found"
}

# Function to restart deployment
restart_deployment() {
    print_header "Restarting Ubuntu Development Container"
    
    print_status "Restarting deployment..."
    kubectl rollout restart deployment/$DEPLOYMENT_NAME -n $NAMESPACE
    
    print_status "Waiting for rollout to complete..."
    kubectl rollout status deployment/$DEPLOYMENT_NAME -n $NAMESPACE
    
    print_status "Deployment restarted successfully!"
}

# Main script logic
case "${1:-help}" in
    deploy)
        deploy_container
        ;;
    delete)
        delete_container
        ;;
    exec)
        exec_container
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    restart)
        restart_deployment
        ;;
    help|*)
        show_usage
        ;;
esac
