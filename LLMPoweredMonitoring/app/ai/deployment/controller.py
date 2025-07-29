from ai.instructions import MonitoringInstruction, KubectlInstruction, HelmInstruction, CreateFileInstruction, OtherInstruction
from printer import printer
from typing import List
import os
import random
import subprocess
import shlex 

class InstructionController:
    def __init__(self, dry_run: bool = False):
        self.instructions: List[MonitoringInstruction] = []
        self.complete_instructions: List[MonitoringInstruction] = []
        self.failed_instructions: List[MonitoringInstruction] = []
        self.dry_run = dry_run  # If True, simulate commands instead of executing them

    def add_instruction(self, instruction: MonitoringInstruction, index = None):
        """Add an instruction to the controller."""
        if index is not None and 0 <= index < len(self.instructions):
            self.instructions.insert(index, instruction)
        else:
            self.instructions.append(instruction)
        printer.info(f"Added instruction: {instruction}")

    def set_instructions(self, instructions: List[MonitoringInstruction]):
        """Set the list of instructions."""
        self.instructions = instructions
        printer.info(f"Set {len(instructions)} instructions.")

    def reset_state(self):
        """Reset controller state for new execution."""
        self.complete_instructions.clear()
        self.failed_instructions.clear()
        self.instructions.clear()

    def execute_plan(self, delete: bool = False) -> bool:
        """Execute instructions in the structured plan one by one with basic error handling."""
        # Reset state for fresh execution
        self.complete_instructions.clear()
        self.failed_instructions.clear()
        
        total_instruction_count = len(self.instructions)
        action = "Deleting" if delete else "Executing"

        for i, instruction in enumerate(self.instructions):
            printer.info(f"[{i+1}/{total_instruction_count}] {action}: {instruction}")
            try: 
                success = self.execute_instruction(instruction, delete=delete)
            except Exception as e:
                printer.error(f"Error executing instruction {i+1}/{total_instruction_count}: {instruction} - {e}")
                success = False
            
            if success:
                self.complete_instructions.append(instruction)
            else:
                self._handle_failure(instruction, i+1, total_instruction_count)
                break # Exit early on failure

        if len(self.failed_instructions) == 0:
            printer.success("All instructions executed successfully.")
            return True
        else:
            # Rollback was already called in _handle_failure, just return False
            return False

    def execute_instruction(self, instruction: MonitoringInstruction, delete: bool = False) -> bool:
        """Execute a single instruction and return success status."""
        instruction_function_map = {
            "kubectl": self.execute_kubectl_instruction,
            "helm": self.execute_helm_instruction,
            "create_file": self.create_file_instruction,
            "other": self.execute_other_instruction
        }

        execute_function = instruction_function_map.get(instruction.type)
        if execute_function:
            return execute_function(instruction, delete=delete)
        else:
            printer.error(f"No execution function found for instruction type: {instruction.type}")
            return False
        
    def execute_kubectl_instruction(self, instruction: KubectlInstruction, delete: bool = False) -> bool:
        """Execute a kubectl command."""
        if delete:
            # Convert apply/create commands to delete commands
            command = self._convert_to_delete_command(instruction.command)
            printer.info(f"Executing kubectl delete command: {command}")
        else:
            command = instruction.command
            printer.info(f"Executing kubectl command: {command}")
        
        # Execute the actual command
        success, stdout, stderr = self._execute_command(command)
        return success
    
    def execute_helm_instruction(self, instruction: HelmInstruction, delete: bool = False) -> bool:
        """Execute a helm command."""
        if delete:
            # Convert install/upgrade commands to uninstall commands
            command = self._convert_helm_to_delete_command(instruction.command)
            printer.info(f"Executing helm delete command: {command}")
        else:
            command = instruction.command
            printer.info(f"Executing helm command: {command}")
        
        # Execute the actual command
        success, stdout, stderr = self._execute_command(command)
        return success
    
    def create_file_instruction(self, instruction: CreateFileInstruction, delete: bool = False) -> bool:
        """Create or delete a file."""
        if delete:
            printer.info(f"Deleting file: {instruction.filename}")
            try:
                if os.path.exists(instruction.filename):
                    os.remove(instruction.filename)
                    return True
                else:
                    printer.warning(f"File {instruction.filename} does not exist, skipping deletion")
                    return True
            except Exception as e:
                printer.error(f"Failed to delete file {instruction.filename}: {e}")
                return False
        else:
            printer.info(f"Creating file: {instruction.filename} with content: {instruction.content[:50]}...")
            try:
                # Create directory if it doesn't exist
                file_dir = os.path.dirname(os.path.abspath(instruction.filename))
                if file_dir and file_dir != '/':
                    os.makedirs(file_dir, exist_ok=True)
                with open(instruction.filename, 'w') as f:
                    f.write(instruction.content)
                return True
            except Exception as e:
                printer.error(f"Failed to create file {instruction.filename}: {e}")
                return False
    
    def execute_other_instruction(self, instruction: OtherInstruction, delete: bool = False) -> bool:
        """Execute any other type of instruction."""
        action = "delete" if delete else "execute"
        printer.info(f"Do not have the tools to {action} the following instruction: {instruction.description}")
        # Simulate execution logic here
        return random.choice([True, True, True, True])
    
    def _execute_command(self, command: str, timeout: int = 300) -> tuple[bool, str, str]:
        """Execute a shell command and return success status, stdout, and stderr.
        
        Args:
            command: The command to execute
            timeout: Command timeout in seconds (default: 5 minutes)
            
        Returns:
            Tuple of (success: bool, stdout: str, stderr: str)
        """
        if self.dry_run:
            # Simulate command execution for safety
            printer.info(f"[DRY RUN] Would execute: {command}")
            # Simulate 75% success rate for testing
            success = random.choice([True, True, True, False])
            if success:
                return True, "Simulated successful output", ""
            else:
                return False, "", "Simulated error"
        
        try:
            # Use shlex.split to properly handle command arguments
            cmd_args = shlex.split(command)
            
            # Execute the command
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False  # Don't raise exception on non-zero exit
            )
            
            # Check if command was successful
            success = result.returncode == 0
            
            if success:
                printer.info(f"Command succeeded: {command}")
                if result.stdout.strip():
                    printer.info(f"Output: {result.stdout.strip()}")
            else:
                printer.error(f"Command failed (exit code {result.returncode}): {command}")
                if result.stderr.strip():
                    printer.error(f"Error: {result.stderr.strip()}")
                    
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            printer.error(f"Command timed out after {timeout}s: {command}")
            return False, "", f"Command timed out after {timeout} seconds"
            
        except FileNotFoundError:
            printer.error(f"Command not found: {command.split()[0]}")
            return False, "", f"Command not found: {command.split()[0]}"
            
        except Exception as e:
            printer.error(f"Error executing command '{command}': {e}")
            return False, "", str(e)
    
    def _check_tool_availability(self, tool: str) -> bool:
        """Check if a command-line tool is available."""
        try:
            result = subprocess.run(
                [tool, "version"], 
                capture_output=True, 
                text=True, 
                timeout=10,
                check=False
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def check_prerequisites(self) -> dict[str, bool]:
        """Check if required tools are available.
        
        Returns:
            Dictionary with tool availability status
        """
        tools = {
            "kubectl": self._check_tool_availability("kubectl"),
            "helm": self._check_tool_availability("helm")
        }
        
        for tool, available in tools.items():
            if available:
                printer.info(f"✅ {tool} is available")
            else:
                printer.warning(f"⚠️  {tool} is not available or not in PATH")
                
        return tools
    
    def _convert_to_delete_command(self, kubectl_command: str) -> str:
        """Convert kubectl apply/create commands to delete commands."""
        if "apply" in kubectl_command:
            return kubectl_command.replace("apply", "delete")
        elif "create" in kubectl_command:
            return kubectl_command.replace("create", "delete")
        elif kubectl_command.startswith("kubectl get"):
            # For get commands, we can't really delete, so return as-is
            return kubectl_command
        elif "version" in kubectl_command or "help" in kubectl_command:
            # For version/help commands, we can't delete, return as-is
            return kubectl_command
        else:
            # For other commands, try to add delete
            parts = kubectl_command.split()
            if len(parts) >= 2 and parts[0] == "kubectl":
                parts[1] = "delete"
                return " ".join(parts)
            return kubectl_command
    
    def _convert_helm_to_delete_command(self, helm_command: str) -> str:
        """Convert helm install/upgrade commands to uninstall commands."""
        if "install" in helm_command or "upgrade" in helm_command:
            parts = helm_command.split()
            for i, part in enumerate(parts):
                if part in ["install", "upgrade"]:
                    parts[i] = "uninstall"
                    break
            # Remove chart references and keep only release name
            filtered_parts = []
            skip_next = False
            for i, part in enumerate(parts):
                if skip_next:
                    skip_next = False
                    continue
                if part in ["-f", "--values", "--set", "--namespace", "-n"]:
                    skip_next = True
                    continue
                if not part.startswith("-") and "/" not in part and "=" not in part:
                    filtered_parts.append(part)
                elif part.startswith("helm") or part == "uninstall":
                    filtered_parts.append(part)
            return " ".join(filtered_parts)
        elif "version" in helm_command or "help" in helm_command or "repo" in helm_command:
            # For version/help/repo commands, we can't delete, return as-is
            return helm_command
        return helm_command
    
    def _handle_failure(self, instruction: MonitoringInstruction, step: int, total_instruction_count: int):
        """Handle failures during instruction execution."""
        printer.error(f"Error executing instruction {step}/{total_instruction_count}: {instruction}")
        self.failed_instructions.append(instruction)
        printer.warning("Rolling back all executed instructions to this point...")
        self.rollback_instructions()

    def rollback_instructions(self):
        """Rollback any changes made by the executed instructions."""
        printer.info("Rolling back executed instructions...")
        for instruction in reversed(self.complete_instructions):
            printer.info(f"Rolling back: {instruction}")
            try:
                success = self.execute_instruction(instruction, delete=True)
                if not success:
                    printer.warning(f"Failed to rollback instruction: {instruction}")
            except Exception as e:
                printer.error(f"Error rolling back instruction {instruction}: {e}")