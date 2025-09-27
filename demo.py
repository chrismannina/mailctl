#!/usr/bin/env python3
"""
Demo mode for mailctl - Test with sample emails
"""

import sys
import os
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from rich.console import Console
from src.ai_analyzer import AIAnalyzer
from src.thread_analyzer import ThreadAnalyzer
from src.task_manager import TaskManager

console = Console()

# Sample email data for testing
SAMPLE_EMAILS = [
    {
        'id': 'email_1',
        'sender': 'boss@company.com',
        'subject': 'Budget Approval Needed - Q4 Planning',
        'body': '''Hi there,

I need your approval for the Q4 budget allocation. We're looking at $50,000 for the new marketing campaign.

Please review the attached spreadsheet and let me know your thoughts by Friday.

Thanks!
Sarah''',
        'headers': [
            {'name': 'Message-ID', 'value': '<budget-thread-001@company.com>'},
            {'name': 'Date', 'value': 'Mon, 15 Jan 2024 10:30:00 -0800'}
        ],
        'provider': 'demo'
    },
    {
        'id': 'email_2',
        'sender': 'client@important-client.com',
        'subject': 'URGENT: Production Bug Report',
        'body': '''Hello,

We're experiencing a critical bug in production that's affecting our users. The login system appears to be down.

This is blocking our entire operation. Can you please look into this immediately?

Error details:
- Users cannot log in
- Error 500 on /auth/login
- Started approximately 2 hours ago

Please respond ASAP.

Best regards,
John Smith
CTO, Important Client Inc.''',
        'headers': [
            {'name': 'Message-ID', 'value': '<bug-report-001@important-client.com>'},
            {'name': 'Date', 'value': 'Mon, 15 Jan 2024 11:45:00 -0800'}
        ],
        'provider': 'demo'
    },
    {
        'id': 'email_3',
        'sender': 'newsletter@techblog.com',
        'subject': 'Weekly Tech Digest: Latest in AI and Development',
        'body': '''Welcome to this week's tech digest!

🤖 AI News:
- New GPT model released
- AI coding assistants improving
- Machine learning trends

💻 Development:
- JavaScript frameworks update
- Python 3.12 features
- DevOps best practices

🔗 Links and resources included...

Happy coding!
Tech Blog Team''',
        'headers': [
            {'name': 'Message-ID', 'value': '<newsletter-123@techblog.com>'},
            {'name': 'Date', 'value': 'Mon, 15 Jan 2024 09:00:00 -0800'},
            {'name': 'List-Unsubscribe', 'value': '<mailto:unsubscribe@techblog.com>'}
        ],
        'provider': 'demo'
    },
    {
        'id': 'email_4',
        'sender': 'team@company.com',
        'subject': 'Re: Budget Approval Needed - Q4 Planning',
        'body': '''Hi Sarah,

I have some questions about the budget allocation:

1. What's the expected ROI for this marketing campaign?
2. Do we have metrics from previous campaigns?
3. Is this the final amount or could it change?

I'd like to schedule a quick meeting to discuss before I approve.

Best,
Manager''',
        'headers': [
            {'name': 'Message-ID', 'value': '<budget-thread-002@company.com>'},
            {'name': 'In-Reply-To', 'value': '<budget-thread-001@company.com>'},
            {'name': 'Date', 'value': 'Mon, 15 Jan 2024 12:15:00 -0800'}
        ],
        'provider': 'demo'
    },
    {
        'id': 'email_5',
        'sender': 'promotions@shopping.com',
        'subject': '🎉 50% OFF Everything! Limited Time Offer',
        'body': '''MASSIVE SALE ALERT! 🚨

Everything must go! 50% off EVERYTHING in our store!

⏰ Limited time only - Sale ends midnight tonight!
🛍️ Free shipping on orders over $50
💳 Use code: SAVE50

Shop now: https://shopping.com/sale

Don't miss out on these incredible deals!

Shopping Team''',
        'headers': [
            {'name': 'Message-ID', 'value': '<promo-456@shopping.com>'},
            {'name': 'Date', 'value': 'Mon, 15 Jan 2024 08:30:00 -0800'},
            {'name': 'List-Unsubscribe', 'value': '<https://shopping.com/unsubscribe>'}
        ],
        'provider': 'demo'
    }
]


def demo_ai_analysis():
    """Demonstrate AI analysis capabilities"""
    console.print("[bold blue]🤖 AI Analysis Demo[/bold blue]\n")

    ai_analyzer = AIAnalyzer()

    for i, email in enumerate(SAMPLE_EMAILS, 1):
        console.print(f"[bold]Email {i}: {email['subject']}[/bold]")
        console.print(f"From: {email['sender']}")

        # Analyze with thread context
        analysis = ai_analyzer.analyze_email_with_context(email, SAMPLE_EMAILS)

        if analysis:
            console.print(f"Category: {analysis.get('category', 'Unknown')}")
            console.print(f"Priority: {analysis.get('priority', 'Medium')}")
            console.print(f"Summary: {analysis.get('summary', 'No summary')}")
            console.print(f"Suggested Action: {analysis.get('suggested_action', 'NoAction')}")

            # Show thread context if available
            thread_context = analysis.get('thread_context')
            if thread_context:
                console.print(f"Thread Length: {thread_context.get('thread_length', 1)} messages")
                if thread_context.get('reply_recommended'):
                    console.print(f"💬 Reply Recommended: {thread_context.get('suggested_reply_type', 'standard')}")

        console.print()


def demo_draft_generation():
    """Demonstrate draft generation"""
    console.print("[bold green]✍️ Draft Generation Demo[/bold green]\n")

    ai_analyzer = AIAnalyzer()

    # Generate a draft for the urgent bug report
    urgent_email = SAMPLE_EMAILS[1]  # The production bug email
    console.print(f"[bold]Generating reply for: {urgent_email['subject']}[/bold]")

    draft = ai_analyzer.generate_draft_reply(urgent_email, all_emails=SAMPLE_EMAILS)

    if draft:
        console.print(f"\n[bold]Generated Draft:[/bold]")
        console.print(f"Subject: {draft.get('subject', '')}")
        console.print(f"Confidence: {draft.get('confidence', 0)} / 1.0")
        console.print(f"Requires Review: {draft.get('requires_review', True)}")
        console.print(f"\nBody:\n{draft.get('body', '')}")
    else:
        console.print("[red]Could not generate draft (API key may be missing)[/red]")

    console.print()


def demo_thread_analysis():
    """Demonstrate thread analysis"""
    console.print("[bold yellow]🧵 Thread Analysis Demo[/bold yellow]\n")

    thread_analyzer = ThreadAnalyzer()

    # Group emails by thread
    threads = thread_analyzer.group_emails_by_thread(SAMPLE_EMAILS)

    console.print(f"Found {len(threads)} conversation threads:")

    for thread_id, thread_emails in threads.items():
        console.print(f"\n[bold]Thread: {thread_id[:20]}...[/bold]")
        console.print(f"Messages: {len(thread_emails)}")

        if len(thread_emails) > 1:
            # Analyze the thread
            thread_analysis = thread_analyzer.analyze_thread_patterns(thread_emails)
            summary = thread_analyzer.get_conversation_summary(thread_emails)

            console.print(f"Summary: {summary}")
            console.print(f"Participants: {', '.join(thread_analysis.get('participants', []))}")

            # Check if replies are recommended
            for email in thread_emails:
                reply_rec = thread_analyzer.should_draft_reply(email, thread_emails)
                if reply_rec.get('should_reply'):
                    console.print(f"💬 Reply recommended for: {email['subject'][:30]}...")


def demo_task_management():
    """Demonstrate task management"""
    console.print("[bold magenta]📝 Task Management Demo[/bold magenta]\n")

    task_manager = TaskManager("demo_tasks.md")

    # Create tasks from emails
    for email in SAMPLE_EMAILS:
        if 'budget' in email['subject'].lower() or 'urgent' in email['subject'].lower():
            task_desc = f"Follow up on: {email['subject']}"
            success = task_manager.create_task(
                task_desc,
                email['sender'],
                email['subject'],
                'High' if 'urgent' in email['subject'].lower() else 'Medium'
            )
            if success:
                console.print(f"✓ Created task: {task_desc}")

    # Show created tasks
    tasks = task_manager.get_tasks()
    if tasks:
        console.print(f"\n[bold]Created {len(tasks)} tasks:[/bold]")
        for task in tasks:
            status = "✓" if task['completed'] else "○"
            console.print(f"{status} {task['text']}")
    else:
        console.print("No tasks found in demo_tasks.md")


def main():
    """Run all demos"""
    console.print("[bold]🚀 mailctl Demo Mode[/bold]")
    console.print("Testing all features with sample emails\n")

    try:
        demo_ai_analysis()
        demo_thread_analysis()
        demo_draft_generation()
        demo_task_management()

        console.print("[bold green]✅ All demos completed successfully![/bold green]")
        console.print("\nTo run the full application:")
        console.print("  TUI mode: python mailctl_v2.py --mode tui")
        console.print("  CLI mode: python mailctl_v2.py --mode cli")

    except Exception as e:
        console.print(f"[red]Demo error: {e}[/red]")
        console.print("\nNote: Some features require ANTHROPIC_API_KEY in .env file")


if __name__ == "__main__":
    main()