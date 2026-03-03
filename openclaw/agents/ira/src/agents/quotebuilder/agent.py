#!/usr/bin/env python3
"""
QUOTEBUILDER — Detailed Quote Builder with PDF Export
======================================================

Builds professional, detailed quotes matching the format of real quotations
in data/imports/01_Quotes_and_Proposals/, including full tech specs, process
flow, power requirements, floor plan dimensions, and terms. Exports to PDF
for sending as an attachment.

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
import math
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

MACHINECRAFT_BLUE = (0, 70, 130)
MACHINECRAFT_DARK = (30, 30, 30)
SECTION_BG = (235, 242, 250)
TABLE_HEADER_BG = (0, 70, 130)
TABLE_ALT_ROW = (245, 248, 252)
TOTAL_ROW_BG = (200, 230, 200)


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
    structure of real Machinecraft quotations with process flow, floor plan,
    and comprehensive technical specifications.
    """

    def __init__(self):
        if not FPDF_AVAILABLE:
            raise ImportError("fpdf2 is required. Install with: pip install fpdf2")
        super().__init__()
        self.add_page()
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*MACHINECRAFT_BLUE)
        self.cell(0, 10, "MACHINECRAFT TECHNOLOGIES", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*MACHINECRAFT_DARK)
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
        self.ln(3)
        self.set_draw_color(*MACHINECRAFT_BLUE)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-20)
        self.set_draw_color(*MACHINECRAFT_BLUE)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(100)
        self.cell(
            0, 4,
            "Machinecraft Technologies | 505, Palm Springs, Link Road, Malad (W), Mumbai 400064, India",
            align="C", new_x="LMARGIN", new_y="NEXT"
        )
        self.cell(0, 4, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title: str):
        self.ln(4)
        self.set_fill_color(*SECTION_BG)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*MACHINECRAFT_BLUE)
        self.cell(0, 8, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*MACHINECRAFT_DARK)
        self.ln(3)

    def key_value(self, key: str, value: str, key_width: int = 55):
        self.set_font("Helvetica", "B", 9)
        self.cell(key_width, 6, key)
        self.set_font("Helvetica", "", 9)
        safe_val = (value or "-").encode("ascii", "replace").decode()
        self.cell(0, 6, safe_val[:90], new_x="LMARGIN", new_y="NEXT")

    def _safe(self, text: str) -> str:
        return text.encode("ascii", "replace").decode()

    def _format_inr(self, amount: int) -> str:
        if amount >= 10000000:
            return f"Rs. {amount / 10000000:.2f} Cr"
        if amount >= 100000:
            return f"Rs. {amount / 100000:.1f} Lakhs"
        return f"Rs. {amount:,}"

    def _table_row(self, col1: str, col2: str, col1_w: int = 80, col2_w: int = 100,
                   bold_col1: bool = False, fill: bool = False):
        if fill:
            self.set_fill_color(*TABLE_ALT_ROW)
        self.set_font("Helvetica", "B" if bold_col1 else "", 9)
        self.cell(col1_w, 6, self._safe(col1), border=0, fill=fill)
        self.set_font("Helvetica", "", 9)
        self.cell(col2_w, 6, self._safe(col2), border=0, fill=fill, new_x="LMARGIN", new_y="NEXT")

    def _render_quote(self, quote: "GeneratedQuote") -> None:
        w, h = quote.forming_area_mm
        is_servo = quote.machine_variant in ["X", "S"]
        forming_sqm = quote.forming_area_sqm or (w * h / 1_000_000)
        heater_power = int(forming_sqm * 40)
        vacuum_capacity = max(100, int(forming_sqm * 50))
        total_power = heater_power + (45 if is_servo else 20)
        heater_type = quote.requirements.get("heater_type", "IR Ceramic")
        max_depth = quote.requirements.get("max_depth", 600)

        # ── TITLE ──
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*MACHINECRAFT_BLUE)
        self.cell(0, 12, "QUOTATION", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*MACHINECRAFT_DARK)
        self.ln(2)

        # ── QUOTE DETAILS ──
        self.section_title("QUOTE DETAILS")
        self.key_value("Quote No:", quote.quote_id)
        self.key_value("Date:", quote.quote_date)
        self.key_value("Model:", quote.recommended_model)
        self.key_value("Validity:", "30 days from date of issue")
        self.key_value("Prepared by:", "Rushabh Doshi, Director - Sales & Marketing")

        # ── PREPARED FOR ──
        if quote.customer_name and quote.customer_name != "Valued Customer":
            self.section_title("PREPARED FOR")
            self.key_value("Client Name:", quote.customer_name)
            self.key_value("Company:", quote.company_name or "")
            self.key_value("Email:", quote.customer_email or "")
            self.key_value("Country:", quote.country or "India")

        # ── MACHINE OVERVIEW ──
        self.section_title(f"{quote.recommended_model} - MACHINE OVERVIEW")
        self.set_font("Helvetica", "", 9)
        variant_name = "All-Servo (PF1-X Series)" if is_servo else "Pneumatic (PF1-C Series)"
        overview = (
            f"The {quote.recommended_model} is a heavy-gauge, single-station cut-sheet thermoforming "
            f"machine from the {variant_name} range, designed for versatility and high performance. "
            f"All models in the PF1 Series feature a robust closed-chamber design that prevents "
            f"sheet sag by allowing pre-blow air pressure control, ensuring superior forming quality "
            f"on thick materials.\n\n"
            f"With a generous {w} x {h} mm forming area, the {quote.recommended_model} delivers "
            f"precision forming for a variety of thermoplastic sheets (typically 2-12 mm thick), "
            f"making it ideal for automotive, aerospace, industrial, and commercial applications."
        )
        self.multi_cell(self.w - self.l_margin - self.r_margin, 5, self._safe(overview))
        self.ln(2)

        # ── KEY FEATURES ──
        self.section_title("KEY FEATURES")
        self.set_font("Helvetica", "", 9)
        for feature in quote.key_features:
            self.cell(5, 5, chr(149))
            self.multi_cell(self.w - self.l_margin - self.r_margin - 5, 5, self._safe(feature))
            self.ln(1)
        self.ln(1)

        # ── PROCESS FLOW ──
        self._render_process_flow(quote, w, h, is_servo, max_depth)

        # ── TECHNICAL SPECIFICATIONS ──
        self._render_technical_specs(quote, w, h, is_servo, heater_type, heater_power,
                                     vacuum_capacity, total_power, max_depth, forming_sqm)

        # ── POWER & UTILITIES ──
        self._render_power_requirements(is_servo, heater_power, total_power, vacuum_capacity, w, h)

        # ── FLOOR PLAN ──
        self._render_floor_plan(w, h, is_servo)

        # ── PRICING ──
        self._render_pricing(quote, is_servo)

        # ── OPTIONAL EXTRAS ──
        self._render_optional_extras(is_servo)

        # ── TERMS & CONDITIONS ──
        self._render_terms(quote)

        # ── CONTACT ──
        self._render_contact()

    def _render_process_flow(self, quote, w, h, is_servo, max_depth):
        """Detailed step-by-step thermoforming process flow."""
        self.section_title("THERMOFORMING PROCESS FLOW")
        self.set_font("Helvetica", "", 9)
        intro = (
            f"The {quote.recommended_model} operates as a single-station, cut-sheet thermoforming "
            f"machine. Below is the step-by-step process cycle from sheet loading to finished part removal."
        )
        self.multi_cell(self.w - self.l_margin - self.r_margin, 5, self._safe(intro))
        self.ln(3)

        loading_desc = (
            "Automatic sheet loading system picks up a pre-cut sheet from the "
            "loading table and positions it onto the clamp frame."
        ) if is_servo else (
            "Operator manually places a pre-cut thermoplastic sheet (typically 2-12 mm thick) "
            "onto the clamp frame loading table. Sheet is positioned against alignment guides."
        )

        clamping_desc = (
            "Servo-driven motorized clamp frame with universal aperture setting grips the sheet "
            "on all four sides. Aperture size is set via the HMI touchscreen - no manual adjustment "
            "needed. Clamp force is pneumatically applied and adjustable via regulator."
        ) if is_servo else (
            "Pneumatic clamp frame (fixed welded frame, 1 frame included) grips the sheet on all "
            "four sides. Clamp force is pneumatically applied via 2 cylinders with rack & pinion "
            "mechanism. Additional custom-sized frames available for different sheet sizes."
        )

        heating_desc = (
            f"The clamped sheet moves into the sandwich heating oven (top & bottom heaters). "
            f"{quote.requirements.get('heater_type', 'IR Ceramic')} heating elements with individual "
            f"SSR (Solid State Relay) and digital PID control via HMI provide precise, zone-by-zone "
            f"temperature control. Approximate heater power: {int((w * h / 1_000_000) * 40)} kW. "
            f"Heating time depends on material type and thickness (typically 60-180 seconds for "
            f"3-8 mm sheets). {'Servo-driven oven movement ensures repeatable positioning.' if is_servo else 'Pneumatic high-temperature cylinders drive oven movement.'}"
        )

        preblow_desc = (
            "Once the sheet reaches forming temperature, the closed chamber beneath the sheet line "
            "activates. Pulsated air pressure (pre-blow) is applied from below to maintain the "
            "sheet level and prevent sag. Light sensors continuously monitor sheet position and "
            "automatically adjust air pressure. This zero-sag system is critical for uniform "
            "wall thickness distribution in the final part."
        )

        forming_desc = (
            f"The heated sheet (now pliable) is transferred to the forming station. The forming "
            f"platen rises {'via servo motor drive with programmable speed and acceleration profiles' if is_servo else 'via 4 pneumatic cylinders with rack & pinion mechanism'}, "
            f"bringing the mold into contact with the sheet. Maximum forming stroke: {max_depth} mm. "
            f"Vacuum is applied through the mold (capacity: ~{max(100, int((w * h / 1_000_000) * 50))} m3/hr) "
            f"to draw the sheet tightly against the mold surface. "
            f"{'Servo plug assist with programmable depth and speed helps distribute material evenly for deep-draw parts.' if is_servo else 'Pneumatic plug assist (manual height adjustment) available for deep-draw applications.'}"
        )

        cooling_desc = (
            "Centrifugal cooling fans blow ambient air across the formed part while it remains "
            "on the mold under vacuum. Cooling time varies by material and thickness (typically "
            "30-120 seconds). The part must cool below the material's heat deflection temperature "
            "before release to maintain dimensional stability. Optional spray mist cooling "
            "available for faster cycle times."
        )

        release_desc = (
            "Vacuum is released and a brief burst of compressed air (blow-off) separates the "
            "formed part from the mold surface. "
            f"The forming platen lowers {'via servo drive' if is_servo else 'pneumatically'} "
            f"back to the home position."
        )

        unloading_desc = (
            "The clamp frame releases and the formed part is removed. "
            f"{'Automatic unloading system transfers the part to the output table.' if is_servo else 'Operator manually removes the formed part from the machine.'} "
            "The machine is ready for the next cycle. Typical cycle time: 2-5 minutes "
            "depending on material, thickness, and part geometry."
        )

        steps = [
            ("1. SHEET LOADING", loading_desc),
            ("2. CLAMPING", clamping_desc),
            ("3. HEATING", heating_desc),
            ("4. PRE-BLOW / SAG CONTROL", preblow_desc),
            ("5. VACUUM FORMING", forming_desc),
            ("6. COOLING", cooling_desc),
            ("7. PART RELEASE", release_desc),
            ("8. UNLOADING & CYCLE REPEAT", unloading_desc),
        ]

        for title, desc in steps:
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(*MACHINECRAFT_BLUE)
            self.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*MACHINECRAFT_DARK)
            self.multi_cell(self.w - self.l_margin - self.r_margin, 4, self._safe(desc))
            self.ln(2)

    def _render_technical_specs(self, quote, w, h, is_servo, heater_type, heater_power,
                                vacuum_capacity, total_power, max_depth, forming_sqm):
        """Comprehensive technical specifications table."""
        self.section_title("TECHNICAL SPECIFICATIONS")

        specs = [
            ("Machine Model", quote.recommended_model),
            ("Machine Type", "Single-Station Cut-Sheet Thermoformer"),
            ("Variant", "All-Servo (PF1-X)" if is_servo else "Pneumatic (PF1-C)"),
            ("", ""),
            ("FORMING", ""),
            ("Forming Area (Max)", f"{w} x {h} mm (L x W)"),
            ("Forming Area", f"{forming_sqm:.2f} m2"),
            ("Max Stroke Z Direction", f"{max_depth} mm"),
            ("Sheet Thickness Range", "Typically 2-12 mm (material-dependent)"),
            ("Compatible Materials", "ABS, HDPE, PP, PC, PMMA, PVC, PETG, TPO, and more"),
            ("", ""),
            ("CLAMP FRAME", ""),
        ]

        if is_servo:
            specs.extend([
                ("Clamp Frame System", "Universal Motorized Aperture Setting"),
                ("Aperture Adjustment", "Motorized via HMI touchscreen (both axes)"),
                ("Clamp Force", "Pneumatic, adjustable via regulator"),
                ("Frame Change Time", "< 2 minutes (motorized adjustment)"),
            ])
        else:
            specs.extend([
                ("Clamp Frame System", "Fixed Welded Frames (1 frame included)"),
                ("Clamp Force", "Pneumatic, 2 cylinders + rack & pinion"),
                ("Additional Frames", "Custom sizes available on request"),
            ])

        specs.extend([
            ("", ""),
            ("DRIVE SYSTEM", ""),
        ])

        if is_servo:
            specs.extend([
                ("Forming Platen Drive", "Servo Motor Driven"),
                ("Heater Oven Drive", "Servo Motor Driven"),
                ("Clamp Frame Drive", "Servo Motor Driven"),
                ("Plug Assist Drive", "Servo Motor Driven"),
                ("Sheet Loading", "Automatic Sheet Loading System"),
                ("Speed/Acceleration", "Fully programmable via HMI"),
            ])
        else:
            specs.extend([
                ("Forming Platen Drive", "Pneumatic (4 cylinders + rack & pinion)"),
                ("Heater Oven Drive", "Pneumatic (high-temp cylinders)"),
                ("Clamp Frame Drive", "Pneumatic (2 cylinders + rack & pinion)"),
                ("Plug Assist Drive", "Pneumatic (manual height adjustment)"),
                ("Sheet Loading", "Manual by operator"),
            ])

        specs.extend([
            ("", ""),
            ("HEATING SYSTEM", ""),
            ("Oven Configuration", f"Sandwich - Top & Bottom, {heater_type}"),
            ("Heater Control", "Individual SSR + Digital PID via HMI"),
            ("Zone Control", "Individual zone temperature setting"),
            ("Heater Power (approx)", f"{heater_power} kW"),
            ("", ""),
            ("VACUUM & PRESSURE", ""),
            ("Vacuum System", f"~{vacuum_capacity} m3/hr capacity"),
            ("Vacuum Tank", "Dedicated tank for instant vacuum"),
            ("Pre-blow / Sag Control", "Yes (closed chamber with light sensors)"),
            ("Compressed Air", "~6 bar (100 psi) required"),
            ("", ""),
            ("CONTROL SYSTEM", ""),
            ("PLC", "Siemens / equivalent industrial PLC"),
            ("HMI", '7" color touchscreen'),
            ("Recipe Storage", "Multiple recipes with parameter save/recall"),
            ("Diagnostics", "Built-in fault diagnostics and alarm history"),
            ("", ""),
            ("COOLING", ""),
            ("Cooling System", "Centrifugal fans (standard)"),
            ("Optional Cooling", "Spray mist cooling (on request)"),
            ("", ""),
            ("SAFETY", ""),
            ("Safety Features", "Emergency stops, safety interlocks, light curtains"),
            ("CE Marking", "Available for export models"),
        ])

        row_idx = 0
        for spec_name, spec_val in specs:
            if spec_name == "" and spec_val == "":
                self.ln(2)
                continue
            if spec_val == "":
                self.set_font("Helvetica", "B", 9)
                self.set_text_color(*MACHINECRAFT_BLUE)
                self.cell(0, 6, spec_name, new_x="LMARGIN", new_y="NEXT")
                self.set_text_color(*MACHINECRAFT_DARK)
                row_idx = 0
                continue
            self._table_row(spec_name, spec_val, bold_col1=True, fill=(row_idx % 2 == 0))
            row_idx += 1

    def _render_power_requirements(self, is_servo, heater_power, total_power, vacuum_capacity, w, h):
        """Power, utilities, and infrastructure requirements."""
        self.section_title("POWER & UTILITY REQUIREMENTS")

        vacuum_motor_kw = max(3, int(vacuum_capacity / 40))
        compressed_air_cfm = max(20, int((w * h / 1_000_000) * 15))

        reqs = [
            ("Total Connected Load", f"~{total_power} kW"),
            ("Heater Power", f"~{heater_power} kW"),
            ("Drive System Power", f"~{45 if is_servo else 20} kW"),
            ("Vacuum Pump Motor", f"~{vacuum_motor_kw} kW"),
            ("Power Supply", "400V / 440V, 50Hz, 3-Phase + Neutral + Earth"),
            ("", ""),
            ("Compressed Air Supply", f"~6 bar (100 psi), {compressed_air_cfm} CFM minimum"),
            ("Cooling Water", "Not required (air-cooled standard)"),
            ("Vacuum Capacity", f"~{vacuum_capacity} m3/hr"),
        ]

        for i, (label, val) in enumerate(reqs):
            if label == "" and val == "":
                self.ln(2)
                continue
            self._table_row(label, val, bold_col1=True, fill=(i % 2 == 0))

    def _render_floor_plan(self, w, h, is_servo):
        """Machine dimensions and floor plan requirements."""
        self.section_title("FLOOR PLAN & DIMENSIONS")

        machine_length_mm = w + 2500 if is_servo else w + 2000
        machine_width_mm = h + 1500 if is_servo else h + 1200
        machine_height_mm = 3200 if is_servo else 2800
        machine_weight_kg = int((w * h / 1_000_000) * 4000) + (2000 if is_servo else 1000)

        clearance_front = 2000
        clearance_sides = 1500
        clearance_rear = 1500
        clearance_top = 1000

        floor_length = machine_length_mm + clearance_front + clearance_rear
        floor_width = machine_width_mm + clearance_sides * 2

        dims = [
            ("MACHINE DIMENSIONS (APPROX)", ""),
            ("Machine Length", f"~{machine_length_mm} mm"),
            ("Machine Width", f"~{machine_width_mm} mm"),
            ("Machine Height", f"~{machine_height_mm} mm"),
            ("Machine Weight (approx)", f"~{machine_weight_kg} kg"),
            ("", ""),
            ("FLOOR SPACE REQUIREMENTS", ""),
            ("Minimum Floor Area", f"~{floor_length} x {floor_width} mm ({floor_length * floor_width / 1_000_000:.1f} m2)"),
            ("Front Clearance", f"{clearance_front} mm (for sheet loading/part removal)"),
            ("Side Clearance", f"{clearance_sides} mm each side (maintenance access)"),
            ("Rear Clearance", f"{clearance_rear} mm (utilities and service access)"),
            ("Overhead Clearance", f"{clearance_top} mm above machine (oven movement)"),
            ("", ""),
            ("INSTALLATION", ""),
            ("Foundation", "Level concrete floor, minimum 200 mm thick"),
            ("Floor Loading", f"~{machine_weight_kg / ((machine_length_mm / 1000) * (machine_width_mm / 1000)):.0f} kg/m2"),
            ("Vibration Isolation", "Anti-vibration mounts included"),
        ]

        row_idx = 0
        for label, val in dims:
            if label == "" and val == "":
                self.ln(2)
                continue
            if val == "":
                self.set_font("Helvetica", "B", 9)
                self.set_text_color(*MACHINECRAFT_BLUE)
                self.cell(0, 6, label, new_x="LMARGIN", new_y="NEXT")
                self.set_text_color(*MACHINECRAFT_DARK)
                row_idx = 0
                continue
            self._table_row(label, val, bold_col1=True, fill=(row_idx % 2 == 0))
            row_idx += 1

    def _render_pricing(self, quote, is_servo):
        """Pricing table with line items."""
        self.section_title("PRICING")
        col_w = [110, 20, 50]
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*TABLE_HEADER_BG)
        self.set_text_color(255, 255, 255)
        self.cell(col_w[0], 7, "  Item", border=0, fill=True)
        self.cell(col_w[1], 7, "Qty", border=0, fill=True, align="C")
        self.cell(col_w[2], 7, "Price (INR)", border=0, fill=True, align="R",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*MACHINECRAFT_DARK)

        for i, item in enumerate(quote.line_items):
            if i % 2 == 0:
                self.set_fill_color(*TABLE_ALT_ROW)
            self.set_font("Helvetica", "", 9)
            self.cell(col_w[0], 6, self._safe(f"  {item.description[:55]}"), fill=(i % 2 == 0))
            self.cell(col_w[1], 6, str(item.quantity), fill=(i % 2 == 0), align="C")
            self.cell(col_w[2], 6, self._format_inr(item.total_price_inr), fill=(i % 2 == 0),
                      align="R", new_x="LMARGIN", new_y="NEXT")

        self.ln(1)
        self.set_draw_color(*MACHINECRAFT_BLUE)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

        self.set_font("Helvetica", "B", 9)
        self.cell(col_w[0], 6, "  Subtotal")
        self.cell(col_w[1], 6, "")
        self.cell(col_w[2], 6, self._format_inr(quote.subtotal_inr), align="R",
                  new_x="LMARGIN", new_y="NEXT")

        if quote.gst_inr > 0:
            self.set_font("Helvetica", "", 9)
            self.cell(col_w[0], 6, "  GST (18%)")
            self.cell(col_w[1], 6, "")
            self.cell(col_w[2], 6, self._format_inr(quote.gst_inr), align="R",
                      new_x="LMARGIN", new_y="NEXT")

        self.set_fill_color(*TOTAL_ROW_BG)
        self.set_font("Helvetica", "B", 10)
        self.cell(col_w[0], 8, "  TOTAL", fill=True)
        self.cell(col_w[1], 8, "", fill=True)
        self.cell(col_w[2], 8, self._format_inr(quote.total_inr), fill=True, align="R",
                  new_x="LMARGIN", new_y="NEXT")

        self.ln(2)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 5,
                  self._safe(f"Approximately ${quote.total_usd:,} USD. "
                             f"Price Ex-Works Machinecraft plant, Umargam, Gujarat. "
                             f"Subject to configuration and current pricing."),
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def _render_optional_extras(self, is_servo):
        """Optional extras table."""
        self.section_title("OPTIONAL EXTRAS")
        extras = [
            ("Additional Clamp Frames", "Custom-sized frames for different products"),
            ("Installation & Commissioning", "At customer site by Machinecraft engineers"),
            ("Operator Training", "2-3 days at customer site"),
        ]
        if not is_servo:
            extras.extend([
                ("Automatic Sheet Loading", "Powered loading system for faster cycles"),
                ("Universal Frame System", "Motorized aperture adjustment"),
            ])
        extras.extend([
            ("Enhanced Vacuum System", "Higher capacity pump for deep-draw parts"),
            ("Servo Vacuuming", "Programmable vacuum profiles"),
            ("Ball Transfer Tool Loading", "Easy mold changeover system"),
            ("Spray Mist Cooling", "Faster cooling for reduced cycle times"),
            ("IoT / Remote Monitoring", "VPN-based remote support module"),
            ("Additional Heater Zones", "Finer temperature control"),
        ])

        col_w = [70, 80, 30]
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*TABLE_HEADER_BG)
        self.set_text_color(255, 255, 255)
        self.cell(col_w[0], 6, "  Item", fill=True)
        self.cell(col_w[1], 6, "Description", fill=True)
        self.cell(col_w[2], 6, "Price", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*MACHINECRAFT_DARK)

        for i, (item, desc) in enumerate(extras):
            if i % 2 == 0:
                self.set_fill_color(*TABLE_ALT_ROW)
            self.set_font("Helvetica", "", 8)
            self.cell(col_w[0], 5, self._safe(f"  {item[:35]}"), fill=(i % 2 == 0))
            self.cell(col_w[1], 5, self._safe(desc[:40]), fill=(i % 2 == 0))
            self.cell(col_w[2], 5, "On Request", fill=(i % 2 == 0), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def _render_terms(self, quote):
        """Terms and conditions."""
        self.section_title("TERMS & CONDITIONS")
        self.key_value("Lead Time:", quote.delivery_time)
        self.key_value("Payment Terms:", quote.payment_terms)
        self.key_value("Shipping:", "EXW Machinecraft plant, Umargam, Gujarat, India")
        self.key_value("Warranty:", quote.warranty)
        self.key_value("Validity:", "This quotation is valid for 30 days from date of issue")
        self.ln(2)

        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*MACHINECRAFT_BLUE)
        self.cell(0, 5, "DELIVERY TERMS", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*MACHINECRAFT_DARK)
        self.set_font("Helvetica", "", 8)
        self.multi_cell(self.w - self.l_margin - self.r_margin, 4, self._safe(
            "Packing, freight, insurance, and on-site installation costs are not included "
            "unless explicitly stated. Buyer is responsible for import duties, taxes, and "
            "customs clearance at destination."
        ))
        self.ln(2)

        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*MACHINECRAFT_BLUE)
        self.cell(0, 5, "INSTALLATION & TRAINING", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*MACHINECRAFT_DARK)
        self.set_font("Helvetica", "", 8)
        self.multi_cell(self.w - self.l_margin - self.r_margin, 4, self._safe(
            "Machinecraft will provide on-site commissioning and basic operator training "
            "(2-3 days). Travel and lodging costs for technicians are extra. Extended "
            "training programs available on request."
        ))
        self.ln(2)

        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*MACHINECRAFT_BLUE)
        self.cell(0, 5, "FACTORY ACCEPTANCE TEST (FAT)", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*MACHINECRAFT_DARK)
        self.set_font("Helvetica", "", 8)
        self.multi_cell(self.w - self.l_margin - self.r_margin, 4, self._safe(
            "Machinecraft will perform a dry run test and run the machine on a demo tool "
            "with 1x material (ABS or PS) in 1x thickness at our factory prior to dispatch. "
            "Customer is welcome to attend FAT at our facility."
        ))
        self.ln(2)

    def _render_contact(self):
        """Contact information and signature block."""
        self.section_title("CONTACT INFORMATION")
        self.key_value("Rushabh Doshi", "Director - Sales & Marketing")
        self.key_value("Sales Team", "+91-22-40140000")
        self.key_value("Email", "sales@machinecraft.org")
        self.key_value("Direct Email", "rushabh@machinecraft.org")
        self.key_value("Technical Support", "support@machinecraft.org")
        self.key_value("Website", "www.machinecraft.org")
        self.ln(5)

        self.set_draw_color(*MACHINECRAFT_BLUE)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "For acceptance of this offer, please sign below and return a copy:",
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(8)
        self.cell(100, 5, "Accepted by (Authorized Signatory): ____________________")
        self.cell(0, 5, "Date: _____________", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(100)
        self.cell(0, 4, self._safe("(c) Machinecraft Technologies. All Rights Reserved."), align="C")


class Quotebuilder:
    """
    Agent that builds detailed quotes (tech spec, process flow, terms,
    optional extras) and exports them to PDF for customer attachment.
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
        """Render a GeneratedQuote to PDF. Returns path to the PDF file."""
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
        Build a detailed quote and save as PDF.
        Returns result with quote_id, pdf_path, total_inr, total_usd, model.
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
