#!/usr/bin/env python3
"""
Vertical Audit: Instrumented RAG Retrieval
=========================================
Runs the 5 ground-truth probes through UnifiedRetriever and logs:
- Raw query
- Top 5 retrieved chunks (pre-rerank and post-rerank)
- Scores and sources

Run from IRA root: python scripts/vertical_audit_instrumented.py
(Place in Ira repo or run with PYTHONPATH)
"""

import json
import logging
import os
import sys
from pathlib import Path

# Ira project root (when run from Ira/scripts/)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Quiet non-audit loggers
logging.getLogger("ira").setLevel(logging.WARNING)
logging.getLogger("qdrant").setLevel(logging.WARNING)

PROBES = [
    {
        "id": "V1",
        "question": "What are the specific safety mechanisms and certifications for the FCS Series when used for medical packaging?",
        "oracle_chunks": ["ingest_fcs_operating_manual.py (safety checks)", "machine_database.py (medical packaging)"],
    },
    {
        "id": "V2",
        "question": "Compare the energy consumption and maintenance schedules of the ATF Series vs. the PF1 Series for a 24/7 operation.",
        "oracle_chunks": ["pf1_c_technical_specs.json (PF1 electrical)", "quote_generator.py (PF1-X vs C power)"],
    },
    {
        "id": "V3",
        "question": "Explain the in-mold graining (IMG) process and which specific polymer types it is most effective with.",
        "oracle_chunks": ["hard_rules.txt (IMG)", "ingest_img_1350_spec_sheet.py", "sales_qualifier.py"],
    },
    {
        "id": "V4",
        "question": "A customer wants to form a 1.2mm HIPS sheet for a refrigerator liner. Which machine do you recommend and what is the expected cycle time?",
        "oracle_chunks": ["hard_rules.txt (PF1 refrigerator, AM thickness)", "telegram state (cycle time)"],
    },
    {
        "id": "V5",
        "question": "What are the key differences in the servo-drive systems between the latest PF1-C-2015 model and the older PF1-B-2012 model?",
        "oracle_chunks": ["store_pf1_c_vs_x.py (PF1-C vs PF1-X)", "pf1_c_technical_specs.json"],
    },
]


def run_instrumented():
    results = []
    try:
        from openclaw.agents.ira.src.brain.unified_retriever import UnifiedRetriever, UnifiedResponse
    except ImportError:
        return {"error": "UnifiedRetriever import failed", "results": []}

    retriever = UnifiedRetriever(use_hybrid=True, use_reranker=True)
    for probe in PROBES:
        rec = {
            "probe_id": probe["id"],
            "question": probe["question"],
            "oracle_chunks": probe["oracle_chunks"],
            "raw_query": probe["question"],
            "retrieved": [],
            "retrieval_time_ms": None,
            "document_count": 0,
            "email_count": 0,
        }
        try:
            resp = retriever.retrieve(probe["question"], top_k=5, include_documents=True, include_emails=True)
            rec["retrieved"] = [
                {
                    "text": r.text[:500],
                    "score": float(r.score) if r.score is not None else None,
                    "source": r.source,
                    "filename": r.filename,
                    "doc_type": r.doc_type,
                }
                for r in (resp.results or [])[:5]
            ]
            rt = getattr(resp, "retrieval_time_ms", None)
            rec["retrieval_time_ms"] = float(rt) if rt is not None else None
            rec["document_count"] = getattr(resp, "document_count", 0)
            rec["email_count"] = getattr(resp, "email_count", 0)
        except Exception as e:
            rec["error"] = str(e)
        results.append(rec)
    return {"results": results}


if __name__ == "__main__":
    out = run_instrumented()
    out_dir = ROOT / "audit_output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "vertical_audit_instrumented.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Written to {out_path}")
    if "results" in out:
        for r in out["results"]:
            print(f"  {r['probe_id']}: {len(r.get('retrieved', []))} chunks")
