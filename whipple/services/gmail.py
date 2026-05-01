"""Gmail send via OAuth refresh token."""
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config import (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN,
                    RECIPIENT_EMAIL)


SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def _build_service():
    creds = Credentials(
        token=None,
        refresh_token=GMAIL_REFRESH_TOKEN,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=GMAIL_CLIENT_ID,
        client_secret=GMAIL_CLIENT_SECRET,
        scopes=SCOPES,
    )
    return build('gmail', 'v1', credentials=creds)


def _html_to_text(html: str) -> str:
    """Minimal HTML to plain text fallback."""
    from bs4 import BeautifulSoup
    return BeautifulSoup(html, 'html5lib').get_text(separator='\n')


def send_bulletin(subject: str, html: str, to: str = None) -> str:
    """Send bulletin email. Returns the Gmail message id."""
    to = to or RECIPIENT_EMAIL
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = to  # sending to self
    msg['To'] = to
    msg.attach(MIMEText(_html_to_text(html), 'plain', 'utf-8'))
    msg.attach(MIMEText(html, 'html', 'utf-8'))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service = _build_service()
    result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return result['id']
