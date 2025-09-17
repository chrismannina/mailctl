#!/usr/bin/env python3
"""
mailctl - Minimal CLI for email control

SETUP INSTRUCTIONS:
==================

GMAIL SETUP:
1. Google Cloud Project Setup:
   - Go to https://console.cloud.google.com/
   - Create a new project or select existing one
   - Enable the Gmail API:
     * Go to APIs & Services > Library
     * Search for "Gmail API" and enable it
   
2. OAuth 2.0 Credentials:
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Select "Desktop application"
   - Download the JSON file and rename it to "credentials.json"
   - Place credentials.json in the same directory as this script

OUTLOOK SETUP:
1. Azure App Registration:
   - Go to https://portal.azure.com/
   - Navigate to Azure Active Directory > App registrations
   - Click "New registration"
   - Name: "mailctl"
   - Supported account types: "Personal Microsoft accounts only"
   - Redirect URI: "Public client/native" with "http://localhost:8080"
   - After creation, note the "Application (client) ID"
   
2. API Permissions:
   - Go to API permissions
   - Add "Microsoft Graph" > "Delegated permissions"
   - Add: Mail.ReadWrite, Mail.Send, offline_access
   - Grant admin consent if required

3. Environment Variables:
   - Create a .env file in this directory with:
     ANTHROPIC_API_KEY="your_anthropic_key_here"
     OUTLOOK_CLIENT_ID="your_azure_app_client_id_here"

4. Install Dependencies:
   pip install -r requirements.txt

5. Run the application:
   python mailctl.py
"""

import json
import os
import base64
import re
import urllib.parse
from typing import Dict, List, Optional, Any
from email.mime.text import MIMEText

import anthropic
import msal
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text

load_dotenv()

GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
OUTLOOK_SCOPES = ['https://graph.microsoft.com/Mail.ReadWrite', 'https://graph.microsoft.com/Mail.Send']
console = Console()

def outlook_authenticate() -> Optional[str]:
    """Authenticate with Microsoft Graph API using MSAL."""
    client_id = os.getenv('OUTLOOK_CLIENT_ID')
    if not client_id:
        console.print("[red]Error: OUTLOOK_CLIENT_ID not found in environment![/red]")
        console.print("Please follow the setup instructions at the top of this file.")
        return None
    
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
            return result['access_token']
    
    # Interactive authentication
    result = app.acquire_token_interactive(
        scopes=OUTLOOK_SCOPES,
        port=8080
    )
    
    if 'access_token' in result:
        return result['access_token']
    else:
        console.print(f"[red]Authentication failed: {result.get('error_description', 'Unknown error')}[/red]")
        return None

def gmail_authenticate() -> Any:
    """Authenticate with Gmail API using OAuth 2.0."""
    creds = None
    
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', GMAIL_SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                console.print("[red]Error: credentials.json file not found![/red]")
                console.print("Please follow the setup instructions at the top of this file.")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as error:
        console.print(f"[red]An error occurred during authentication: {error}[/red]")
        return None

def fetch_unread_outlook_emails(access_token: str, count: int = 10) -> List[Dict]:
    """Fetch unread emails from Outlook using Microsoft Graph API."""
    headers = {
        'Authorization': f'Bearer {access_token}',
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
                'headers': message.get('internetMessageHeaders', [])
            }
            emails.append(email_data)
        
        return emails
    
    except requests.RequestException as error:
        console.print(f"[red]Error fetching Outlook emails: {error}[/red]")
        return []

def fetch_unread_emails(service: Any, count: int = 10) -> List[str]:
    """Fetch unread email IDs from Gmail."""
    try:
        results = service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=count
        ).execute()
        
        messages = results.get('messages', [])
        return [msg['id'] for msg in messages]
    
    except HttpError as error:
        console.print(f"[red]An error occurred fetching emails: {error}[/red]")
        return []

def get_outlook_email_details(access_token: str, message_id: str) -> Optional[Dict[str, str]]:
    """Get detailed information about a specific Outlook email."""
    headers = {
        'Authorization': f'Bearer {access_token}',
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
            'headers': message.get('internetMessageHeaders', [])
        }
    
    except requests.RequestException as error:
        console.print(f"[red]Error fetching Outlook email details: {error}[/red]")
        return None

def get_email_details(service: Any, message_id: str) -> Optional[Dict[str, str]]:
    """Get detailed information about a specific email."""
    try:
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        headers = message['payload'].get('headers', [])
        
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        
        body = extract_email_body(message['payload'])
        
        return {
            'id': message_id,
            'sender': sender,
            'subject': subject,
            'body': body,
            'headers': headers
        }
    
    except HttpError as error:
        console.print(f"[red]Error fetching email details: {error}[/red]")
        return None

def extract_email_body(payload: Dict) -> str:
    """Extract plain text body from email payload."""
    body = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
                break
            elif part['mimeType'] == 'multipart/alternative':
                body = extract_email_body(part)
                if body:
                    break
    elif payload['mimeType'] == 'text/plain':
        data = payload['body']['data']
        body = base64.urlsafe_b64decode(data).decode('utf-8')
    
    return body[:2000]  # Limit body length for AI processing

def analyze_email_with_ai(sender: str, subject: str, body: str) -> Optional[Dict]:
    """Analyze email content using Claude AI."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        console.print("[red]Error: ANTHROPIC_API_KEY not found in environment![/red]")
        return None
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""
        Analyze this email and return a JSON object with the following structure:

        {{
          "summary": "A concise one-sentence summary of the email's content.",
          "category": "Choose one: Important, Newsletter, Promotion, Transactional, Spam, TaskRequest",
          "suggested_action": "Choose one: Reply, Delete, Unsubscribe, CreateTask, NoAction",
          "task_description": "If the email contains a task, describe the task here. Otherwise, null."
        }}

        Email Details:
        From: {sender}
        Subject: {subject}
        Body: {body[:1500]}

        Return only the JSON object, no additional text.
        """
        
        message = client.messages.create(
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
    
    except Exception as error:
        console.print(f"[red]Error analyzing email with AI: {error}[/red]")
        return {
            "summary": "Failed to analyze",
            "category": "Unknown",
            "suggested_action": "NoAction",
            "task_description": None
        }

def delete_outlook_email(access_token: str, message_id: str) -> bool:
    """Move Outlook email to trash."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    url = f'https://graph.microsoft.com/v1.0/me/messages/{message_id}'
    
    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        return True
    except requests.RequestException as error:
        console.print(f"[red]Error deleting Outlook email: {error}[/red]")
        return False

def delete_email(service: Any, message_id: str) -> bool:
    """Move email to trash."""
    try:
        service.users().messages().trash(userId='me', id=message_id).execute()
        return True
    except HttpError as error:
        console.print(f"[red]Error deleting email: {error}[/red]")
        return False

def unsubscribe_from_outlook_email(access_token: str, message_id: str, headers: List[Dict]) -> bool:
    """Attempt to unsubscribe from Outlook email using List-Unsubscribe header."""
    unsubscribe_header = None
    for header in headers:
        if header.get('name', '').lower() == 'list-unsubscribe':
            unsubscribe_header = header.get('value')
            break
    
    if not unsubscribe_header:
        console.print("[yellow]No unsubscribe header found in this email[/yellow]")
        return False
    
    mailto_match = re.search(r'<mailto:([^>]+)>', unsubscribe_header)
    if mailto_match:
        unsubscribe_email = mailto_match.group(1)
        
        # Send unsubscribe email via Microsoft Graph
        email_data = {
            "message": {
                "subject": "Unsubscribe",
                "body": {
                    "contentType": "Text",
                    "content": ""
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": unsubscribe_email
                        }
                    }
                ]
            }
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                'https://graph.microsoft.com/v1.0/me/sendMail',
                headers=headers,
                json=email_data
            )
            response.raise_for_status()
            console.print(f"[green]Unsubscribe email sent to: {unsubscribe_email}[/green]")
            return True
        except requests.RequestException as error:
            console.print(f"[red]Error sending unsubscribe email: {error}[/red]")
            return False
    
    http_match = re.search(r'<(https?://[^>]+)>', unsubscribe_header)
    if http_match:
        unsubscribe_url = http_match.group(1)
        console.print(f"[yellow]Unsubscribe link (manual action required): {unsubscribe_url}[/yellow]")
        return True
    
    console.print("[yellow]Could not parse unsubscribe header[/yellow]")
    return False

def unsubscribe_from_email(service: Any, message_id: str) -> bool:
    """Attempt to unsubscribe from email using List-Unsubscribe header."""
    try:
        message = service.users().messages().get(
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
            console.print("[yellow]No unsubscribe header found in this email[/yellow]")
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
            
            service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            console.print(f"[green]Unsubscribe email sent to: {unsubscribe_email}[/green]")
            return True
        
        http_match = re.search(r'<(https?://[^>]+)>', unsubscribe_header)
        if http_match:
            unsubscribe_url = http_match.group(1)
            console.print(f"[yellow]Unsubscribe link (manual action required): {unsubscribe_url}[/yellow]")
            return True
        
        console.print("[yellow]Could not parse unsubscribe header[/yellow]")
        return False
    
    except HttpError as error:
        console.print(f"[red]Error processing unsubscribe: {error}[/red]")
        return False

def create_task(task_description: str, sender: str) -> bool:
    """Append task to tasks.md file."""
    try:
        task_entry = f"- [ ] {task_description} (From: {sender})\n"
        
        with open('tasks.md', 'a', encoding='utf-8') as f:
            f.write(task_entry)
        
        console.print(f"[green]Task added to tasks.md[/green]")
        return True
    
    except Exception as error:
        console.print(f"[red]Error creating task: {error}[/red]")
        return False

def display_email_info(email: Dict, analysis: Dict, index: int, total: int):
    """Display email information and AI analysis using rich formatting."""
    
    category_colors = {
        'Important': 'red',
        'Newsletter': 'blue',
        'Promotion': 'magenta',
        'Transactional': 'green',
        'Spam': 'bright_red',
        'TaskRequest': 'yellow'
    }
    
    color = category_colors.get(analysis['category'], 'white')
    
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Field", style="bold")
    table.add_column("Value")
    
    table.add_row("From:", email['sender'])
    table.add_row("Subject:", email['subject'])
    table.add_row("Summary:", analysis['summary'])
    table.add_row("Category:", Text(analysis['category'], style=color))
    table.add_row("Suggested:", analysis['suggested_action'])
    
    if analysis['task_description']:
        table.add_row("Task:", analysis['task_description'])
    
    panel = Panel(
        table,
        title=f"Email {index}/{total}",
        title_align="left",
        border_style=color
    )
    
    console.print(panel)

def get_action_prompt(suggested_action: str) -> str:
    """Generate action prompt based on AI suggestion."""
    action_map = {
        'Reply': '(R)eply',
        'Delete': '(D)elete',
        'Unsubscribe': '(U)nsubscribe', 
        'CreateTask': '(T)ask',
        'NoAction': '(S)kip'
    }
    
    suggested = action_map.get(suggested_action, '(S)kip')
    
    options = ['(D)elete', '(U)nsubscribe', '(T)ask', '(S)kip', '(Q)uit']
    
    if suggested in options:
        options.remove(suggested)
        options.insert(0, f"[bold]{suggested}[/bold]")
    
    return f"Action: {' | '.join(options)}"

def process_emails(provider: str, service_or_token: Any, emails: List[Dict]):
    """Process emails with AI analysis and user actions."""
    for i, email_data in enumerate(emails, 1):
        if provider == 'outlook':
            email_details = email_data  # Outlook emails already have full details
        else:
            email_details = get_email_details(service_or_token, email_data)
            if not email_details:
                continue
        
        with console.status("[bold green]Analyzing email with AI..."):
            analysis = analyze_email_with_ai(
                email_details['sender'],
                email_details['subject'],
                email_details['body']
            )
        
        if not analysis:
            continue
        
        display_email_info(email_details, analysis, i, len(emails))
        
        action_prompt = get_action_prompt(analysis['suggested_action'])
        action = Prompt.ask(action_prompt).lower()
        
        if action in ['d', 'delete']:
            if provider == 'outlook':
                success = delete_outlook_email(service_or_token, email_details['id'])
            else:
                success = delete_email(service_or_token, email_details['id'])
            
            if success:
                console.print("[green]✓ Email deleted[/green]")
            else:
                console.print("[red]✗ Failed to delete email[/red]")
        
        elif action in ['u', 'unsubscribe']:
            if provider == 'outlook':
                unsubscribe_from_outlook_email(service_or_token, email_details['id'], email_details['headers'])
            else:
                unsubscribe_from_email(service_or_token, email_details['id'])
        
        elif action in ['t', 'task']:
            task_desc = analysis.get('task_description')
            if not task_desc:
                task_desc = Prompt.ask("Enter task description")
            
            if create_task(task_desc, email_details['sender']):
                console.print("[green]✓ Task created[/green]")
        
        elif action in ['r', 'reply']:
            console.print("[yellow]Reply functionality not implemented in this prototype[/yellow]")
        
        elif action in ['q', 'quit']:
            console.print("[blue]Goodbye![/blue]")
            return
        
        elif action in ['s', 'skip']:
            console.print("[yellow]Skipped[/yellow]")
        
        else:
            console.print("[red]Invalid action, skipping email[/red]")
        
        console.print()  # Add spacing between emails

def main():
    """Main application loop."""
    console.print(Panel.fit(
        "[bold blue]mailctl[/bold blue]\n"
        "Minimal CLI for email control powered by AI",
        title="Welcome"
    ))
    
    # Provider selection
    provider_choice = Prompt.ask(
        "Choose email provider",
        choices=["gmail", "outlook"],
        default="gmail"
    )
    
    if provider_choice == "gmail":
        service = gmail_authenticate()
        if not service:
            return
        
        console.print("[green]Successfully authenticated with Gmail![/green]")
        
        email_ids = fetch_unread_emails(service, 10)
        if not email_ids:
            console.print("[yellow]No unread emails found![/yellow]")
            return
        
        console.print(f"[blue]Found {len(email_ids)} unread emails[/blue]\n")
        process_emails("gmail", service, email_ids)
    
    elif provider_choice == "outlook":
        access_token = outlook_authenticate()
        if not access_token:
            return
        
        console.print("[green]Successfully authenticated with Outlook![/green]")
        
        emails = fetch_unread_outlook_emails(access_token, 10)
        if not emails:
            console.print("[yellow]No unread emails found![/yellow]")
            return
        
        console.print(f"[blue]Found {len(emails)} unread emails[/blue]\n")
        process_emails("outlook", access_token, emails)

if __name__ == "__main__":
    main()