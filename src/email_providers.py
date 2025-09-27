"""
Email provider implementations for Gmail and Outlook
"""

import json
import os
import base64
import re
import urllib.parse
from typing import Dict, List, Optional, Any
from email.mime.text import MIMEText

import msal
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
OUTLOOK_SCOPES = ['https://graph.microsoft.com/Mail.ReadWrite', 'https://graph.microsoft.com/Mail.Send']


class EmailProvider:
    """Base class for email providers"""

    def authenticate(self) -> bool:
        """Authenticate with the email provider"""
        raise NotImplementedError

    def fetch_unread_emails(self, count: int = 10) -> List[Dict]:
        """Fetch unread emails"""
        raise NotImplementedError

    def get_email_details(self, message_id: str) -> Optional[Dict[str, str]]:
        """Get detailed information about a specific email"""
        raise NotImplementedError

    def delete_email(self, message_id: str) -> bool:
        """Move email to trash"""
        raise NotImplementedError

    def unsubscribe_from_email(self, message_id: str, headers: List[Dict] = None) -> bool:
        """Attempt to unsubscribe from email"""
        raise NotImplementedError

    def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send an email"""
        raise NotImplementedError


class GmailProvider(EmailProvider):
    """Gmail provider implementation"""

    def __init__(self):
        self.service = None

    def authenticate(self) -> bool:
        """Authenticate with Gmail API using OAuth 2.0."""
        creds = None

        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', GMAIL_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    return False

                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', GMAIL_SCOPES)
                creds = flow.run_local_server(port=0)

            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        try:
            self.service = build('gmail', 'v1', credentials=creds)
            return True
        except Exception:
            return False

    def fetch_unread_emails(self, count: int = 10) -> List[Dict]:
        """Fetch unread email IDs from Gmail."""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=count
            ).execute()

            messages = results.get('messages', [])
            email_details = []

            for msg in messages:
                details = self.get_email_details(msg['id'])
                if details:
                    email_details.append(details)

            return email_details

        except HttpError:
            return []

    def get_email_details(self, message_id: str) -> Optional[Dict[str, str]]:
        """Get detailed information about a specific email."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            headers = message['payload'].get('headers', [])

            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')

            body = self._extract_email_body(message['payload'])

            return {
                'id': message_id,
                'sender': sender,
                'subject': subject,
                'body': body,
                'headers': headers,
                'provider': 'gmail'
            }

        except HttpError:
            return None

    def _extract_email_body(self, payload: Dict) -> str:
        """Extract plain text body from email payload."""
        body = ""

        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
                elif part['mimeType'] == 'multipart/alternative':
                    body = self._extract_email_body(part)
                    if body:
                        break
        elif payload['mimeType'] == 'text/plain':
            data = payload['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8')

        return body[:2000]  # Limit body length for AI processing

    def delete_email(self, message_id: str) -> bool:
        """Move email to trash."""
        try:
            self.service.users().messages().trash(userId='me', id=message_id).execute()
            return True
        except HttpError:
            return False

    def unsubscribe_from_email(self, message_id: str, headers: List[Dict] = None) -> bool:
        """Attempt to unsubscribe from email using List-Unsubscribe header."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            headers = message['payload'].get('headers', [])
            unsubscribe_header = next(
                (h['value'] for h in headers if h['name'] == 'List-Unsubscribe'),
                None
            )

            if not unsubscribe_header:
                return False

            mailto_match = re.search(r'<mailto:([^>]+)>', unsubscribe_header)
            if mailto_match:
                unsubscribe_email = mailto_match.group(1)

                unsubscribe_msg = MIMEText('')
                unsubscribe_msg['to'] = unsubscribe_email
                unsubscribe_msg['subject'] = 'Unsubscribe'

                raw_message = base64.urlsafe_b64encode(
                    unsubscribe_msg.as_bytes()
                ).decode()

                self.service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message}
                ).execute()

                return True

            return False

        except HttpError:
            return False

    def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send an email via Gmail."""
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject

            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode()

            self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            return True
        except HttpError:
            return False


class OutlookProvider(EmailProvider):
    """Outlook provider implementation"""

    def __init__(self):
        self.access_token = None

    def authenticate(self) -> bool:
        """Authenticate with Microsoft Graph API using MSAL."""
        client_id = os.getenv('OUTLOOK_CLIENT_ID')
        if not client_id:
            return False

        authority = "https://login.microsoftonline.com/common"

        app = msal.PublicClientApplication(
            client_id=client_id,
            authority=authority
        )

        # Try to get token from cache
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(OUTLOOK_SCOPES, account=accounts[0])
            if result and 'access_token' in result:
                self.access_token = result['access_token']
                return True

        # Interactive authentication
        result = app.acquire_token_interactive(
            scopes=OUTLOOK_SCOPES,
            port=8080
        )

        if 'access_token' in result:
            self.access_token = result['access_token']
            return True

        return False

    def fetch_unread_emails(self, count: int = 10) -> List[Dict]:
        """Fetch unread emails from Outlook using Microsoft Graph API."""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        url = f'https://graph.microsoft.com/v1.0/me/messages?$filter=isRead eq false&$top={count}&$select=id,sender,subject,body,internetMessageHeaders'

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()
            emails = []

            for message in data.get('value', []):
                email_data = {
                    'id': message['id'],
                    'sender': message['sender']['emailAddress']['address'],
                    'subject': message.get('subject', 'No Subject'),
                    'body': message['body']['content'][:2000] if message['body']['content'] else '',
                    'headers': message.get('internetMessageHeaders', []),
                    'provider': 'outlook'
                }
                emails.append(email_data)

            return emails

        except requests.RequestException:
            return []

    def get_email_details(self, message_id: str) -> Optional[Dict[str, str]]:
        """Get detailed information about a specific Outlook email."""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        url = f'https://graph.microsoft.com/v1.0/me/messages/{message_id}?$select=id,sender,subject,body,internetMessageHeaders'

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            message = response.json()

            return {
                'id': message_id,
                'sender': message['sender']['emailAddress']['address'],
                'subject': message.get('subject', 'No Subject'),
                'body': message['body']['content'][:2000] if message['body']['content'] else '',
                'headers': message.get('internetMessageHeaders', []),
                'provider': 'outlook'
            }

        except requests.RequestException:
            return None

    def delete_email(self, message_id: str) -> bool:
        """Move Outlook email to trash."""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        url = f'https://graph.microsoft.com/v1.0/me/messages/{message_id}'

        try:
            response = requests.delete(url, headers=headers)
            response.raise_for_status()
            return True
        except requests.RequestException:
            return False

    def unsubscribe_from_email(self, message_id: str, headers: List[Dict] = None) -> bool:
        """Attempt to unsubscribe from Outlook email using List-Unsubscribe header."""
        if not headers:
            email_details = self.get_email_details(message_id)
            if not email_details:
                return False
            headers = email_details['headers']

        unsubscribe_header = None
        for header in headers:
            if header.get('name', '').lower() == 'list-unsubscribe':
                unsubscribe_header = header.get('value')
                break

        if not unsubscribe_header:
            return False

        mailto_match = re.search(r'<mailto:([^>]+)>', unsubscribe_header)
        if mailto_match:
            unsubscribe_email = mailto_match.group(1)
            return self.send_email(unsubscribe_email, "Unsubscribe", "")

        return False

    def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send an email via Outlook."""
        email_data = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": body
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to
                        }
                    }
                ]
            }
        }

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(
                'https://graph.microsoft.com/v1.0/me/sendMail',
                headers=headers,
                json=email_data
            )
            response.raise_for_status()
            return True
        except requests.RequestException:
            return False


def get_provider(provider_name: str) -> EmailProvider:
    """Factory function to get email provider"""
    if provider_name.lower() == 'gmail':
        return GmailProvider()
    elif provider_name.lower() == 'outlook':
        return OutlookProvider()
    else:
        raise ValueError(f"Unsupported email provider: {provider_name}")