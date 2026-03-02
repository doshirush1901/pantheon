#!/usr/bin/env python3
"""
Reorganize data/imports/ into themed subfolders with clean filenames.
Uses imports_metadata.json for doc_type, keywords, and machine references.

Folder structure:
  01_Quotes_and_Proposals/
  02_Orders_and_POs/
  03_Product_Catalogues/
  04_Machine_Manuals_and_Specs/
  05_Presentations/
  06_Market_Research_and_Analysis/
  07_Leads_and_Contacts/
  08_Sales_and_CRM/
  09_Industry_Knowledge/
  10_Company_Internal/
  11_Project_Case_Studies/
  12_Emails_and_Correspondence/
  13_Contracts_and_Legal/
  14_Miscellaneous/
"""

import json
import os
import re
import shutil
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent.parent
IMPORTS = BASE / "data" / "imports"
META_PATH = BASE / "data" / "brain" / "imports_metadata.json"
DRY_RUN = False

FOLDER_MAP = {
    "01_Quotes_and_Proposals": [],
    "02_Orders_and_POs": [],
    "03_Product_Catalogues": [],
    "04_Machine_Manuals_and_Specs": [],
    "05_Presentations": [],
    "06_Market_Research_and_Analysis": [],
    "07_Leads_and_Contacts": [],
    "08_Sales_and_CRM": [],
    "09_Industry_Knowledge": [],
    "10_Company_Internal": [],
    "11_Project_Case_Studies": [],
    "12_Emails_and_Correspondence": [],
    "13_Contracts_and_Legal": [],
    "14_Miscellaneous": [],
}


def sanitize_filename(name: str) -> str:
    name = name.replace("\u3000", " ")  # fullwidth space
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', ' ', name).strip()
    name = name.strip('. ')
    if len(name) > 120:
        stem, ext = os.path.splitext(name)
        name = stem[:115] + ext
    return name


def clean_rename(original: str, meta: dict) -> str:
    """Produce a cleaner filename from the original + metadata."""
    stem, ext = os.path.splitext(original)
    ext = ext.lower()
    if ext == '.docx':
        ext = '.docx'

    machines = meta.get("machines", [])
    keywords = meta.get("keywords", [])
    doc_type = meta.get("doc_type", "other")

    cleaned = stem
    cleaned = re.sub(r'_[a-f0-9]{8,12}$', '', cleaned)
    cleaned = re.sub(r'\s*\(\d+\)\s*$', '', cleaned)
    cleaned = re.sub(r'\s*copy\s*\d*\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*\.docx\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'Gmail\s*-\s*', '', cleaned)
    cleaned = cleaned.strip(' .-_')

    if not cleaned:
        cleaned = stem

    cleaned = sanitize_filename(cleaned)
    return cleaned + ext


def classify_file(name: str, meta: dict) -> str:
    """Determine which folder a file belongs in."""
    doc_type = meta.get("doc_type", "other")
    keywords = [k.lower() for k in meta.get("keywords", [])]
    machines = meta.get("machines", [])
    name_lower = name.lower()

    if name.startswith("Quotes/") or name.startswith("Quotes 2/"):
        return "01_Quotes_and_Proposals"

    if doc_type == "quote":
        return "01_Quotes_and_Proposals"

    if name.startswith("Orders Data/"):
        return "02_Orders_and_POs"

    if doc_type == "order":
        return "02_Orders_and_POs"
    if any(w in name_lower for w in ["purchase order", " po ", "po-", "po_", "order_mt", "work order", "order book"]):
        return "02_Orders_and_POs"

    if doc_type == "catalogue":
        return "03_Product_Catalogues"
    if any(w in name_lower for w in ["catalogue", "catalog", "brochure", "model list"]):
        return "03_Product_Catalogues"

    if doc_type == "manual":
        return "04_Machine_Manuals_and_Specs"
    if doc_type == "technical_spec":
        return "04_Machine_Manuals_and_Specs"
    if any(w in name_lower for w in ["manual", "spec sheet", "work_order_template", "configurator",
                                      "machine details", "machine selection", "machine line-up",
                                      "machine comparison", "machine options", "gannt chart",
                                      "cycle time", "process anime", "operating manual",
                                      "infrared heating", "double pitch heater", "price list",
                                      "payment schedule", "master machine list"]):
        return "04_Machine_Manuals_and_Specs"

    if doc_type == "presentation":
        return "05_Presentations"
    if any(w in name_lower for w in [".pptx", "presentation", " ppt"]):
        return "05_Presentations"

    if any(w in name_lower for w in ["market analysis", "market opportunity", "market data",
                                      "thermoforming industry", "competitor", "prospects",
                                      "technology of thermoforming", "tehcnology of thermoforming",
                                      "thermoforming vs alternative", "heavy gauge",
                                      "vehicle construction", "ag-equip", "value of itf",
                                      "top 50 european", "machine comparison"]):
        return "06_Market_Research_and_Analysis"

    if doc_type == "lead_list":
        return "07_Leads_and_Contacts"
    if any(w in name_lower for w in ["leads", "contacts", "visitor list", "invite list",
                                      "customers", "clients", "inquiry form", "diamond mine",
                                      "exhibition", "plastindia", "k2016", "k2022", "k2025"]):
        return "07_Leads_and_Contacts"

    if any(w in name_lower for w in ["sales memo", "cold email", "linkedin post", "outreach",
                                      "mailchimp", "roi", "deadlines", "orders.xlsx",
                                      "order analysis", "mct orders", "european_machine_sales",
                                      "sales diamond"]):
        return "08_Sales_and_CRM"

    if any(w in name_lower for w in ["soft-feel interiors", "ev era", "img thermoforming",
                                      "frimo thermoforming", "applications using",
                                      "applications list", "applications database",
                                      "precision_final", "inline", "roll feeder",
                                      "vacuum forming machine comparison",
                                      "car mats study", "bom_costing", "rigid packaging"]):
        return "09_Industry_Knowledge"

    if doc_type == "email":
        return "12_Emails_and_Correspondence"
    if "gmail" in name_lower:
        return "12_Emails_and_Correspondence"

    if doc_type == "contract":
        return "13_Contracts_and_Legal"
    if any(w in name_lower for w in ["nda", "contract", "warranty"]):
        return "13_Contracts_and_Legal"

    if any(w in name_lower for w in ["brand guidelines", "org structure", "who is rushabh",
                                      "maker's inheritance", "evolution and performance",
                                      "struggle in plastics", "latest news",
                                      "comprehensive_master_database", "mc europe"]):
        return "10_Company_Internal"

    if any(w in name_lower for w in ["case study", "feasibility", "project summary",
                                      "dezet story", "iac", "motherson", "maruti suzuki",
                                      "porta toilet", "bathtub", "bathroom", "agriculture",
                                      "bus ppt", "cv india", "off highway", "formpack",
                                      "tom machine", "tooling examples"]):
        return "11_Project_Case_Studies"

    if machines and doc_type == "other":
        if any(w in name_lower for w in ["quote", "offer", "rfq", "mt20"]):
            return "01_Quotes_and_Proposals"
        return "04_Machine_Manuals_and_Specs"

    return "14_Miscellaneous"


def build_plan(meta_data: dict) -> list:
    """Build a list of (old_relative_path, new_relative_path) tuples."""
    files = meta_data["files"]
    plan = []
    used_names = defaultdict(int)

    for rel_name, meta in sorted(files.items()):
        folder = classify_file(rel_name, meta)

        original_basename = rel_name.split("/")[-1]
        new_name = clean_rename(original_basename, meta)

        key = (folder, new_name.lower())
        used_names[key] += 1
        if used_names[key] > 1:
            stem, ext = os.path.splitext(new_name)
            new_name = f"{stem} ({used_names[key]}){ext}"

        new_rel = f"{folder}/{new_name}"
        plan.append((rel_name, new_rel, meta))

    return plan


def execute_plan(plan: list, meta_data: dict):
    """Move files and update metadata."""
    folders_created = set()
    moved = 0
    skipped = 0
    errors = []

    for old_rel, new_rel, meta in plan:
        old_path = IMPORTS / old_rel
        new_path = IMPORTS / new_rel

        folder = new_path.parent
        if folder not in folders_created:
            if not DRY_RUN:
                folder.mkdir(parents=True, exist_ok=True)
            folders_created.add(folder)

        if not old_path.exists():
            skipped += 1
            continue

        if DRY_RUN:
            print(f"  [DRY] {old_rel}")
            print(f"     -> {new_rel}")
            moved += 1
            continue

        try:
            shutil.move(str(old_path), str(new_path))
            meta["name"] = new_path.name
            meta["path"] = str(new_path)
            moved += 1
        except Exception as e:
            errors.append((old_rel, str(e)))

    new_files = {}
    for old_rel, new_rel, meta in plan:
        new_files[new_rel] = meta

    meta_data["files"] = new_files

    return moved, skipped, errors, len(folders_created)


def cleanup_empty_dirs():
    """Remove now-empty directories like Quotes/, Quotes 2/, Orders Data/."""
    for d in ["Quotes", "Quotes 2", "Orders Data", "docs_from_telegram"]:
        dirpath = IMPORTS / d
        if dirpath.exists():
            try:
                remaining = list(dirpath.iterdir())
                remaining = [f for f in remaining if f.name not in ('.DS_Store', '.gitkeep')]
                if not remaining:
                    shutil.rmtree(str(dirpath))
                    print(f"  Removed empty dir: {d}/")
            except Exception as e:
                print(f"  Could not remove {d}/: {e}")


def main():
    print("=" * 60)
    print("IMPORTS FOLDER REORGANIZATION")
    print("=" * 60)

    with open(META_PATH) as f:
        meta_data = json.load(f)

    total = len(meta_data["files"])
    print(f"\nTotal files in metadata: {total}")

    plan = build_plan(meta_data)

    folder_counts = defaultdict(int)
    for _, new_rel, _ in plan:
        folder = new_rel.split("/")[0]
        folder_counts[folder] += 1

    print("\nPlanned folder distribution:")
    for folder in sorted(folder_counts):
        print(f"  {folder}: {folder_counts[folder]} files")

    if DRY_RUN:
        print("\n--- DRY RUN (first 20) ---")
        for old_rel, new_rel, _ in plan[:20]:
            print(f"  {old_rel}")
            print(f"    -> {new_rel}")
        print(f"\n  ... and {len(plan) - 20} more")
        return

    print("\nExecuting moves...")
    moved, skipped, errors, folders = execute_plan(plan, meta_data)

    print(f"\n  Folders created: {folders}")
    print(f"  Files moved: {moved}")
    print(f"  Files skipped (not found on disk): {skipped}")
    if errors:
        print(f"  Errors: {len(errors)}")
        for path, err in errors[:10]:
            print(f"    {path}: {err}")

    print("\nUpdating metadata...")
    with open(META_PATH, "w") as f:
        json.dump(meta_data, f, indent=2, ensure_ascii=False)
    print("  imports_metadata.json updated.")

    print("\nCleaning up empty directories...")
    cleanup_empty_dirs()

    print("\nDone!")


if __name__ == "__main__":
    main()
