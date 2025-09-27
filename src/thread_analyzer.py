"""
Thread analysis and context management for email conversations
"""

import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class ThreadAnalyzer:
    """Analyze email threads and provide conversation context"""

    def __init__(self):
        self.thread_cache = {}

    def extract_thread_id(self, email: Dict) -> str:
        """Extract a thread identifier from email headers"""
        headers = email.get('headers', [])

        # Look for standard threading headers
        in_reply_to = None
        references = None
        message_id = None

        for header in headers:
            name = header.get('name', '').lower()
            value = header.get('value', '')

            if name == 'message-id':
                message_id = self._normalize_message_id(value)
            elif name == 'in-reply-to':
                in_reply_to = self._normalize_message_id(value)
            elif name == 'references':
                references = value

        # Use In-Reply-To header for threading (best for grouping)
        if in_reply_to:
            return in_reply_to

        # Use first reference from References header
        if references:
            refs = references.split()
            if refs:
                return self._normalize_message_id(refs[0])

        # Use Message-ID as thread root
        if message_id:
            return message_id

        # Fallback: use subject-based threading
        subject = email.get('subject', '')
        normalized_subject = self._normalize_subject(subject)

        return f"subject-{hash(normalized_subject)}"

    def _normalize_message_id(self, message_id: str) -> str:
        """Normalize message ID for threading"""
        # Remove angle brackets and whitespace
        return re.sub(r'[<>\s]', '', message_id)

    def _normalize_subject(self, subject: str) -> str:
        """Normalize subject for threading"""
        # Remove Re:, Fwd:, etc.
        normalized = re.sub(r'^(re|fwd|fw):\s*', '', subject.lower(), flags=re.IGNORECASE)
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def group_emails_by_thread(self, emails: List[Dict]) -> Dict[str, List[Dict]]:
        """Group emails into conversation threads"""
        threads = {}

        for email in emails:
            thread_id = self.extract_thread_id(email)

            if thread_id not in threads:
                threads[thread_id] = []

            threads[thread_id].append(email)

        # Sort emails within each thread by date if available
        for thread_id, thread_emails in threads.items():
            thread_emails.sort(key=self._get_email_timestamp)

        return threads

    def _get_email_timestamp(self, email: Dict) -> datetime:
        """Extract timestamp from email for sorting"""
        headers = email.get('headers', [])

        for header in headers:
            if header.get('name', '').lower() == 'date':
                try:
                    # Parse email date - this is simplified, real implementation
                    # would need proper RFC 2822 date parsing
                    date_str = header.get('value', '')
                    # For now, return current time as fallback
                    return datetime.now()
                except:
                    pass

        return datetime.now()

    def get_thread_context(self, email: Dict, all_emails: List[Dict]) -> List[Dict]:
        """Get conversation context for an email"""
        thread_id = self.extract_thread_id(email)

        # Find all emails in the same thread
        thread_emails = []
        for other_email in all_emails:
            if self.extract_thread_id(other_email) == thread_id:
                thread_emails.append(other_email)

        # Sort by timestamp
        thread_emails.sort(key=self._get_email_timestamp)

        # Return context (excluding the current email)
        context = [e for e in thread_emails if e.get('id') != email.get('id')]

        return context

    def analyze_thread_patterns(self, thread_emails: List[Dict]) -> Dict:
        """Analyze patterns in a thread for better AI context"""
        if not thread_emails:
            return {}

        analysis = {
            'thread_length': len(thread_emails),
            'participants': set(),
            'response_pattern': [],
            'urgency_escalation': False,
            'question_count': 0,
            'action_items': []
        }

        previous_sender = None
        urgency_keywords = ['urgent', 'asap', 'immediate', 'deadline', 'emergency']

        for i, email in enumerate(thread_emails):
            sender = email.get('sender', '')
            body = email.get('body', '').lower()
            subject = email.get('subject', '').lower()

            analysis['participants'].add(sender)

            # Track response pattern (back and forth vs one-sided)
            if previous_sender and previous_sender != sender:
                analysis['response_pattern'].append('response')
            else:
                analysis['response_pattern'].append('continuation')

            # Check for urgency escalation
            if any(keyword in body or keyword in subject for keyword in urgency_keywords):
                if i > 0:  # Not the first email
                    analysis['urgency_escalation'] = True

            # Count questions
            analysis['question_count'] += body.count('?')

            # Look for action items (simplified)
            if any(phrase in body for phrase in ['please', 'can you', 'need to', 'should we']):
                analysis['action_items'].append(f"Email {i+1}: Action requested")

            previous_sender = sender

        analysis['participants'] = list(analysis['participants'])

        return analysis

    def get_conversation_summary(self, thread_emails: List[Dict]) -> str:
        """Generate a summary of the conversation thread"""
        if not thread_emails:
            return "No conversation history"

        if len(thread_emails) == 1:
            return "First message in conversation"

        participants = set(email.get('sender', 'Unknown') for email in thread_emails)
        key_topics = []

        # Extract key topics from subjects
        subjects = [email.get('subject', '') for email in thread_emails]
        if subjects:
            # Use the most recent subject as primary topic
            primary_topic = self._normalize_subject(subjects[-1])
            key_topics.append(primary_topic)

        summary = f"Conversation with {len(participants)} participants ({', '.join(list(participants)[:3])}"
        if len(participants) > 3:
            summary += f" +{len(participants)-3} others"
        summary += f"), {len(thread_emails)} messages"

        if key_topics:
            summary += f". Topic: {key_topics[0][:50]}"

        return summary

    def should_draft_reply(self, email: Dict, thread_context: List[Dict]) -> Dict:
        """Determine if and how to draft a reply based on thread context"""
        thread_analysis = self.analyze_thread_patterns(thread_context + [email])

        recommendations = {
            'should_reply': False,
            'reply_urgency': 'normal',
            'reply_type': 'standard',
            'confidence': 0.5
        }

        # Check if this appears to be addressed to the user
        body = email.get('body', '').lower()
        subject = email.get('subject', '').lower()

        # Simple heuristics for reply recommendation
        if any(indicator in body for indicator in ['?', 'please', 'can you', 'what do you think']):
            recommendations['should_reply'] = True
            recommendations['confidence'] = 0.8

        if thread_analysis.get('urgency_escalation'):
            recommendations['reply_urgency'] = 'high'
            recommendations['confidence'] = min(1.0, recommendations['confidence'] + 0.2)

        # Determine reply type based on thread length
        if thread_analysis.get('thread_length', 0) > 5:
            recommendations['reply_type'] = 'summary'  # Suggest summarizing the thread
        elif any(word in body for word in ['meeting', 'schedule', 'calendar']):
            recommendations['reply_type'] = 'scheduling'
        elif thread_analysis.get('question_count', 0) > 2:
            recommendations['reply_type'] = 'detailed_response'

        return recommendations