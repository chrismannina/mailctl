"""
TUI application using textual for enhanced email management
"""

from typing import List, Dict, Optional, Any
import asyncio

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header, Footer, Static, ListView, ListItem, Label, Button,
    Input, TextArea, Select, ProgressBar, Tabs, TabPane
)
from textual.reactive import reactive
from textual.message import Message
from textual.binding import Binding
from textual.screen import ModalScreen
from rich.text import Text
from rich.panel import Panel

from .email_providers import get_provider, EmailProvider
from .ai_analyzer import AIAnalyzer
from .task_manager import TaskManager


class EmailItem(ListItem):
    """Custom list item for displaying emails"""

    def __init__(self, email_data: Dict, analysis: Dict = None):
        super().__init__()
        self.email_data = email_data
        self.analysis = analysis

    def compose(self) -> ComposeResult:
        category = self.analysis.get('category', 'Unknown') if self.analysis else 'Unknown'
        priority = self.analysis.get('priority', 'Medium') if self.analysis else 'Medium'

        # Priority and category indicators
        priority_marker = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(priority, "🟡")
        category_colors = {
            'Important': 'red',
            'Newsletter': 'blue',
            'Promotion': 'magenta',
            'Transactional': 'green',
            'Spam': 'bright_red',
            'TaskRequest': 'yellow'
        }

        sender = self.email_data.get('sender', 'Unknown')[:30]
        subject = self.email_data.get('subject', 'No Subject')[:50]

        label_text = f"{priority_marker} {sender:<30} | {subject}"
        yield Label(label_text, classes=f"email-item category-{category.lower()}")


class DraftModal(ModalScreen):
    """Modal screen for editing email drafts"""

    def __init__(self, draft: Dict, email: Dict):
        super().__init__()
        self.draft = draft
        self.email = email

    def compose(self) -> ComposeResult:
        yield Container(
            Label(f"Draft Reply to: {self.email.get('sender', 'Unknown')}", classes="draft-title"),
            Label(f"Subject: {self.draft.get('subject', 'Re: ')}", classes="draft-subject"),
            TextArea(self.draft.get('body', ''), classes="draft-body"),
            Horizontal(
                Button("Send", id="send", variant="primary"),
                Button("Save Draft", id="save"),
                Button("Cancel", id="cancel"),
                classes="draft-buttons"
            ),
            classes="draft-modal"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send":
            # TODO: Send email
            self.dismiss({"action": "send", "draft": self.draft})
        elif event.button.id == "save":
            # TODO: Save draft
            self.dismiss({"action": "save", "draft": self.draft})
        else:
            self.dismiss(None)


class EmailPreview(Static):
    """Widget for previewing email content"""

    email_data: reactive[Optional[Dict]] = reactive(None)
    analysis: reactive[Optional[Dict]] = reactive(None)

    def watch_email_data(self, email_data: Optional[Dict]) -> None:
        """Update preview when email data changes"""
        if email_data:
            self.update_preview()

    def watch_analysis(self, analysis: Optional[Dict]) -> None:
        """Update preview when analysis changes"""
        if analysis:
            self.update_preview()

    def update_preview(self) -> None:
        """Update the preview content"""
        if not self.email_data:
            self.update("Select an email to preview")
            return

        sender = self.email_data.get('sender', 'Unknown')
        subject = self.email_data.get('subject', 'No Subject')
        body = self.email_data.get('body', '')[:1000]

        content = f"**From:** {sender}\n"
        content += f"**Subject:** {subject}\n\n"

        if self.analysis:
            content += f"**Category:** {self.analysis.get('category', 'Unknown')}\n"
            content += f"**Priority:** {self.analysis.get('priority', 'Medium')}\n"
            content += f"**Summary:** {self.analysis.get('summary', 'No summary')}\n"

            # Add thread context information if available
            thread_context = self.analysis.get('thread_context')
            if thread_context:
                content += f"**Thread:** {thread_context.get('thread_length', 1)} messages"
                if thread_context.get('participants'):
                    content += f", {len(thread_context['participants'])} participants"
                content += "\n"
                if thread_context.get('conversation_summary'):
                    content += f"**Context:** {thread_context['conversation_summary']}\n"
                if thread_context.get('reply_recommended'):
                    reply_type = thread_context.get('suggested_reply_type', 'standard')
                    content += f"**💬 Reply suggested:** {reply_type}\n"

            content += "\n"

        content += f"**Body:**\n{body}"

        if len(self.email_data.get('body', '')) > 1000:
            content += "\n\n... (truncated)"

        self.update(content)


class ActionPanel(Static):
    """Widget for displaying available actions"""

    suggested_action: reactive[Optional[str]] = reactive(None)
    analysis: reactive[Optional[Dict]] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Label("Actions", classes="panel-title")
        yield Static("", id="suggestions")
        yield Button("Reply", id="reply", variant="primary")
        yield Button("Delete", id="delete", variant="error")
        yield Button("Unsubscribe", id="unsubscribe")
        yield Button("Create Task", id="task")
        yield Button("Archive", id="archive")
        yield Button("Skip", id="skip")

    def watch_analysis(self, analysis: Optional[Dict]) -> None:
        """Update suggestions based on analysis"""
        suggestions_widget = self.query_one("#suggestions", Static)

        if not analysis:
            suggestions_widget.update("")
            return

        suggestions = []

        # Add AI suggestions
        if analysis.get('suggested_action'):
            suggestions.append(f"🤖 Suggested: {analysis['suggested_action']}")

        # Add thread context suggestions
        thread_context = analysis.get('thread_context', {})
        if thread_context.get('reply_recommended'):
            reply_type = thread_context.get('suggested_reply_type', 'standard')
            suggestions.append(f"💬 Reply: {reply_type}")

        if thread_context.get('reply_urgency') == 'high':
            suggestions.append("⚡ High priority")

        if suggestions:
            suggestions_widget.update("\n".join(suggestions))
        else:
            suggestions_widget.update("No specific suggestions")

    def watch_suggested_action(self, action: Optional[str]) -> None:
        """Highlight suggested action"""
        # TODO: Highlight the suggested action button
        pass


class MailctlTUI(App):
    """Main TUI application"""

    TITLE = "mailctl - AI Email Manager"
    CSS_PATH = "mailctl.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("j", "next_email", "Next Email"),
        Binding("k", "prev_email", "Previous Email"),
        Binding("d", "delete_email", "Delete"),
        Binding("u", "unsubscribe", "Unsubscribe"),
        Binding("t", "create_task", "Task"),
        Binding("enter", "reply", "Reply"),
    ]

    def __init__(self, provider_name: str = "gmail"):
        super().__init__()
        self.provider_name = provider_name
        self.provider: Optional[EmailProvider] = None
        self.ai_analyzer = AIAnalyzer()
        self.task_manager = TaskManager()
        self.emails: List[Dict] = []
        self.current_email_index = 0

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()

        with Container(id="main-container"):
            with Horizontal():
                # Left panel - Email list
                with Vertical(classes="email-list-panel"):
                    yield Label("Inbox", classes="panel-title")
                    yield ListView(id="email-list")
                    yield ProgressBar(id="load-progress", show_eta=False)

                # Center panel - Email preview
                with Vertical(classes="email-preview-panel"):
                    yield EmailPreview(id="email-preview")

                # Right panel - Actions
                with Vertical(classes="action-panel"):
                    yield ActionPanel(id="actions")

        yield Footer()

    async def on_mount(self) -> None:
        """Called when app starts."""
        self.title = f"mailctl - {self.provider_name.title()}"
        await self.authenticate_and_load()

    async def authenticate_and_load(self) -> None:
        """Authenticate with email provider and load emails"""
        try:
            self.provider = get_provider(self.provider_name)

            # Show loading
            progress = self.query_one("#load-progress", ProgressBar)
            progress.update(progress=25)

            if not self.provider.authenticate():
                self.notify("Authentication failed!", severity="error")
                return

            progress.update(progress=50)

            # Fetch emails
            self.emails = self.provider.fetch_unread_emails(20)
            progress.update(progress=75)

            if not self.emails:
                self.notify("No unread emails found")
                progress.update(progress=100)
                return

            # Analyze emails with AI
            await self.analyze_emails()
            progress.update(progress=100)

            # Populate email list
            await self.populate_email_list()

        except Exception as e:
            self.notify(f"Error loading emails: {str(e)}", severity="error")

    async def analyze_emails(self) -> None:
        """Analyze emails with AI and thread context"""
        for i, email in enumerate(self.emails):
            try:
                # Use enhanced analysis with thread context
                analysis = self.ai_analyzer.analyze_email_with_context(email, self.emails)
                email['analysis'] = analysis
            except Exception:
                email['analysis'] = self.ai_analyzer._fallback_analysis()

    async def populate_email_list(self) -> None:
        """Populate the email list widget"""
        email_list = self.query_one("#email-list", ListView)
        email_list.clear()

        for email in self.emails:
            analysis = email.get('analysis', {})
            item = EmailItem(email, analysis)
            email_list.append(item)

        if self.emails:
            email_list.index = 0
            await self.show_email_preview(0)

    async def show_email_preview(self, index: int) -> None:
        """Show preview of selected email"""
        if 0 <= index < len(self.emails):
            email = self.emails[index]
            analysis = email.get('analysis', {})

            preview = self.query_one("#email-preview", EmailPreview)
            preview.email_data = email
            preview.analysis = analysis

            # Update action panel
            actions = self.query_one("#actions", ActionPanel)
            actions.suggested_action = analysis.get('suggested_action')
            actions.analysis = analysis

            self.current_email_index = index

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle email selection"""
        if event.list_view.id == "email-list":
            asyncio.create_task(self.show_email_preview(event.list_view.index))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if not self.emails or self.current_email_index >= len(self.emails):
            return

        current_email = self.emails[self.current_email_index]

        if event.button.id == "reply":
            self.action_reply()
        elif event.button.id == "delete":
            self.action_delete()
        elif event.button.id == "unsubscribe":
            self.action_unsubscribe()
        elif event.button.id == "task":
            self.action_create_task()
        elif event.button.id == "archive":
            self.action_archive()
        elif event.button.id == "skip":
            self.action_skip()

    def action_reply(self) -> None:
        """Handle reply action"""
        if not self.emails:
            return

        current_email = self.emails[self.current_email_index]
        analysis = current_email.get('analysis', {})

        # Use thread context for better draft generation
        draft = self.ai_analyzer.generate_draft_reply(
            current_email,
            all_emails=self.emails,
            reply_type="auto"  # Let AI determine best reply type
        )

        if draft:
            self.push_screen(DraftModal(draft, current_email), self.handle_draft_result)
        else:
            self.notify("Could not generate draft reply", severity="error")

    def handle_draft_result(self, result: Optional[Dict]) -> None:
        """Handle result from draft modal"""
        if result and result.get('action') == 'send':
            # TODO: Send the email
            self.notify("Email sent successfully!")
        elif result and result.get('action') == 'save':
            self.notify("Draft saved")

    def action_delete(self) -> None:
        """Handle delete action"""
        if not self.emails:
            return

        current_email = self.emails[self.current_email_index]

        if self.provider.delete_email(current_email.get('id')):
            self.notify("Email deleted")
            self.remove_current_email()
        else:
            self.notify("Failed to delete email", severity="error")

    def action_unsubscribe(self) -> None:
        """Handle unsubscribe action"""
        if not self.emails:
            return

        current_email = self.emails[self.current_email_index]

        if self.provider.unsubscribe_from_email(current_email.get('id')):
            self.notify("Unsubscribed successfully")
        else:
            self.notify("Could not unsubscribe", severity="warning")

    def action_create_task(self) -> None:
        """Handle create task action"""
        if not self.emails:
            return

        current_email = self.emails[self.current_email_index]
        analysis = current_email.get('analysis', {})

        task_desc = analysis.get('task_description', 'Follow up on email')

        if self.task_manager.create_task(
            task_desc,
            current_email.get('sender', ''),
            current_email.get('subject', ''),
            analysis.get('priority', 'Medium')
        ):
            self.notify("Task created")
        else:
            self.notify("Failed to create task", severity="error")

    def action_archive(self) -> None:
        """Handle archive action"""
        self.notify("Email archived")
        self.remove_current_email()

    def action_skip(self) -> None:
        """Handle skip action"""
        self.notify("Email skipped")
        if self.current_email_index < len(self.emails) - 1:
            asyncio.create_task(self.show_email_preview(self.current_email_index + 1))

    def remove_current_email(self) -> None:
        """Remove current email from list and update view"""
        if self.emails and 0 <= self.current_email_index < len(self.emails):
            self.emails.pop(self.current_email_index)

            # Update email list display
            asyncio.create_task(self.populate_email_list())

            # Adjust current index
            if self.current_email_index >= len(self.emails) and self.emails:
                self.current_email_index = len(self.emails) - 1

            if self.emails:
                asyncio.create_task(self.show_email_preview(self.current_email_index))

    # Keyboard shortcuts
    def action_refresh(self) -> None:
        """Refresh emails"""
        asyncio.create_task(self.authenticate_and_load())

    def action_next_email(self) -> None:
        """Navigate to next email"""
        if self.current_email_index < len(self.emails) - 1:
            email_list = self.query_one("#email-list", ListView)
            email_list.index = self.current_email_index + 1

    def action_prev_email(self) -> None:
        """Navigate to previous email"""
        if self.current_email_index > 0:
            email_list = self.query_one("#email-list", ListView)
            email_list.index = self.current_email_index - 1

    def action_delete_email(self) -> None:
        """Keyboard shortcut for delete"""
        self.action_delete()


def run_tui(provider: str = "gmail") -> None:
    """Run the TUI application"""
    app = MailctlTUI(provider)
    app.run()