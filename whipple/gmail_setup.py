"""One-time OAuth device flow to mint Gmail refresh token.

Run once during deploy:
    docker compose exec whipple python -m whipple.gmail_setup
"""
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def main():
    print('--- Whipple Gmail OAuth Setup ---')
    print('1. Go to https://console.cloud.google.com/apis/credentials')
    print('2. Create OAuth client ID (type: Desktop app)')
    print('3. Download the JSON; save to /app/data/gmail_client.json')
    print()
    input('Press ENTER once /app/data/gmail_client.json exists...')

    flow = InstalledAppFlow.from_client_secrets_file('/app/data/gmail_client.json', SCOPES)
    creds = flow.run_console()

    print()
    print('=== ADD THESE LINES TO .env ===')
    print(f'GMAIL_CLIENT_ID={flow.client_config["client_id"]}')
    print(f'GMAIL_CLIENT_SECRET={flow.client_config["client_secret"]}')
    print(f'GMAIL_REFRESH_TOKEN={creds.refresh_token}')
    print('=== END ===')


if __name__ == '__main__':
    main()
