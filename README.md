# mailctl

A minimal CLI for email control powered by AI. Process Gmail and Outlook emails with smart categorization and automated actions.

## Features

- 🤖 **AI-Powered Analysis**: Uses Claude 3.5 Sonnet to categorize emails and suggest actions
- 📧 **Multi-Provider Support**: Works with both Gmail and Outlook
- 🎯 **Smart Actions**: Delete, unsubscribe, create tasks, or skip emails based on AI recommendations
- 🎨 **Rich Interface**: Beautiful console interface with color-coded categories
- 📝 **Task Management**: Automatically creates tasks from action-required emails

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Set up email authentication**:
   - **Gmail**: Download `credentials.json` from Google Cloud Console (see setup instructions in script)
   - **Outlook**: Configure Azure app registration (see setup instructions in script)

4. **Run the application**:
   ```bash
   python mailctl.py
   ```

## Email Categories

The AI categorizes emails into:
- **Important**: Urgent or high-priority emails
- **Newsletter**: Subscriptions and newsletters
- **Promotion**: Marketing and promotional emails
- **Transactional**: Receipts, confirmations, notifications
- **Spam**: Unwanted or suspicious emails
- **TaskRequest**: Emails requiring action or follow-up

## Actions Available

- **Delete**: Move email to trash
- **Unsubscribe**: Automatically unsubscribe using List-Unsubscribe headers
- **Create Task**: Add task to `tasks.md` file
- **Skip**: Leave email as-is
- **Quit**: Exit the application

## Configuration

### Gmail Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select project and enable Gmail API
3. Create OAuth 2.0 credentials for desktop application
4. Download and save as `credentials.json` in project directory

### Outlook Setup
1. Go to [Azure Portal](https://portal.azure.com/)
2. Create app registration with Mail permissions
3. Add client ID to `.env` file

## Requirements

- Python 3.7+
- Anthropic API key
- Gmail or Outlook account with API access

## Security Note

Never commit `.env`, `credentials.json`, or `token.json` files to version control. These contain sensitive authentication data.