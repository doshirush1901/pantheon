#!/usr/bin/env python3
"""
QUOTES & EMAIL INGESTION SCRIPT
===============================

Scans the data/imports/01_Quotes_and_Proposals folder and ingests:
1. Gmail PDFs - Email conversations with customers
2. Quote PDFs - Machine quotations and offers

Extracts:
- Machine models mentioned
- Customer/company names
- Applications discussed
- Pricing information
- Technical requirements

Usage:
    python ingest_quotes.py
"""

import logging
import os
import sys
import re
import json

logger = logging.getLogger(__name__)
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))

# Import from centralized config
try:
    from config import get_logger
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    # Fallback: Load environment manually
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"'))

from document_extractor import extract_pdf
from knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

QUOTES_DIR = PROJECT_ROOT / "data" / "imports" / "01_Quotes_and_Proposals"

MACHINE_PATTERNS = [
    r'PF1-[A-Z]?-?\d{4}',
    r'PF1-\d{4}',
    r'PF2-\d+[xX]\d+',
    r'AM-[A-Z]?-?\d{4}',
    r'AMP-\d{4}',
    r'IMG-\d{4}',
    r'FCS-\d{4}',
    r'ATF-\d{4}',
    r'RT-\d[A-Z]-\d{4}',
    r'UNO-\d{4}',
    r'DUO-\d{4}',
]

PRICE_PATTERNS = [
    r'INR\s*[\d,]+(?:\.\d+)?(?:\s*/-)?',
    r'₹\s*[\d,]+(?:\.\d+)?',
    r'USD\s*[\d,]+(?:\.\d+)?',
    r'\$\s*[\d,]+(?:\.\d+)?',
    r'EUR\s*[\d,]+(?:\.\d+)?',
    r'€\s*[\d,]+(?:\.\d+)?',
]

APPLICATION_KEYWORDS = {
    'automotive': ['automotive', 'car', 'vehicle', 'dashboard', 'interior', 'panel', 'bumper'],
    'packaging': ['packaging', 'tray', 'blister', 'clamshell', 'container', 'food'],
    'industrial': ['industrial', 'enclosure', 'cover', 'housing', 'tank', 'bin'],
    'signage': ['signage', 'sign', 'letter', 'display', 'advertising'],
    'aerospace': ['aerospace', 'aircraft', 'aviation'],
    'medical': ['medical', 'healthcare', 'hospital', 'pharmaceutical'],
    'construction': ['construction', 'building', 'architectural'],
}


def extract_machines(text: str) -> List[str]:
    """Extract machine model numbers from text."""
    machines = set()
    for pattern in MACHINE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            machines.add(match.upper())
    return list(machines)


def extract_prices(text: str) -> List[str]:
    """Extract price mentions from text."""
    prices = []
    for pattern in PRICE_PATTERNS:
        matches = re.findall(pattern, text)
        prices.extend(matches)
    return prices[:5]


def extract_applications(text: str) -> List[str]:
    """Detect application areas from text."""
    text_lower = text.lower()
    apps = []
    for app, keywords in APPLICATION_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            apps.append(app)
    return apps


def extract_company_name(text: str, filename: str) -> str:
    """Try to extract customer/company name."""
    patterns = [
        r'To:\s*([^<\n]+)',
        r'Dear\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        r'for\s+([A-Z][A-Za-z\s]+(?:Ltd|Inc|Corp|Pvt|LLC|GmbH|S\.?A\.?))',
        r'([A-Z][A-Za-z\s]+(?:Ltd|Inc|Corp|Pvt|LLC|GmbH|S\.?A\.?))',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text[:2000])
        if match:
            name = match.group(1).strip()
            if len(name) > 3 and len(name) < 50:
                name = re.sub(r'\s+', ' ', name)
                if 'machinecraft' not in name.lower():
                    return name
    
    if 'Paracoat' in filename or 'Paracoat' in text:
        return 'Paracoat Products Ltd'
    if 'Naffco' in filename or 'Naffco' in text:
        return 'Naffco'
    if 'HIUS' in text:
        return 'HIUS'
    
    return ""


def classify_document(filename: str, text: str) -> str:
    """Classify document type."""
    filename_lower = filename.lower()
    
    if 'gmail' in filename_lower:
        if 'inquiry' in filename_lower or 'enquiry' in filename_lower or 'request' in filename_lower:
            return 'customer_inquiry'
        elif 'offer' in filename_lower or 'quote' in filename_lower:
            return 'sales_offer'
        elif 'order' in filename_lower or 'purchase' in filename_lower:
            return 'purchase_order'
        else:
            return 'email_conversation'
    
    elif 'quote' in filename_lower or 'quotation' in filename_lower or 'offer' in filename_lower:
        return 'machine_quote'
    
    elif 'price' in filename_lower:
        return 'price_list'
    
    elif 'portfolio' in filename_lower or 'catalogue' in filename_lower:
        return 'catalogue'
    
    return 'general_document'


def generate_summary(doc_type: str, machines: List[str], customer: str, 
                     applications: List[str], prices: List[str]) -> str:
    """Generate a human-readable summary."""
    parts = []
    
    if doc_type == 'customer_inquiry':
        parts.append("Customer inquiry")
    elif doc_type == 'sales_offer':
        parts.append("Sales offer/quotation")
    elif doc_type == 'machine_quote':
        parts.append("Machine quotation")
    elif doc_type == 'purchase_order':
        parts.append("Purchase order")
    else:
        parts.append(doc_type.replace('_', ' ').title())
    
    if customer:
        parts.append(f"for {customer}")
    
    if machines:
        parts.append(f"regarding {', '.join(machines[:3])}")
    
    if applications:
        parts.append(f"for {', '.join(applications[:2])} applications")
    
    if prices:
        parts.append(f"- {prices[0]}")
    
    return " ".join(parts)


def process_pdf(pdf_path: Path) -> Optional[Dict[str, Any]]:
    """Process a single PDF and extract knowledge."""
    
    logger.info("Processing: %s", pdf_path.name)
    
    text = extract_pdf(pdf_path)
    if not text or len(text) < 50:
        logger.warning("Could not extract text from %s", pdf_path.name)
        return None
    
    doc_type = classify_document(pdf_path.name, text)
    machines = extract_machines(text)
    prices = extract_prices(text)
    applications = extract_applications(text)
    customer = extract_company_name(text, pdf_path.name)
    
    summary = generate_summary(doc_type, machines, customer, applications, prices)
    
    if doc_type in ['customer_inquiry', 'sales_offer', 'email_conversation', 'purchase_order']:
        knowledge_type = 'customer'
    elif doc_type in ['machine_quote', 'price_list']:
        knowledge_type = 'pricing'
    else:
        knowledge_type = 'general'
    
    primary_entity = machines[0] if machines else (customer if customer else pdf_path.stem[:30])
    
    result = {
        "text": text[:8000],
        "entity": primary_entity,
        "knowledge_type": knowledge_type,
        "summary": summary,
        "metadata": {
            "doc_type": doc_type,
            "machines": machines,
            "customer": customer,
            "applications": applications,
            "prices": prices,
            "filename": pdf_path.name,
            "extracted_at": datetime.now().isoformat(),
        }
    }
    
    logger.info("Type: %s, Machines: %s, Customer: %s", doc_type, machines[:3], customer or 'N/A')
    
    return result


def main():
    """Main ingestion flow."""
    import gc
    
    logging.basicConfig(level=logging.INFO)
    logger.info("=" * 60)
    logger.info("QUOTES & EMAIL INGESTION")
    logger.info("=" * 60)
    logger.info("Source: %s", QUOTES_DIR)
    logger.info("=" * 60)
    
    if not QUOTES_DIR.exists():
        logger.error("Directory not found: %s", QUOTES_DIR)
        return
    
    pdf_files = list(QUOTES_DIR.glob("*.pdf"))
    logger.info("Found %d PDF files", len(pdf_files))
    
    stats = {
        "total": len(pdf_files),
        "processed": 0,
        "failed": 0,
        "ingested": 0,
        "skipped": 0,
        "by_type": {},
    }
    
    all_machines = set()
    all_customers = set()
    
    ingestor = KnowledgeIngestor(use_graph=False, verbose=False)
    
    logger.info("-" * 60)
    logger.info("PROCESSING FILES ONE BY ONE")
    logger.info("-" * 60)
    
    for idx, pdf_path in enumerate(pdf_files):
        logger.info("[%d/%d] %s", idx + 1, len(pdf_files), pdf_path.name)
        
        result = process_pdf(pdf_path)
        
        if result:
            stats["processed"] += 1
            doc_type = result["metadata"]["doc_type"]
            stats["by_type"][doc_type] = stats["by_type"].get(doc_type, 0) + 1
            
            all_machines.update(result["metadata"].get("machines", []))
            customer = result["metadata"].get("customer", "")
            if customer:
                all_customers.add(customer)
            
            item = KnowledgeItem(
                text=result["text"],
                entity=result["entity"],
                knowledge_type=result["knowledge_type"],
                source_file=pdf_path.name,
                summary=result["summary"],
                metadata=result["metadata"],
            )
            
            try:
                ingest_result = ingestor.ingest_batch([item])
                stats["ingested"] += ingest_result.items_ingested
                stats["skipped"] += ingest_result.items_skipped
                
                if ingest_result.items_ingested > 0:
                    logger.info("Ingested to Qdrant+Mem0")
                else:
                    logger.info("Skipped (duplicate)")
            except Exception as e:
                logger.error("Ingest error: %s", e)
            
            del item
            del result
            gc.collect()
        else:
            stats["failed"] += 1
    
    logger.info("=" * 60)
    logger.info("INGESTION COMPLETE")
    logger.info("=" * 60)
    logger.info("Total files: %d", stats['total'])
    logger.info("Successfully processed: %d", stats['processed'])
    logger.info("Failed: %d", stats['failed'])
    logger.info("Items ingested: %d", stats['ingested'])
    logger.info("Items skipped (duplicates): %d", stats['skipped'])
    
    logger.info("By document type:")
    for doc_type, count in sorted(stats["by_type"].items(), key=lambda x: -x[1]):
        logger.info("  %s: %d", doc_type, count)
    
    logger.info("-" * 60)
    logger.info("ENTITIES DISCOVERED")
    logger.info("-" * 60)
    logger.info("Machine models: %d", len(all_machines))
    for m in sorted(all_machines)[:15]:
        logger.info("  - %s", m)
    if len(all_machines) > 15:
        logger.info("  ... and %d more", len(all_machines) - 15)
    
    logger.info("Customers/Companies: %d", len(all_customers))
    for c in sorted(all_customers):
        logger.info("  - %s", c)
    
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
