"""
Task management system for email-derived tasks
"""

import os
from datetime import datetime
from typing import List, Dict, Optional


class TaskManager:
    """Manage tasks created from emails"""

    def __init__(self, tasks_file: str = "tasks.md"):
        self.tasks_file = tasks_file

    def create_task(self, task_description: str, sender: str, email_subject: str = "", priority: str = "Medium") -> bool:
        """Create a task from an email."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            priority_marker = self._get_priority_marker(priority)

            task_entry = f"- [ ] {priority_marker} {task_description}\n"
            task_entry += f"  - From: {sender}\n"
            if email_subject:
                task_entry += f"  - Re: {email_subject}\n"
            task_entry += f"  - Created: {timestamp}\n\n"

            with open(self.tasks_file, 'a', encoding='utf-8') as f:
                f.write(task_entry)

            return True

        except Exception:
            return False

    def create_calendar_event(self, event_details: Dict) -> bool:
        """Create a calendar event from email (placeholder for future implementation)."""
        # This would integrate with calendar APIs
        # For now, create a task with calendar notation
        task_desc = f"📅 {event_details.get('title', 'Calendar Event')}"
        if event_details.get('datetime'):
            task_desc += f" on {event_details['datetime']}"

        return self.create_task(
            task_desc,
            event_details.get('organizer', 'Unknown'),
            event_details.get('subject', ''),
            "High"
        )

    def get_tasks(self) -> List[Dict]:
        """Get all tasks from the tasks file."""
        if not os.path.exists(self.tasks_file):
            return []

        tasks = []
        try:
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Simple parsing - could be enhanced with more sophisticated markdown parsing
            lines = content.split('\n')
            current_task = None

            for line in lines:
                if line.startswith('- [ ]') or line.startswith('- [x]'):
                    if current_task:
                        tasks.append(current_task)

                    completed = '[x]' in line
                    task_text = line[5:].strip()  # Remove "- [ ] " or "- [x] "

                    current_task = {
                        'text': task_text,
                        'completed': completed,
                        'metadata': {}
                    }
                elif line.strip().startswith('- ') and current_task:
                    # Metadata line
                    meta_text = line.strip()[2:]  # Remove "- "
                    if ':' in meta_text:
                        key, value = meta_text.split(':', 1)
                        current_task['metadata'][key.strip()] = value.strip()

            if current_task:
                tasks.append(current_task)

        except Exception:
            pass

        return tasks

    def _get_priority_marker(self, priority: str) -> str:
        """Get priority marker for tasks."""
        priority_markers = {
            "High": "🔴",
            "Medium": "🟡",
            "Low": "🟢"
        }
        return priority_markers.get(priority, "🟡")