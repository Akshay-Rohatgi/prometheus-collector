"""
Instruction objects for structured monitoring plans.
"""
from pydantic import BaseModel, Field
from typing import Union, Literal


class KubectlInstruction(BaseModel):
    """Represents a kubectl command instruction."""
    type: Literal["kubectl"] = Field(default="kubectl", description="Instruction type")
    command: str
    
    def __str__(self) -> str:
        return f"KubectlInstruction: {self.command[:50]}..."


class HelmInstruction(BaseModel):
    """Represents a helm command instruction."""
    type: Literal["helm"] = Field(default="helm", description="Instruction type")
    command: str
    
    def __str__(self) -> str:
        return f"HelmInstruction: {self.command[:50]}..."


class CreateFileInstruction(BaseModel):
    """Represents a file creation instruction."""
    type: Literal["create_file"] = Field(default="create_file", description="Instruction type")
    filename: str
    content: str
    
    def __str__(self) -> str:
        return f"CreateFileInstruction: {self.filename}"


class OtherInstruction(BaseModel):
    """Represents any other type of instruction."""
    type: Literal["other"] = Field(default="other", description="Instruction type")
    description: str
    content: str
    
    def __str__(self) -> str:
        return f"OtherInstruction: {self.description[:50]}..."


# Union type for all instruction types
MonitoringInstruction = Union[KubectlInstruction, HelmInstruction, CreateFileInstruction, OtherInstruction]
