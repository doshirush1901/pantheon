#!/usr/bin/env python3
"""
QUOTEBUILDER — Detailed Quote Builder with PDF Export
======================================================

Builds professional, detailed quotes matching the format of real quotations
in data/imports/01_Quotes_and_Proposals/, including full tech specs, terms,
and optional extras, then exports to PDF for sending as an attachment.

Usage:
    from openclaw.agents.ira.src.agents.quotebuilder.agent import get_quotebuilder, build_quote_pdf

    pdf_path = build_quote_pdf(
        width_mm=2000,
        height_mm=1500,
        variant="C",
        customer_name="John Smith",
        company_name="Acme Corp",
        country="India",
    )
"""

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ira.quotebuilder")

AGENT_DIR = Path(__file__).resolve().parent
SRC_DIR = AGENT_DIR.parent.parent
PROJECT_ROOT = SRC_DIR.parent.parent.parent.parent.parent
if not (PROJECT_ROOT / "data" / "brain").exists():
    PROJECT_ROOT = Path.cwd()
    while PROJECT_ROOT != PROJECT_ROOT.parent:
        if (PROJECT_ROOT / "data" / "brain").exists():
            break
        PROJECT_ROOT = PROJECT_ROOT.parent

sys.path.insert(0, str(SRC_DIR / "brain"))
sys.path.insert(0, str(SRC_DIR / "crm"))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

try:
    from quote_generator import (
        QuoteGenerator,
        GeneratedQuote,
        QuoteLineItem,
        generate_quote as brain_generate_quote,
    )
    BRAIN_QUOTE_AVAILABLE = True
except ImportError:
    BRAIN_QUOTE_AVAILABLE = False

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False


EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"
QUOTE_PDF_EXPORTS = EXPORTS_DIR / "quotes"


@dataclass
class BuildQuoteResult:
    """Result of building a quote and PDF."""
    quote_id: str
    pdf_path: str
    total_inr: int
    total_usd: int
    model: str


class DetailedQuotePDF(FPDF if FPDF_AVAILABLE else object):
    """
    Renders a full detailed quote (GeneratedQuote) to PDF, matching the
    structure of real quotes in data/imports/01_Quotes_and_Proposals/.
    """

    def __init__(self):
        if not FPDF_AVAILABLE:
            raise ImportError("fpdf2 is required. Install with: pip install fpdf2")
        super().__init__()
        self.add_page()
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "MACHINECRAFT TECHNOLOGIES", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(
            0, 5,
            "Plot 92, Dehri Road, Umbergaon, Dist. Valsad, Gujarat-396170, India",
            align="C", new_x="LMARGIN", new_y="NEXT"
        )
        self.cell(
            0, 5,
            "Tel: +91-22-40140000 | Email: sales@machinecraft.org | Web: www.machinecraft.org",
            align="C", new_x="LMARGIN", new_y="NEXT"
        )
        self.ln(5)
        self.set_draw_color(0, 0, 0)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-25)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128)
        self.cell(
            0, 4,
            "Machinecraft Technologies - 505, Palm Springs, Link Road, Malad (W), Mumbai 400064, India",
            align="C", new_x="LMARGIN", new_y="NEXT"
        )
        self.cell(0, 4, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title: str):
        self.ln(3)
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 8, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def key_value(self, key: str, value: str, key_width: int = 50):
        self.set_font("Helvetica", "B", 10)
        self.cell(key_width, 6, key)
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, (value or "-")[:80], new_x="LMARGIN", new_y="NEXT")

    def _format_inr(self, amount: int) -> str:
        if amount >= 10000000:
            return f"{amount / 10000000:.2f} Cr"
        if amount >= 100000:
            return f"{amount / 100000:.1f} L"
        return f"{amount:,}"

    def _render_quote(self, quote: "GeneratedQuote") -> None:
        w, h = quote.forming_area_mm
        is_servo = quote.machine_variant in ["X", "S"]

        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "QUOTATION", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

        self.section_title("QUOTE DETAILS")
        self.key_value("Quote No:", quote.quote_id)
        self.key_value("Date:", quote.quote_date)
        self.key_value("Model:", quote.recommended_model)
        self.key_value("Validity:", "30 days from date of issue")
        self.key_value("Prepared by:", "Rushabh Doshi, Director - Sales & Marketing")

        if quote.customer_name and quote.customer_name != "Valued Customer":
            self.section_title("PREPARED FOR")
            self.key_value("Client Name:", quote.customer_name)
            self.key_value("Company:", quote.company_name or "")
            self.key_value("Email:", quote.customer_email or "")
            self.key_value("Country:", quote.country or "India")

        self.section_title(f"{quote.recommended_model} - MACHINE OVERVIEW")
        self.set_font("Helvetica", "", 10)
        overview = (
            f"The {quote.recommended_model} is a heavy-gauge, single-station cut-sheet thermoforming "
            f"machine designed for versatility and high performance. All models in the PF1 Series "
            f"feature a robust closed-chamber design that prevents sheet sag by allowing pre-blow "
            f"air pressure control, ensuring superior forming quality on thick materials.\n\n"
            f"With a generous {w} x {h} mm forming area, the {quote.recommended_model} delivers "
            f"precision forming for a variety of thermoplastic sheets (typically 2-12 mm thick), "
            f"making it ideal for automotive, aerospace, industrial, and commercial applications."
        )
        self.multi_cell(self.w - self.l_margin - self.r_margin, 5, overview.encode("ascii", "replace").decode())
        self.ln(3)

        self.section_title("KEY FEATURES")
        self.set_font("Helvetica", "", 10)
        for feature in quote.key_features:
            self.cell(5, 6, chr(149))
            self.multi_cell(self.w - self.l_margin - self.r_margin - 5, 6, feature.encode("ascii", "replace").decode())
        self.ln(2)

        self.section_title("TECHNICAL SPECIFICATIONS")
        max_depth = quote.requirements.get("max_depth", 600)
        self.key_value("Machine Model:", quote.recommended_model)
        self.key_value("Forming Area (Max):", f"{w} x {h} mm (L x W)")
        self.key_value("Max Stroke Z Direction:", f"{max_depth} mm")
        self.key_value("Sheet Thickness Range:", "Typically 2-12 mm (material-dependent)")
        if is_servo:
            self.key_value("Clamp Frame System:", "Universal Motorized Aperture Setting")
            self.key_value("Sheet Loading/Unloading:", "Automatic Sheet Loading System")
            self.key_value("Forming Platen Drive:", "Servo Motor Driven")
            self.key_value("Heater Oven Drive:", "Servo Motor Driven")
            self.key_value("Clamp Frame Drive:", "Servo Motor Driven")
            self.key_value("Plug Assist Drive:", "Servo Motor Driven")
        else:
            self.key_value("Clamp Frame System:", "Fixed Welded Frames (1 frame included)")
            self.key_value("Sheet Loading/Unloading:", "Manual Loading by Operator")
            self.key_value("Forming Platen Drive:", "Pneumatic (4 cylinders + rack & pinion)")
            self.key_value("Heater Oven Drive:", "Pneumatic (high-temp cylinders)")
            self.key_value("Clamp Frame Drive:", "Pneumatic (2 cylinders + rack & pinion)")
            self.key_value("Plug Assist Drive:", "Pneumatic (manual height adjustment)")
        heater_type = quote.requirements.get("heater_type", "IR Ceramic")
        forming_sqm = quote.forming_area_sqm or (w * h / 1_000_000)
        heater_power = int(forming_sqm * 40)
        vacuum_capacity = max(100, int(forming_sqm * 50))
        total_power = heater_power + (45 if is_servo else 20)
        self.key_value("Heating Oven Configuration:", f"Sandwich - Top & Bottom, {heater_type}")
        self.key_value("Heater Power (approx):", f"{heater_power} kW")
        self.key_value("Vacuum System:", f"~{vacuum_capacity} m3/hr capacity")
        self.key_value("Compressed Air Requirement:", "~6 bar (100 psi)")
        self.key_value("Control System & HMI:", "PLC + 7\" color touchscreen HMI")
        self.key_value("Pre-blow / Sag Control:", "Yes (closed chamber with light sensors)")
        self.key_value("Total Connected Load:", f"~{total_power} kW")
        self.ln(2)

        self.section_title("PRICING")
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(220, 220, 220)
        self.cell(120, 8, "Item", border=1, fill=True)
        self.cell(25, 8, "Qty", border=1, fill=True, align="C")
        self.cell(45, 8, "Price (INR)", border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 10)
        for item in quote.line_items:
            self.cell(120, 7, item.description[:50], border=1)
            self.cell(25, 7, str(item.quantity), border=1, align="C")
            self.cell(45, 7, self._format_inr(item.total_price_inr), border=1, align="R",
                      new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "B", 10)
        self.cell(120, 7, "Subtotal", border=1)
        self.cell(25, 7, "", border=1)
        self.cell(45, 7, self._format_inr(quote.subtotal_inr), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
        if quote.gst_inr > 0:
            self.cell(120, 7, "GST (18%)", border=1)
            self.cell(25, 7, "", border=1)
            self.cell(45, 7, self._format_inr(quote.gst_inr), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_fill_color(200, 230, 200)
        self.cell(120, 8, "TOTAL", border=1, fill=True)
        self.cell(25, 8, "", border=1, fill=True)
        self.cell(45, 8, self._format_inr(quote.total_inr), border=1, align="R", fill=True,
                  new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "I", 9)
        self.cell(0, 6, f"Approximately ${quote.total_usd:,} USD. Price Ex-Works Machinecraft plant, Umargam, Gujarat.",
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

        self.section_title("OPTIONAL EXTRAS")
        self.set_font("Helvetica", "", 9)
        extras = [
            ("Additional Clamp Frames", "Custom-sized frames", "On Request"),
            ("Installation & Commissioning", "At customer site", "On Request"),
            ("Operator Training", "At customer site", "On Request"),
        ]
        if not is_servo:
            extras.extend([
                ("Automatic Sheet Loading", "Powered loading system", "On Request"),
                ("Universal Frame System", "Motorized adjustment", "On Request"),
            ])
        extras.extend([
            ("Enhanced Vacuum System", "Higher capacity pump", "On Request"),
            ("IoT / Remote Monitoring", "VPN-based support module", "On Request"),
        ])
        self.set_font("Helvetica", "B", 9)
        self.cell(70, 6, "Item", border=1)
        self.cell(60, 6, "Description", border=1)
        self.cell(40, 6, "Price", border=1, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        for item, desc, price in extras:
            self.cell(70, 6, item[:35], border=1)
            self.cell(60, 6, desc[:30], border=1)
            self.cell(40, 6, price, border=1, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

        self.section_title("TERMS & CONDITIONS")
        self.key_value("Lead Time:", quote.delivery_time)
        self.key_value("Payment Terms:", quote.payment_terms)
        self.key_value("Shipping:", "EXW Machinecraft plant, Umargam, Gujarat, India")
        self.key_value("Warranty:", quote.warranty)
        self.key_value("Validity:", "This quotation is valid for 30 days from date of issue")
        self.set_font("Helvetica", "", 9)
        terms_text = (
            "DELIVERY TERMS: Packing, freight, insurance, and on-site installation costs are not included unless explicitly stated. "
            "INSTALLATION & TRAINING: Machinecraft will provide on-site commissioning and basic training. "
            "FAT: Machinecraft will do a dry run test and run the machine on demo tool with 1x material like ABS or PS."
        )
        self.multi_cell(self.w - self.l_margin - self.r_margin, 4, terms_text)
        self.ln(3)

        self.section_title("CONTACT INFORMATION")
        self.key_value("Rushabh Doshi", "Director - Sales & Marketing")
        self.key_value("Sales Team", "+91-22-40140000")
        self.key_value("Email", "sales@machinecraft.org")
        self.key_value("Direct Email", "rushabh@machinecraft.org")
        self.key_value("Website", "www.machinecraft.org")
        self.ln(5)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "For acceptance of this offer, please sign below and return a copy:", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)
        self.cell(100, 5, "Accepted by (Authorized Signatory): ____________________")
        self.cell(0, 5, "Date: _____________", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 4, "© Machinecraft Technologies. All Rights Reserved.", align="C")


class Quotebuilder:
    """
    Agent that builds detailed quotes (tech spec, terms, optional extras)
    and exports them to PDF for customer attachment.
    """

    def __init__(self):
        self._generator = QuoteGenerator() if BRAIN_QUOTE_AVAILABLE else None
        QUOTE_PDF_EXPORTS.mkdir(parents=True, exist_ok=True)

    def build_quote(
        self,
        forming_size: Tuple[int, int],
        variant: str = "C",
        materials: Optional[List[str]] = None,
        customer_name: str = "",
        company_name: str = "",
        customer_email: str = "",
        country: str = "India",
        options: Optional[Dict[str, Any]] = None,
    ) -> GeneratedQuote:
        """Build a full detailed quote (no PDF)."""
        if not self._generator:
            raise RuntimeError("Brain quote_generator not available.")
        return self._generator.generate_quick_quote(
            forming_size=forming_size,
            variant=variant,
            materials=materials,
            options=options or {},
            customer_name=customer_name,
            company_name=company_name,
            country=country,
        )

    def quote_to_pdf(self, quote: GeneratedQuote, output_path: Optional[Path] = None) -> str:
        """
        Render a GeneratedQuote to PDF. Returns path to the PDF file.
        """
        if not FPDF_AVAILABLE:
            raise ImportError("fpdf2 is required. Install with: pip install fpdf2")
        pdf = DetailedQuotePDF()
        pdf.alias_nb_pages()
        pdf._render_quote(quote)
        path = output_path or (QUOTE_PDF_EXPORTS / f"Quote_{quote.quote_id}_{quote.recommended_model}.pdf")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        pdf.output(str(path))
        return str(path)

    def build_quote_pdf(
        self,
        width_mm: int,
        height_mm: int,
        variant: str = "C",
        materials: Optional[List[str]] = None,
        customer_name: str = "",
        company_name: str = "",
        customer_email: str = "",
        country: str = "India",
        options: Optional[Dict[str, Any]] = None,
    ) -> BuildQuoteResult:
        """
        Build a detailed quote and save as PDF. Returns result with quote_id and pdf_path.
        """
        forming_size = (width_mm, height_mm)
        quote = self.build_quote(
            forming_size=forming_size,
            variant=variant,
            materials=materials,
            customer_name=customer_name,
            company_name=company_name,
            customer_email=customer_email,
            country=country,
            options=options,
        )
        quote.customer_email = customer_email
        pdf_path = self.quote_to_pdf(quote)
        return BuildQuoteResult(
            quote_id=quote.quote_id,
            pdf_path=pdf_path,
            total_inr=quote.total_inr,
            total_usd=quote.total_usd,
            model=quote.recommended_model,
        )


_quotebuilder: Optional[Quotebuilder] = None


def get_quotebuilder() -> Quotebuilder:
    """Return the singleton Quotebuilder agent."""
    global _quotebuilder
    if _quotebuilder is None:
        _quotebuilder = Quotebuilder()
    return _quotebuilder


def build_quote_pdf(
    width_mm: int,
    height_mm: int,
    variant: str = "C",
    customer_name: str = "",
    company_name: str = "",
    customer_email: str = "",
    country: str = "India",
    materials: Optional[List[str]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> BuildQuoteResult:
    """
    Build a detailed quote and export to PDF. Convenience function.

    Returns:
        BuildQuoteResult with quote_id, pdf_path, total_inr, total_usd, model.
    """
    return get_quotebuilder().build_quote_pdf(
        width_mm=width_mm,
        height_mm=height_mm,
        variant=variant,
        materials=materials,
        customer_name=customer_name,
        company_name=company_name,
        customer_email=customer_email,
        country=country,
        options=options,
    )
