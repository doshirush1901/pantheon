#!/usr/bin/env python3
"""
Send Day 1 European Drip Campaign Emails

Reads from day1_send_now.csv and sends each email via Gmail API.
Logs results and updates campaign state.
"""

import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
BRAIN_DIR = PROJECT_ROOT / "openclaw/agents/ira/src/brain"
sys.path.insert(0, str(BRAIN_DIR))

from knowledge_validator import send_email_gmail


def main():
    csv_path = PROJECT_ROOT / "data/exports/day1_send_now.csv"
    log_path = PROJECT_ROOT / "data/exports/day1_send_log.json"
    
    if not csv_path.exists():
        print(f"❌ CSV not found: {csv_path}")
        return 1
    
    results = []
    success_count = 0
    fail_count = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        emails = list(reader)
    
    print(f"\n📧 SENDING {len(emails)} DAY 1 INTRO EMAILS")
    print("=" * 50)
    
    for i, email in enumerate(emails, 1):
        to_email = email['to_email']
        to_name = email['to_name']
        company = email['company']
        subject = email['subject']
        body = email['body']
        
        print(f"\n[{i}/{len(emails)}] Sending to {to_name} at {company}...")
        print(f"    Email: {to_email}")
        print(f"    Subject: {subject}")
        
        try:
            success = send_email_gmail(
                to_email=to_email,
                subject=subject,
                body=body,
                from_email="rushabh@machinecraft.org"
            )
            
            if success:
                print(f"    ✅ SENT")
                success_count += 1
                status = "sent"
            else:
                print(f"    ⚠️ FAILED (unknown reason)")
                fail_count += 1
                status = "failed"
                
        except Exception as e:
            print(f"    ❌ ERROR: {e}")
            fail_count += 1
            status = "error"
            success = False
        
        results.append({
            "to_email": to_email,
            "to_name": to_name,
            "company": company,
            "subject": subject,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Small delay between emails to avoid rate limiting
        if i < len(emails):
            time.sleep(2)
    
    # Save log
    with open(log_path, 'w') as f:
        json.dump({
            "campaign": "European Day 1 Intro",
            "sent_at": datetime.now().isoformat(),
            "total": len(emails),
            "success": success_count,
            "failed": fail_count,
            "results": results
        }, f, indent=2)
    
    print("\n" + "=" * 50)
    print(f"📊 SUMMARY: {success_count}/{len(emails)} sent successfully")
    if fail_count > 0:
        print(f"    ⚠️ {fail_count} failed")
    print(f"\n📝 Log saved to: {log_path}")
    
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
