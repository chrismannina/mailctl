"""
AI-powered email analysis and draft generation
"""

import json
import os
from typing import Dict, List, Optional

import anthropic
from dotenv import load_dotenv

from .thread_analyzer import ThreadAnalyzer

load_dotenv()


class AIAnalyzer:
    """AI-powered email analyzer using Claude"""

    def __init__(self):
        self.client = None
        self.thread_analyzer = ThreadAnalyzer()
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            self.client = anthropic.Anthropic(api_key=api_key)

    def analyze_email(self, sender: str, subject: str, body: str, thread_context: List[Dict] = None) -> Optional[Dict]:
        """Analyze email content using Claude AI with optional thread context."""
        if not self.client:
            return self._fallback_analysis()

        try:
            thread_info = ""
            if thread_context:
                thread_info = f"\n\nThread Context ({len(thread_context)} previous messages):\n"
                for i, msg in enumerate(thread_context[-3:], 1):  # Last 3 messages for context
                    thread_info += f"{i}. From: {msg.get('sender', 'Unknown')} - {msg.get('subject', 'No subject')}\n"
                    thread_info += f"   {msg.get('body', '')[:200]}...\n"

            prompt = f"""
            Analyze this email and return a JSON object with the following structure:

            {{
              "summary": "A concise one-sentence summary of the email's content and intent.",
              "category": "Choose one: Important, Newsletter, Promotion, Transactional, Spam, TaskRequest",
              "priority": "Choose one: High, Medium, Low",
              "suggested_action": "Choose one: Reply, Delete, Unsubscribe, CreateTask, Schedule, Archive, NoAction",
              "urgency_indicators": ["list", "of", "urgency", "keywords", "found"],
              "requires_response": true/false,
              "estimated_response_time": "Quick (2min), Medium (15min), Long (1hr+), or null",
              "task_description": "If action needed, describe the specific task. Otherwise, null.",
              "thread_position": "First message, Follow-up, or Ongoing conversation"
            }}

            Email Details:
            From: {sender}
            Subject: {subject}
            Body: {body[:1500]}
            {thread_info}

            Consider the thread context when determining priority and suggested actions.
            Return only the JSON object, no additional text.
            """

            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text.strip()

            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end != 0:
                json_text = response_text[json_start:json_end]
                return json.loads(json_text)
            else:
                return json.loads(response_text)

        except Exception:
            return self._fallback_analysis()

    def generate_draft_reply(self,
                           email: Dict,
                           all_emails: List[Dict] = None,
                           reply_tone: str = "professional",
                           reply_type: str = "auto") -> Optional[Dict]:
        """Generate a draft reply for an email with enhanced thread awareness."""
        if not self.client:
            return None

        try:
            # Get thread context and analysis
            thread_context = []
            thread_summary = "No conversation history"
            reply_recommendations = {"should_reply": True, "reply_type": "standard"}

            if all_emails:
                thread_context = self.thread_analyzer.get_thread_context(email, all_emails)
                if thread_context:
                    thread_summary = self.thread_analyzer.get_conversation_summary(thread_context + [email])
                    reply_recommendations = self.thread_analyzer.should_draft_reply(email, thread_context)

            # Auto-determine reply type if set to auto
            if reply_type == "auto":
                reply_type = reply_recommendations.get('reply_type', 'standard')

            thread_info = ""
            if thread_context:
                thread_info = f"\n\nConversation Context: {thread_summary}\n\n"
                thread_info += "Recent Messages in Thread:\n"
                for i, msg in enumerate(thread_context[-3:], 1):  # Last 3 messages
                    thread_info += f"{i}. From: {msg.get('sender', 'Unknown')}\n"
                    thread_info += f"   Subject: {msg.get('subject', 'No subject')}\n"
                    thread_info += f"   {msg.get('body', '')[:300]}...\n\n"

            # Enhanced prompt based on reply type
            type_instructions = {
                'standard': 'Provide a complete, professional response addressing all points',
                'quick_acknowledgment': 'Brief acknowledgment that you received the email and will respond soon',
                'detailed_response': 'Comprehensive response with detailed explanations',
                'scheduling': 'Focus on scheduling/calendar coordination',
                'summary': 'Summarize the thread and provide clear next steps',
                'decline': 'Politely decline the request with brief explanation'
            }

            instruction = type_instructions.get(reply_type, type_instructions['standard'])

            prompt = f"""
            Generate a professional email reply based on the email and conversation context below.

            Reply Guidelines:
            - Tone: {reply_tone}
            - Type: {reply_type} - {instruction}
            - Consider the full conversation history for context and continuity
            - Be appropriate for the relationship level indicated by the thread
            - Address the sender's main points and any questions asked
            - Confidence level should reflect how sure you are this reply is appropriate

            Current Email to Reply To:
            From: {email.get('sender', 'Unknown')}
            Subject: {email.get('subject', 'No Subject')}
            Body: {email.get('body', '')}
            {thread_info}

            Reply Recommendations from Analysis:
            - Should reply: {reply_recommendations.get('should_reply', True)}
            - Urgency: {reply_recommendations.get('reply_urgency', 'normal')}
            - Confidence: {reply_recommendations.get('confidence', 0.5)}

            Return a JSON object with:
            {{
              "subject": "Re: [appropriate subject line]",
              "body": "The complete email body text",
              "confidence": 0.85,
              "requires_review": true/false,
              "suggested_edits": ["list", "of", "suggestions", "for", "user"],
              "reply_type_used": "{reply_type}",
              "thread_aware": true/false
            }}

            Return only the JSON object.
            """

            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text.strip()

            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end != 0:
                json_text = response_text[json_start:json_end]
                result = json.loads(json_text)
                result['original_email_id'] = email.get('id')
                return result

            return None

        except Exception:
            return None

    def generate_bulk_suggestions(self, emails: List[Dict]) -> Dict[str, List[str]]:
        """Generate bulk action suggestions for multiple emails."""
        if not self.client:
            return {"delete": [], "archive": [], "unsubscribe": []}

        try:
            email_summaries = []
            for i, email in enumerate(emails[:20]):  # Limit to 20 for processing
                summary = f"{i+1}. From: {email.get('sender', 'Unknown')} | Subject: {email.get('subject', 'No subject')} | Body: {email.get('body', '')[:100]}..."
                email_summaries.append(summary)

            prompt = f"""
            Analyze these emails and suggest bulk actions. Group emails by suggested action type.

            Emails to analyze:
            {chr(10).join(email_summaries)}

            Return a JSON object with email numbers grouped by action:
            {{
              "delete": [1, 5, 8],
              "archive": [2, 3, 6],
              "unsubscribe": [4, 7],
              "review": [9, 10],
              "priority": [11]
            }}

            Guidelines:
            - delete: obvious spam, unwanted promotions
            - archive: newsletters, notifications that don't need action
            - unsubscribe: newsletters user likely doesn't want
            - review: emails that need individual attention
            - priority: urgent or important emails
            """

            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text.strip()
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start != -1 and json_end != 0:
                json_text = response_text[json_start:json_end]
                return json.loads(json_text)

            return {"delete": [], "archive": [], "unsubscribe": [], "review": [], "priority": []}

        except Exception:
            return {"delete": [], "archive": [], "unsubscribe": [], "review": [], "priority": []}

    def analyze_email_with_context(self, email: Dict, all_emails: List[Dict] = None) -> Optional[Dict]:
        """Analyze email with full thread context and enhanced recommendations."""
        # Get basic analysis
        basic_analysis = self.analyze_email(
            email.get('sender', ''),
            email.get('subject', ''),
            email.get('body', '')
        )

        if not basic_analysis:
            return None

        # Enhance with thread context
        if all_emails:
            thread_context = self.thread_analyzer.get_thread_context(email, all_emails)
            if thread_context:
                thread_summary = self.thread_analyzer.get_conversation_summary(thread_context + [email])
                reply_recommendations = self.thread_analyzer.should_draft_reply(email, thread_context)
                thread_analysis = self.thread_analyzer.analyze_thread_patterns(thread_context + [email])

                # Enhance the basic analysis with thread insights
                basic_analysis.update({
                    'thread_context': {
                        'thread_length': thread_analysis.get('thread_length', 1),
                        'participants': thread_analysis.get('participants', []),
                        'conversation_summary': thread_summary,
                        'reply_recommended': reply_recommendations.get('should_reply', False),
                        'reply_urgency': reply_recommendations.get('reply_urgency', 'normal'),
                        'suggested_reply_type': reply_recommendations.get('reply_type', 'standard')
                    }
                })

                # Adjust priority based on thread context
                if reply_recommendations.get('reply_urgency') == 'high':
                    basic_analysis['priority'] = 'High'
                elif thread_analysis.get('urgency_escalation'):
                    if basic_analysis.get('priority') == 'Low':
                        basic_analysis['priority'] = 'Medium'

        return basic_analysis

    def _fallback_analysis(self) -> Dict:
        """Fallback analysis when AI is not available."""
        return {
            "summary": "AI analysis unavailable",
            "category": "Unknown",
            "priority": "Medium",
            "suggested_action": "NoAction",
            "urgency_indicators": [],
            "requires_response": False,
            "estimated_response_time": None,
            "task_description": None,
            "thread_position": "Unknown"
        }

    def learn_from_action(self, email: Dict, analysis: Dict, user_action: str):
        """Learn from user actions to improve future suggestions (placeholder for future ML)."""
        # This could be implemented to store user preferences and improve suggestions
        # For now, it's a placeholder for future machine learning capabilities
        pass