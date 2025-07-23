# Objective
Convert monitoring plans from Markdown format into structured instruction lists for AI execution.

# Output Format
List of tuples: `[("InstructionType", "content"), ...]`

## Instruction Types
- **KubectlCommand**: `kubectl` commands
- **HelmCommand**: `helm` commands  
- **CreateFile**: File creation instructions
- **Other**: Any other actionable instructions

# Processing Rules
1. Process top-down, one instruction per tuple
2. Skip: Prerequisites, References, "(optional)" sections, explanatory text

# Example
Input: "Create namespace: `kubectl create namespace monitoring`"
Output: `[("KubectlCommand", "kubectl create namespace monitoring")]`

# Available Tools
- `create_add_instruction(type: string, content: string)`: Add instruction to plan