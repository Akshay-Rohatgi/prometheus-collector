# Knowledge Index

## Context Files Overview

This directory contains comprehensive documentation for the LLM-Powered Monitoring System. Each file serves a specific purpose in documenting different aspects of the system, providing complete knowledge for future agents and developers.

### Core Architecture and Design
1. **ARCHITECTURE.md** - Complete system architecture, components, and design patterns
   - FastAPI application structure
   - LangGraph workflow orchestration
   - Agent-based monitoring system design
   - Azure OpenAI integration architecture

### AI and Workflow Management
2. **AI_AGENTS.md** - Comprehensive AI agent documentation
   - Agent roles and responsibilities
   - LangGraph workflow implementation
   - Tool integration and usage
   - State management and routing

3. **WORKFLOW_STATES.md** - Workflow state management and transitions
   - State definitions and lifecycle
   - Transition conditions and routing
   - Interrupt handling and user interaction
   - Error handling and recovery

### API and Integration
4. **API_REFERENCE.md** - Complete API documentation
   - REST endpoint specifications
   - Request/response schemas
   - Authentication and security
   - Error handling and status codes

5. **KUBERNETES_INTEGRATION.md** - Kubernetes integration guide
   - Service discovery implementation
   - Workload detection algorithms
   - RBAC and security configurations
   - Resource management patterns

### Deployment and Operations
6. **DEPLOYMENT_GUIDE.md** - Complete deployment procedures
   - Environment setup and configuration
   - Docker containerization
   - Kubernetes manifest management
   - Production deployment strategies

7. **CONFIGURATION_REFERENCE.md** - Configuration management guide
   - Environment variable documentation
   - Model configuration options
   - Azure service integration settings
   - Security and authentication configuration

### Development and Testing
8. **TESTING_GUIDE.md** - Comprehensive testing framework
   - DeepEval integration and custom metrics
   - AI agent testing procedures
   - Integration testing strategies
   - Performance testing and benchmarks

9. **TROUBLESHOOTING.md** - Complete troubleshooting guide
   - Common issues and solutions
   - Diagnostic procedures and tools
   - Performance optimization techniques
   - System health monitoring

### Logging and Monitoring
10. **LOGGING_README.md** - Logging configuration and best practices
    - Structured logging implementation
    - Log levels and message formatting
    - Centralized logging strategies
    - Debug and performance monitoring

### Utilities and Tools
11. **MARKDOWN_PARSER_DIAGNOSIS.md** - Markdown parsing utilities
    - Parser implementation details
    - Error handling and validation
    - Content extraction algorithms
    - Tool integration patterns

## Quick Navigation Guide

### For New Developers
**Recommended Reading Order:**
1. Start with: **ARCHITECTURE.md** - Understand overall system design
2. Continue with: **AI_AGENTS.md** - Learn AI workflow implementation
3. Review: **API_REFERENCE.md** - Understand API interactions
4. Study: **WORKFLOW_STATES.md** - Master state management
5. Practice with: **TESTING_GUIDE.md** - Learn testing procedures

### For DevOps Engineers
**Essential Documents:**
1. **DEPLOYMENT_GUIDE.md** - Complete deployment procedures
2. **KUBERNETES_INTEGRATION.md** - K8s configuration and management
3. **CONFIGURATION_REFERENCE.md** - Environment and service setup
4. **TROUBLESHOOTING.md** - Operational issue resolution
5. **LOGGING_README.md** - Monitoring and observability

### For AI/ML Engineers
**Core Resources:**
1. **AI_AGENTS.md** - Agent development and workflow design
2. **TESTING_GUIDE.md** - AI-specific testing and evaluation
3. **ARCHITECTURE.md** - AI system integration patterns
4. **WORKFLOW_STATES.md** - State machine and decision logic
5. **TROUBLESHOOTING.md** - AI agent debugging techniques

### For API Developers
**Key References:**
1. **API_REFERENCE.md** - Complete endpoint documentation
2. **ARCHITECTURE.md** - API architecture and patterns
3. **CONFIGURATION_REFERENCE.md** - API configuration options
4. **TESTING_GUIDE.md** - API testing procedures
5. **TROUBLESHOOTING.md** - API issue resolution

### For Troubleshooting and Support
**Diagnostic Workflow:**
1. **TROUBLESHOOTING.md** - Primary troubleshooting resource
2. **LOGGING_README.md** - Log analysis and interpretation
3. **CONFIGURATION_REFERENCE.md** - Configuration validation
4. **KUBERNETES_INTEGRATION.md** - K8s connectivity issues
5. **API_REFERENCE.md** - API error codes and solutions

## System Overview Summary

The LLM-Powered Monitoring System is a sophisticated Azure Kubernetes Service monitoring solution that uses AI agents to:

### Core Capabilities
- **Automatic OSS Workload Detection**: Discovers open-source services in Kubernetes clusters
- **Intelligent Monitoring Plan Generation**: Creates tailored Prometheus monitoring configurations
- **Automated Deployment**: Executes monitoring setup using Helm charts and kubectl
- **Plan Evaluation and Optimization**: AI-driven monitoring plan assessment and improvement

### Technology Stack
- **Backend**: FastAPI with Python 3.12
- **AI Orchestration**: LangGraph for workflow management
- **AI Models**: Azure OpenAI (GPT-4o, GPT-5)
- **Container Platform**: Kubernetes with Docker
- **Deployment**: Helm charts and kubectl automation
- **Testing**: DeepEval framework with custom metrics
- **Monitoring**: Structured logging with Azure integration

### Key Components
- **Workflow Engine**: State-based AI agent orchestration
- **Kubernetes Client**: Service discovery and cluster interaction
- **AI Agents**: Specialized agents for detection, planning, and evaluation
- **Deployment Controller**: Automated infrastructure provisioning
- **API Layer**: RESTful interface for workflow management

### Security Features
- **RBAC Integration**: Kubernetes role-based access control
- **Secret Management**: Azure Key Vault and Kubernetes secrets
- **API Authentication**: Secure token-based authentication
- **Network Security**: Namespace isolation and network policies

This comprehensive documentation ensures that any future agent or developer can quickly understand, maintain, and extend the LLM-Powered Monitoring System effectively.
