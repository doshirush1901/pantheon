---
name: generate_quote
description: Generate a formal PDF quote document for a customer based on machine selection and configuration.
---

# Generate Quote

Use this skill when a customer requests a formal quotation.

## How to use

    exec python src/sales/quote_generator.py --machine "<machine model>" --customer "<customer name>" --quantity <number>

Optional flags:
- Add `--no-pdf` to get text output instead of PDF generation.
