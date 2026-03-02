#!/usr/bin/env python3
"""
IRA AUTO-REPLY LOOP
===================
Runs continuously to ensure Ira ALWAYS replies last.
"""

import os
import sys
import time
import base64
import pdfplumber
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

PROJECT_ROOT = Path(__file__).parent.parent
for line in (PROJECT_ROOT / ".env").read_text().splitlines():
    if line.strip() and not line.startswith('#') and '=' in line:
        key, _, value = line.partition('=')
        os.environ[key.strip()] = value.strip().strip('"')

sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/src/brain"))

import openai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from qdrant_client import QdrantClient
import voyageai

# Config
CHECK_INTERVAL = 30  # seconds
RUSHABH_EMAILS = ['rushabh@machinecraft.org', 'rushabh@machinecraft.in']
IRA_EMAIL = 'ira@machinecraft.org'

def get_gmail_service():
    creds = Credentials.from_authorized_user_file(str(PROJECT_ROOT / 'token.json'))
    return build('gmail', 'v1', credentials=creds)

def get_price_list():
    price_pdf = PROJECT_ROOT / 'data' / 'imports' / 'Machinecraft Price List for Plastindia (1).pdf'
    with pdfplumber.open(str(price_pdf)) as pdf:
        return '\n'.join(page.extract_text() or '' for page in pdf.pages)

def search_knowledge(query):
    voyage = voyageai.Client()
    embedding = voyage.embed([query], model='voyage-3', input_type='query').embeddings[0]
    qdrant = QdrantClient(url='http://localhost:6333')
    
    context = []
    for collection in ['ira_chunks_v4_voyage', 'ira_dream_knowledge_v1']:
        try:
            results = qdrant.query_points(collection_name=collection, query=embedding, limit=3, with_payload=True)
            for r in results.points:
                text = r.payload.get('text', r.payload.get('raw_text', ''))[:400]
                if text:
                    context.append(text)
        except:
            pass
    return '\n'.join(context)

def generate_reply(query, price_list, context):
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model='gpt-4o',
        messages=[
            {'role': 'system', 'content': '''You are Ira, Machinecraft's AI sales assistant.
PERSONALITY: Dry British wit, warm with colleagues, uses dashes for asides, short paragraphs.
RULES: Use ONLY prices from price list. Be helpful and accurate. Keep replies under 200 words.'''},
            {'role': 'user', 'content': f'''PRICE LIST:\n{price_list[:2500]}\n\nCONTEXT:\n{context[:1500]}\n\nQUERY:\n{query}\n\nReply as Ira with personality.'''}
        ],
        max_tokens=400,
        temperature=0.7
    )
    return response.choices[0].message.content

def check_and_reply():
    service = get_gmail_service()
    
    # Find threads where Rushabh sent the last message
    results = service.users().threads().list(
        userId='me',
        q=f'from:({" OR ".join(RUSHABH_EMAILS)}) newer_than:2h',
        maxResults=10
    ).execute()
    
    threads = results.get('threads', [])
    
    for thread in threads:
        thread_data = service.users().threads().get(userId='me', id=thread['id']).execute()
        messages = thread_data.get('messages', [])
        
        if not messages:
            continue
        
        # Check who sent the last message
        last_msg = messages[-1]
        last_headers = {h['name']: h['value'] for h in last_msg['payload']['headers']}
        last_from = last_headers.get('From', '')
        
        # Only reply if Rushabh sent the last message
        is_from_rushabh = any(email in last_from.lower() for email in RUSHABH_EMAILS)
        is_from_ira = IRA_EMAIL in last_from.lower()
        
        if not is_from_rushabh or is_from_ira:
            continue
        
        # Get message body
        def get_body(payload):
            if 'body' in payload and payload['body'].get('data'):
                return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
            return ''
        
        body = get_body(last_msg['payload'])
        if not body or len(body) < 10:
            continue
        
        # Clean body (remove signature, quoted text)
        clean_body = body.split('With Best Regards')[0].split('Best Regards')[0].strip()
        clean_body = clean_body.split('On ')[0].strip()  # Remove quoted replies
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] New message from Rushabh:")
        print(f"  Thread: {thread['id']}")
        print(f"  Query: {clean_body[:100]}...")
        
        # Generate reply
        price_list = get_price_list()
        context = search_knowledge(clean_body)
        reply = generate_reply(clean_body, price_list, context)
        
        print(f"  Reply: {reply[:100]}...")
        
        # Send reply
        subject = last_headers.get('Subject', '')
        if not subject.startswith('Re:'):
            subject = f"Re: {subject}"
        
        message = MIMEMultipart()
        message['to'] = last_from
        message['from'] = IRA_EMAIL
        message['subject'] = subject
        message.attach(MIMEText(reply, 'plain'))
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        sent = service.users().messages().send(
            userId='me', 
            body={'raw': raw, 'threadId': thread['id']}
        ).execute()
        
        # Mark as read
        service.users().messages().modify(
            userId='me', 
            id=last_msg['id'], 
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        print(f"  ✅ Replied! Message ID: {sent['id']}")

def main():
    print("=" * 60)
    print("IRA AUTO-REPLY LOOP")
    print("Ira will ALWAYS reply last to Rushabh's emails")
    print("=" * 60)
    print(f"Checking every {CHECK_INTERVAL} seconds...")
    print("Press Ctrl+C to stop\n")
    
    while True:
        try:
            check_and_reply()
        except Exception as e:
            print(f"[ERROR] {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
