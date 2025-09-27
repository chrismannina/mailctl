#!/usr/bin/env python3
"""
mailctl v2 - Enhanced email management with TUI support
"""

import sys
import os
import argparse
from rich.console import Console
from rich.prompt import Prompt

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

console = Console()


def run_tui_mode(provider: str):
    """Run the new TUI interface"""
    try:
        from src.tui_app import run_tui
        console.print(f"[green]Starting mailctl TUI with {provider}...[/green]")
        run_tui(provider)
    except ImportError as e:
        console.print(f"[red]TUI dependencies missing. Install with: pip install textual[/red]")
        console.print(f"Error: {e}")
    except Exception as e:
        console.print(f"[red]Error starting TUI: {e}[/red]")


def run_cli_mode(provider: str):
    """Run the original CLI interface"""
    try:
        from src.email_providers import get_provider
        from src.ai_analyzer import AIAnalyzer
        from src.task_manager import TaskManager

        console.print(f"[blue]Starting mailctl CLI with {provider}...[/blue]")

        # Initialize components
        email_provider = get_provider(provider)
        ai_analyzer = AIAnalyzer()
        task_manager = TaskManager()

        # Authenticate
        if not email_provider.authenticate():
            console.print("[red]Authentication failed![/red]")
            return

        console.print("[green]Authentication successful![/green]")

        # Fetch emails
        emails = email_provider.fetch_unread_emails(10)
        if not emails:
            console.print("[yellow]No unread emails found![/yellow]")
            return

        console.print(f"[blue]Found {len(emails)} unread emails[/blue]")

        # Process emails one by one (simplified CLI version)
        for i, email in enumerate(emails, 1):
            console.print(f"\n[bold]Email {i}/{len(emails)}[/bold]")
            console.print(f"From: {email.get('sender', 'Unknown')}")
            console.print(f"Subject: {email.get('subject', 'No Subject')}")

            # Analyze with AI
            with console.status("[bold green]Analyzing with AI..."):
                analysis = ai_analyzer.analyze_email_with_context(email, emails)

            if analysis:
                console.print(f"Category: {analysis.get('category', 'Unknown')}")
                console.print(f"Priority: {analysis.get('priority', 'Medium')}")
                console.print(f"Summary: {analysis.get('summary', 'No summary')}")

                # Show thread context if available
                thread_context = analysis.get('thread_context')
                if thread_context and thread_context.get('thread_length', 1) > 1:
                    console.print(f"Thread: {thread_context['thread_length']} messages")

            # Simple action prompt
            action = Prompt.ask(
                "Action",
                choices=["delete", "reply", "task", "skip", "quit"],
                default="skip"
            )

            if action == "delete":
                if email_provider.delete_email(email.get('id')):
                    console.print("[green]✓ Email deleted[/green]")
                else:
                    console.print("[red]✗ Failed to delete[/red]")

            elif action == "reply":
                draft = ai_analyzer.generate_draft_reply(email, all_emails=emails)
                if draft:
                    console.print("\n[bold]Generated draft:[/bold]")
                    console.print(f"Subject: {draft.get('subject', '')}")
                    console.print(f"Body:\n{draft.get('body', '')}")
                    if Prompt.ask("Send this reply?", choices=["y", "n"], default="n") == "y":
                        # TODO: Send email
                        console.print("[yellow]Email sending not implemented in CLI mode[/yellow]")
                else:
                    console.print("[red]Could not generate draft[/red]")

            elif action == "task":
                task_desc = analysis.get('task_description') if analysis else None
                if not task_desc:
                    task_desc = Prompt.ask("Enter task description")

                if task_manager.create_task(
                    task_desc,
                    email.get('sender', ''),
                    email.get('subject', ''),
                    analysis.get('priority', 'Medium') if analysis else 'Medium'
                ):
                    console.print("[green]✓ Task created[/green]")

            elif action == "quit":
                console.print("[blue]Goodbye![/blue]")
                break

            elif action == "skip":
                console.print("[yellow]Skipped[/yellow]")

    except Exception as e:
        console.print(f"[red]Error in CLI mode: {e}[/red]")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="mailctl - AI-powered email management")
    parser.add_argument(
        "--mode",
        choices=["tui", "cli"],
        default="tui",
        help="Interface mode (default: tui)"
    )
    parser.add_argument(
        "--provider",
        choices=["gmail", "outlook"],
        default="gmail",
        help="Email provider (default: gmail)"
    )

    args = parser.parse_args()

    try:
        console.print("[bold blue]mailctl v2 - Enhanced Email Management[/bold blue]")

        # If no provider specified via args, ask user
        provider = args.provider
        if not provider:
            provider = Prompt.ask(
                "Choose email provider",
                choices=["gmail", "outlook"],
                default="gmail"
            )

        # Run in specified mode
        if args.mode == "tui":
            run_tui_mode(provider)
        else:
            run_cli_mode(provider)

    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()