import rich

def out(message: str):
    """Prints a message to the console using rich."""
    rich.print(message)

def banner(message: str):
    """Prints a banner message to the console using rich."""
    rich.print(f"[bold blue] === {message} === [/bold blue]")

def info(message: str):
    """Prints a message to the console using rich."""
    rich.print(f"ℹ️  {message}")
    
def error(message: str):
    """Prints an error message to the console using rich."""
    rich.print(f"🚨 {message}")

def success(message: str):
    """Prints a success message to the console using rich."""
    rich.print(f"✅ {message}")

def warning(message: str):
    """Prints a warning message to the console using rich."""
    rich.print(f"⚠️  {message}")
