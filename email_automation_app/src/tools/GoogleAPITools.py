import os
import re
import json
import base64
from google.oauth2 import service_account
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from collections import defaultdict
from src.utils import strip_old_replies, strip_old_replies_1


class GmailToolsClass:
    def __init__(self, inbox_email):
        self.inbox_email = inbox_email
        self.service = self._get_gmail_service()

    def _get_gmail_service(self):
        try:
            credentials_info = os.getenv("SERVICE_ACCOUNT_CREDENTIALS")
            if not credentials_info:
                raise EnvironmentError("SERVICE_ACCOUNT_CREDENTIALS environment variable is not set.")
            
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(credentials_info),
                scopes=['https://www.googleapis.com/auth/gmail.modify']
            )
            
            # Delegate credentials to specific user's inbox
            delegated_credentials = credentials.with_subject(self.inbox_email)
            
            return build('gmail', 'v1', credentials=delegated_credentials)
        except Exception as error:
            print(f"Error creating Gmail service: {error}")
            raise

    def fetch_recent_emails(self, max_results=100):
        try:
            now = datetime.now()
            four_hours_ago = now - timedelta(hours=4)

            # Format for Gmail query
            after_timestamp = int(four_hours_ago.timestamp())
            before_timestamp = int(now.timestamp())

            # Query to get emails from the last 4 hours
            query = f'after:{after_timestamp} before:{before_timestamp}'
            results = self.service.users().messages().list(userId=self.inbox_email, q=query, maxResults=max_results).execute()
            messages = results.get('messages', [])
            return messages
        
        except Exception as error:
            print(f"An error occurred while fetching emails: {error}")
            return []

    def fetch_email_threads(self, email_list):
        thread_dict = defaultdict(lambda: {'sender': set(), 'subject': '', 'ids': [], 'body': []})
        
        current_thread = email_list[0]['threadId']
        for email in email_list:
            thread_id = email['threadId']
            if thread_id != current_thread:
                thread_dict[thread_id]['ids'].reverse()
                thread_dict[thread_id]['body'].reverse()
                current_thread = thread_id
            thread_dict[thread_id]['sender'].add(email['sender'])
            if not thread_dict[thread_id]['subject']:
                thread_dict[thread_id]['subject'] = email['subject']
            
            thread_dict[thread_id]['ids'].append(email['id'])
            thread_dict[thread_id]['body'].append({
                "id": email['id'],
                "sender": email['sender'],
                "body": email['body']
            })
        
        # rearrange last thread emails
        thread_dict[thread_id]['ids'].reverse()
        thread_dict[thread_id]['body'].reverse()
        
        combined_threads = []
        for thread_id, thread_info in thread_dict.items():
            combined_threads.append({
                'threadId': thread_id,
                'last_reply_id': thread_info['ids'][-1],
                'sender': list(thread_info['sender']),
                'subject': thread_info['subject'],
                'body': thread_info['body']
            })
        
        return combined_threads
    
    def fetch_draft_replies(self):
        """
        Fetches all draft email replies from Gmail.
        """
        try:
            drafts = self.service.users().drafts().list(userId=self.inbox_email).execute()
            draft_list = drafts.get('drafts', [])
            return [
                {
                    'draft_id': draft['id'], 
                    'threadId': draft['message']['threadId'], 
                    'id': draft['message']['id']
                } for draft in draft_list
            ]
        
        except Exception as error:
            print(f"An error occurred while fetching drafts: {error}")
            return []
        
    def fetch_unreplied_threads(self, max_results=50):
        """
        Fetches recent email threads that don't have draft replies.
        """
        try:
            recent_emails = self.fetch_recent_emails(max_results)
            if not recent_emails:
                return []
            
            latest_emails_in_threads = self._deduplicate_emails(recent_emails)
            drafts = self.fetch_draft_replies()
            threads_with_drafts = {draft['threadId'] for draft in drafts}
            
            unreplied_emails = []
            for email in latest_emails_in_threads:
                if email['threadId'] not in threads_with_drafts:
                    email_info = self._get_email_info(email['id'])
                    if self.skip_returned_emails(email_info['sender']):
                        continue
                    unreplied_emails.append({
                        'id': email['id'],
                        'threadId': email['threadId'],
                        'sender': email_info['sender'],
                        'sender_email': email_info['sender_email'],
                        'subject': email_info['subject'],
                        'body': email_info['body']
                    })
            
            return unreplied_emails
            
        except Exception as error:
            print(f"An error occurred while fetching unreplied threads: {error}")
            return []

    def create_draft_reply(self, id, threadId, sender, subject, reply_text):
        try:
            message = self._create_reply_message(sender, subject, reply_text, id)
            
            draft = self.service.users().drafts().create(
                userId=self.inbox_email,
                body={
                    'message': {
                        'raw': self._encode_message(message),
                        'threadId': threadId
                    }
                }
            ).execute()
            return draft
        except Exception as error:
            print(f"An error occurred while creating draft: {error}")
            return None
        
    def send_reply(self, id, threadId, sender, subject, reply_text):
        try:
            message = self._create_reply_message(sender, subject, reply_text, id)
            sent_message = self.service.users().messages().send(
                userId=self.inbox_email, 
                body={
                    'raw': self._encode_message(message),
                    'threadId': threadId
                }
            ).execute()
            return sent_message
        except Exception as error:
            print(f"An error occurred while sending reply: {error}")
            return None

    def _get_email_info(self, msg_id):
        msg = self.service.users().messages().get(userId=self.inbox_email, id=msg_id, format='full').execute()
        headers = msg['payload']['headers']
        sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'Unknown')
        sender_email = re.search(r'<(.*?)>', sender).group(1) if re.search(r'<(.*?)>', sender) else sender
        subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No Subject')
        body = self._get_email_body(msg)
        body = self._clean_body_text(body)
        return {
            'id': msg_id,
            'threadId': msg["threadId"],
            'sender': sender,
            'sender_email': sender_email,
            'subject': subject,
            'body': body
        }

    def _get_email_body(self, msg):
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        elif 'body' in msg['payload']:
            return base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8')
        return ''
    
    def _clean_body_text(self, text):
        cleaned_text = strip_old_replies(text)
        cleaned_text = strip_old_replies_1(cleaned_text)
        return cleaned_text
    
    def skip_returned_emails(self, sender):
        return sender.lower().find("postmaster@") != -1 or sender.lower().find("mailer-daemon@googlemail.com") != -1

    def _create_reply_message(self, sender, subject, reply_text, original_msg_id):
        message = MIMEText(reply_text)
        message['to'] = sender
        message['subject'] = f"Re: {subject}"
        message['In-Reply-To'] = original_msg_id
        message['References'] = original_msg_id
        message['from'] = self.inbox_email
        return message

    def _encode_message(self, message):
        return base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    def _deduplicate_emails(self, emails):
        thread_map = {}
        for email in emails:
            thread_id = email['threadId']
            if thread_id not in thread_map:
                thread_map[thread_id] = email
        return list(thread_map.values())

class GoogleSheetsToolsClass:
    def __init__(self, sheet_id, range_name):
        """
        Initialize Google Sheets tools with service account authentication.
        """
        self.sheet_id = sheet_id
        self.range_name = range_name
        self.service = self._get_sheets_service()

    def _get_sheets_service(self):
        """
        Create Google Sheets service using service account credentials.
        """
        try:
            credentials_info = os.getenv("SERVICE_ACCOUNT_CREDENTIALS")
            if not credentials_info:
                raise EnvironmentError("SERVICE_ACCOUNT_CREDENTIALS environment variable is not set.")
            
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(credentials_info),
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
            
            return build('sheets', 'v4', credentials=credentials)
            
        except Exception as error:
            print(f"Error creating Sheets service: {error}")
            raise

    def fetch_sheet_data(self):
        """
        Fetch data from Google Sheet and convert to dictionary format.
        """
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=self.range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return {}
            
            data_dict = {row[0]: int(row[1]) for row in values if len(row) >= 2}
            return data_dict

        except Exception as error:
            print(f"An error occurred while fetching sheet data: {error}")
            return {}
