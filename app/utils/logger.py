from rich.console import Console

console = Console()

def log_info(message: str):
    console.print(f"[bold cyan][INFO][/bold cyan] {message}")

def log_success(message: str):
    console.print(f"[bold green][OK][/bold green] {message}")

def log_warn(message: str):
    console.print(f"[bold yellow][WARN][/bold yellow] {message}")

def log_error(message: str):
    console.print(f"[bold red][ERROR][/bold red] {message}")