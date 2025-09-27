#!/usr/bin/env python3
"""
mailctl TUI - Modern terminal interface for email management
"""

import sys
import os
from rich.console import Console
from rich.prompt import Prompt

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.tui_app import run_tui

console = Console()


def main():
    """Main entry point for TUI application"""
    try:
        # Provider selection
        provider_choice = Prompt.ask(
            "Choose email provider",
            choices=["gmail", "outlook"],
            default="gmail"
        )

        console.print(f"[green]Starting mailctl TUI with {provider_choice}...[/green]")

        # Run the TUI
        run_tui(provider_choice)

    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()