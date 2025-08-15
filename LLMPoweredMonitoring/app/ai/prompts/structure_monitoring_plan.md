# Objective
Convert monitoring plans from Markdown format into structured instruction objects for AI execution.

# Output Format
List of instruction objects with specific types and attributes.

## Instruction Types
- **kubectl**: Commands to be executed with kubectl
  - Use: `create_add_instruction("kubectl", "command content")`
- **helm**: Commands to be executed with helm
  - Use: `create_add_instruction("helm", "command content")`
- **create_file**: File creation instructions
  - Use: `create_add_instruction("create_file", "file content", "filename")`
- **other**: Any other actionable instructions
  - Use: `create_add_instruction("other", "instruction content")`

> Note: For Helm commands, if it is not already specified, please include the following commands:
> - `helm repo add prometheus-community https://prometheus-community.github.io/helm-charts`
> - `helm repo update`

# Processing Rules
1. Process top-down, one instruction per call
2. Skip: Prerequisites, References, "(optional)" sections, explanatory text
3. For file creation, extract filename and content separately

# Examples
Input: "Create namespace: `kubectl create namespace monitoring`"
Output: `create_add_instruction("kubectl", "kubectl create namespace monitoring")`

Input: "Create values.yaml file with content: `prometheus: enabled: true`"
Output: `create_add_instruction("create_file", "prometheus:\n  enabled: true", "values.yaml")`

# Available Tools
- `create_add_instruction(type: string, content: string, filename: string = None)`: Add instruction to plan
  - type: "kubectl", "helm", "create_file", or "other"
  - content: The actual instruction content
  - filename: Required only for "create_file" type