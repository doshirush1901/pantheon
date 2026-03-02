#!/usr/bin/env python3
"""
TYCHE - Goddess of Fortune (Professional Quote Builder)
========================================================

Named after the Greek goddess of fortune and prosperity — every quote
Tyche builds is a chance at revenue.

The single authoritative quote system for Machinecraft. Builds detailed,
professional-grade quotations matching the real style from
data/imports/01_Quotes_and_Proposals/ and exports to PDF.

Data sources (all real, no formulas):
  - machine_database.py  -> MachineSpec (real specs from machine_specs.json)
  - pricing_estimator.py -> PricingEstimator + OPTION_PRICES_INR
  - detailed_specs_generator.py -> PF1_X_DETAILED_SPECS (subsystem detail)

Sections in the generated PDF:
  1. Quote Details (ID, date, model, validity, prepared by)
  2. Prepared For (customer, company, email, country)
  3. Machine Overview (narrative paragraph)
  4. Key Features (bullet points)
  5. Technical Specifications (full table from real DB data)
  6. Subsystem Details (heating, motion, vacuum, control, safety, brands)
  7. Pricing (line items table with real prices + selected options)
  8. Optional Extras (with actual INR prices from OPTION_PRICES_INR)
  9. Terms & Conditions (lead time, payment, shipping, warranty, FAT)
 10. Contact Information + acceptance block

Usage:
    from openclaw.agents.ira.src.agents.quotebuilder.agent import build_quote_pdf

    result = build_quote_pdf(
        machine_model="PF1-C-2015",
        customer_name="John Smith",
        company_name="Acme Corp",
        country="Germany",
    )
    print(result.pdf_path)  # data/exports/quotes/Quote_MT...pdf
"""

import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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
    from machine_database import MACHINE_SPECS, get_machine, find_machines_by_size, MachineSpec
    MACHINE_DB_AVAILABLE = True
except ImportError:
    MACHINE_DB_AVAILABLE = False

try:
    from pricing_estimator import PricingEstimator, OPTION_PRICES_INR, VARIANT_MULTIPLIERS, USD_INR_RATE
    PRICING_AVAILABLE = True
except ImportError:
    PRICING_AVAILABLE = False

try:
    from detailed_specs_generator import PF1_X_DETAILED_SPECS
    DETAILED_SPECS_AVAILABLE = True
except ImportError:
    DETAILED_SPECS_AVAILABLE = False

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False


EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"
QUOTE_PDF_EXPORTS = EXPORTS_DIR / "quotes"

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _safe(text: str) -> str:
    """Strip non-latin1 characters so fpdf2 Helvetica doesn't choke."""
    return text.encode("latin-1", "replace").decode("latin-1")


def _fmt_inr(amount: int) -> str:
    if amount >= 10_000_000:
        return f"Rs. {amount / 10_000_000:.2f} Cr"
    if amount >= 100_000:
        return f"Rs. {amount / 100_000:.1f} L"
    return f"Rs. {amount:,}"


def _fmt_usd(amount: int) -> str:
    return f"${amount:,}"


# ─── Data model ───────────────────────────────────────────────────────────────

@dataclass
class QuoteLineItem:
    description: str
    quantity: int = 1
    unit_price_inr: int = 0
    total_price_inr: int = 0


@dataclass
class QuoteData:
    """All data needed to render a professional quote PDF."""
    quote_id: str
    quote_date: str
    valid_until: str

    customer_name: str = ""
    company_name: str = ""
    customer_email: str = ""
    country: str = "India"

    machine_model: str = ""
    machine_series: str = ""
    machine_variant: str = ""
    machine_description: str = ""

    forming_area_mm: str = ""
    forming_area_raw: Tuple[int, int] = (0, 0)
    forming_area_sqm: float = 0.0
    max_tool_height_mm: int = 0
    max_draw_depth_mm: int = 0
    max_sheet_thickness_mm: float = 0.0
    min_sheet_thickness_mm: float = 0.0

    heater_type: str = ""
    heater_power_kw: float = 0.0
    total_power_kw: float = 0.0
    heater_zones: int = 0
    vacuum_pump_capacity: str = ""
    vacuum_tank_size: str = ""
    power_supply: str = ""

    is_servo: bool = False
    key_features: List[str] = field(default_factory=list)
    applications: List[str] = field(default_factory=list)

    line_items: List[QuoteLineItem] = field(default_factory=list)
    base_price_inr: int = 0
    options_total_inr: int = 0
    subtotal_inr: int = 0
    gst_inr: int = 0
    total_inr: int = 0
    total_usd: int = 0

    selected_options: Dict[str, int] = field(default_factory=dict)
    available_extras: List[Tuple[str, str, str]] = field(default_factory=list)

    delivery_time: str = "12-16 weeks from PO & advance payment"
    payment_terms: str = "30% advance, 60% before dispatch, 10% after installation"
    warranty: str = "12 months from installation or 18 months from dispatch"

    confidence: float = 0.9
    notes: List[str] = field(default_factory=list)


@dataclass
class BuildQuoteResult:
    quote_id: str
    pdf_path: str
    total_inr: int
    total_usd: int
    model: str
    summary: str = ""


# ─── Quote builder logic ─────────────────────────────────────────────────────

class Quotebuilder:
    """
    Builds professional-grade quotes from real machine data and renders to PDF.
    """

    def __init__(self):
        self._counter = self._load_counter()
        QUOTE_PDF_EXPORTS.mkdir(parents=True, exist_ok=True)

    # ── counter ───────────────────────────────────────────────────────────

    def _load_counter(self) -> int:
        f = PROJECT_ROOT / "data" / "quote_counter.txt"
        if f.exists():
            try:
                return int(f.read_text().strip())
            except (ValueError, IOError):
                pass
        return 1000

    def _save_counter(self):
        f = PROJECT_ROOT / "data" / "quote_counter.txt"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(str(self._counter))

    def _next_quote_id(self) -> str:
        self._counter += 1
        self._save_counter()
        return f"MT{datetime.now().strftime('%Y%m%d')}{self._counter % 1000:03d}"

    # ── resolve machine ───────────────────────────────────────────────────

    def _resolve_machine(
        self,
        machine_model: Optional[str],
        width_mm: Optional[int],
        height_mm: Optional[int],
        variant: str,
    ) -> "MachineSpec":
        if not MACHINE_DB_AVAILABLE:
            raise RuntimeError("machine_database not available")

        if machine_model:
            if machine_model in MACHINE_SPECS:
                return MACHINE_SPECS[machine_model]
            spec = get_machine(machine_model)
            if spec:
                return spec

        if width_mm and height_mm:
            matches = find_machines_by_size(min_width=width_mm, min_height=height_mm)
            target_variant = variant.upper()
            for m in matches:
                if target_variant in (m.variant or "").upper() or f"-{target_variant}-" in m.model:
                    return m
            if matches:
                return matches[0]

        raise ValueError(
            f"Machine not found. Provide a valid machine_model (e.g. PF1-C-2015) "
            f"or width_mm + height_mm."
        )

    # ── build quote data ──────────────────────────────────────────────────

    def build_quote(
        self,
        machine_model: Optional[str] = None,
        width_mm: Optional[int] = None,
        height_mm: Optional[int] = None,
        variant: str = "C",
        customer_name: str = "",
        company_name: str = "",
        customer_email: str = "",
        country: str = "India",
        options: Optional[Dict[str, str]] = None,
    ) -> QuoteData:
        options = options or {}
        spec = self._resolve_machine(machine_model, width_mm, height_mm, variant)

        is_servo = (
            "-X-" in spec.model or "-XL-" in spec.model or "-S-" in spec.model
            or (spec.variant and "servo" in spec.variant.lower())
        )
        var_letter = "X" if is_servo else "C"

        w, h = spec.forming_area_raw or (0, 0)
        sqm = round(w * h / 1_000_000, 2) if w and h else 0.0

        # ── pricing ──────────────────────────────────────────────────────
        base_price = spec.price_inr or 0
        if base_price == 0 and PRICING_AVAILABLE:
            est = PricingEstimator()
            pe = est.estimate_price(forming_area=(w, h), variant=var_letter, options=options, country=country)
            base_price = pe.base_price_inr

        line_items = [QuoteLineItem(
            description=f"{spec.model} Thermoforming Machine",
            quantity=1,
            unit_price_inr=base_price,
            total_price_inr=base_price,
        )]

        opts_total = 0
        selected_options: Dict[str, int] = {}
        if PRICING_AVAILABLE:
            est = PricingEstimator()
            _, breakdown = est._calculate_options_price(sqm, options, var_letter)
            for name, price in breakdown.items():
                line_items.append(QuoteLineItem(description=name, quantity=1, unit_price_inr=price, total_price_inr=price))
                selected_options[name] = price
                opts_total += price

        subtotal = base_price + opts_total
        is_export = country.lower() != "india"
        gst = 0 if is_export else int(subtotal * 0.18)
        total = subtotal + gst
        total_usd = total // (USD_INR_RATE if PRICING_AVAILABLE else 83)

        # ── key features from DB or generated ─────────────────────────────
        key_features = list(spec.features) if spec.features else []
        if not key_features:
            key_features = [
                "Closed-Chamber Zero-Sag Design",
                f"{spec.forming_area_mm} mm Forming Area",
                "Sandwich Heating Oven (Top & Bottom IR)",
                "PLC Control with Touchscreen HMI",
            ]
            if is_servo:
                key_features += ["All-Servo Drive System (Mitsubishi)", "Universal Motorized Aperture Setting", "Automatic Sheet Loading System"]
            else:
                key_features += ["Pneumatic Forming System (rack & pinion)", "Fixed Clamp Frames (1 frame included)"]
            key_features.append("Pre-blow / Sag Control with Light Sensors")

        # ── optional extras not already selected ──────────────────────────
        extras: List[Tuple[str, str, str]] = []
        _extra_defs = [
            ("frame_universal", "Universal Frame System", "Motorized X-Y adjustment"),
            ("loading_robotic", "Automatic Sheet Loading", "Servo-driven pick & place"),
            ("loading_roll_feeder", "Roll Feeder", "Continuous roll feeding"),
            ("heater_quartz", "IR Quartz Heaters", "~25% energy savings"),
            ("heater_halogen", "IR Halogen Heaters", "~50% energy savings, fastest"),
            ("controller_heatronik", "Heatronik Controller", "Closed-loop heater control"),
            ("cooling_ducted", "Central Ducted Cooling", "20-40% faster cooling"),
            ("plug_assist", "Plug Assist System", "For deep-draw parts"),
            ("pressure_forming", "Pressure Forming Kit", "Up to 6 bar positive pressure"),
            ("twin_sheet", "Twin Sheet Capability", "Two-sheet simultaneous forming"),
            ("clamp_pneumatic", "Pneumatic Tool Clamps", "Quick tool change"),
            ("tool_ball_transfer", "Ball Transfer Units", "Easy tool sliding on platen"),
        ]
        if PRICING_AVAILABLE:
            for key, name, desc in _extra_defs:
                if name not in selected_options:
                    price = OPTION_PRICES_INR.get(key, 0)
                    if price > 0:
                        if "heater" in key and "per" not in desc.lower():
                            price_str = f"Rs. {int(price * max(sqm, 1)):,}"
                        else:
                            price_str = f"Rs. {price:,}"
                        extras.append((name, desc, price_str))
        else:
            for _, name, desc in _extra_defs:
                extras.append((name, desc, "On Request"))
        extras.append(("Installation & Commissioning", "At customer site", "On Request"))
        extras.append(("Operator Training (3 days)", "At customer site", "On Request"))
        extras.append(("IoT / Remote Monitoring", "VPN-based support module", "On Request"))

        # ── notes ─────────────────────────────────────────────────────────
        notes: List[str] = []
        if is_export:
            notes.append("Export pricing - GST exempt. Shipping Ex-Works.")
        notes.append("All prices subject to configuration and current pricing.")

        return QuoteData(
            quote_id=self._next_quote_id(),
            quote_date=datetime.now().strftime("%d %B %Y"),
            valid_until=(datetime.now() + timedelta(days=30)).strftime("%d %B %Y"),
            customer_name=customer_name or "Valued Customer",
            company_name=company_name,
            customer_email=customer_email,
            country=country,
            machine_model=spec.model,
            machine_series=spec.series,
            machine_variant=var_letter,
            machine_description=spec.description or "",
            forming_area_mm=spec.forming_area_mm,
            forming_area_raw=(w, h),
            forming_area_sqm=sqm,
            max_tool_height_mm=spec.max_tool_height_mm,
            max_draw_depth_mm=spec.max_draw_depth_mm,
            max_sheet_thickness_mm=spec.max_sheet_thickness_mm,
            min_sheet_thickness_mm=spec.min_sheet_thickness_mm,
            heater_type=spec.heater_type or ("IR Ceramic/Quartz" if is_servo else "IR Ceramic"),
            heater_power_kw=spec.heater_power_kw,
            total_power_kw=spec.total_power_kw,
            heater_zones=spec.heater_zones,
            vacuum_pump_capacity=spec.vacuum_pump_capacity,
            vacuum_tank_size=spec.vacuum_tank_size,
            power_supply=spec.power_supply or "415V, 50Hz, 3P+N+PE",
            is_servo=is_servo,
            key_features=key_features,
            applications=spec.applications or [],
            line_items=line_items,
            base_price_inr=base_price,
            options_total_inr=opts_total,
            subtotal_inr=subtotal,
            gst_inr=gst,
            total_inr=total,
            total_usd=total_usd,
            selected_options=selected_options,
            available_extras=extras,
            notes=notes,
        )

    # ── render PDF ────────────────────────────────────────────────────────

    def render_pdf(self, q: QuoteData, output_path: Optional[Path] = None) -> str:
        if not FPDF_AVAILABLE:
            raise ImportError("fpdf2 is required. Install with: pip install fpdf2")

        pdf = _QuotePDF()
        pdf.alias_nb_pages()
        pdf.render(q)

        path = output_path or (QUOTE_PDF_EXPORTS / f"Quote_{q.quote_id}_{q.machine_model}.pdf")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        pdf.output(str(path))
        return str(path)

    # ── public convenience ────────────────────────────────────────────────

    def build_and_export(
        self,
        machine_model: Optional[str] = None,
        width_mm: Optional[int] = None,
        height_mm: Optional[int] = None,
        variant: str = "C",
        customer_name: str = "",
        company_name: str = "",
        customer_email: str = "",
        country: str = "India",
        options: Optional[Dict[str, str]] = None,
    ) -> BuildQuoteResult:
        q = self.build_quote(
            machine_model=machine_model,
            width_mm=width_mm, height_mm=height_mm, variant=variant,
            customer_name=customer_name, company_name=company_name,
            customer_email=customer_email, country=country, options=options,
        )
        pdf_path = self.render_pdf(q)
        summary = (
            f"Quote {q.quote_id} for {q.machine_model} "
            f"({q.forming_area_mm} mm). "
            f"Total: {_fmt_inr(q.total_inr)} ({_fmt_usd(q.total_usd)} USD). "
            f"PDF: {pdf_path}"
        )
        return BuildQuoteResult(
            quote_id=q.quote_id,
            pdf_path=pdf_path,
            total_inr=q.total_inr,
            total_usd=q.total_usd,
            model=q.machine_model,
            summary=summary,
        )


# ─── PDF renderer ────────────────────────────────────────────────────────────

class _QuotePDF(FPDF if FPDF_AVAILABLE else object):

    def __init__(self):
        if not FPDF_AVAILABLE:
            raise ImportError("fpdf2 required")
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)

    # ── chrome ────────────────────────────────────────────────────────────

    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, _safe("MACHINECRAFT TECHNOLOGIES"), align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 8)
        self.cell(0, 4, _safe("Plot 92, Dehri Road, Umbergaon, Dist. Valsad, Gujarat-396170, India"), align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 4, _safe("Tel: +91-22-40140000 | sales@machinecraft.org | www.machinecraft.org"), align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)
        self.set_draw_color(40, 40, 40)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(120)
        self.cell(0, 3, _safe("Machinecraft Technologies - 505, Palm Springs, Link Road, Malad (W), Mumbai 400064, India"), align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 3, _safe("Factory: Plot 92, Umbergaon Station-Dehri Rd, Valsad, Gujarat 396170"), align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 3, _safe(f"Page {self.page_no()}/{{nb}}"), align="C")

    # ── primitives ────────────────────────────────────────────────────────

    def _section(self, title: str):
        self.ln(4)
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(30, 60, 110)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, _safe(f"  {title}"), fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0)
        self.ln(2)

    def _kv(self, key: str, value: str, kw: int = 55):
        self.set_font("Helvetica", "B", 9)
        self.cell(kw, 5, _safe(key))
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, _safe((value or "-")[:90]), new_x="LMARGIN", new_y="NEXT")

    def _para(self, text: str, size: int = 9):
        self.set_font("Helvetica", "", size)
        self.multi_cell(self.w - self.l_margin - self.r_margin, 4.5, _safe(text))

    def _bullet(self, text: str, size: int = 9):
        self.set_font("Helvetica", "", size)
        x = self.get_x()
        self.cell(5, 5, _safe(chr(149)))
        self.multi_cell(self.w - self.l_margin - self.r_margin - 5, 5, _safe(text))

    # ── main render ───────────────────────────────────────────────────────

    def render(self, q: QuoteData):
        self.add_page()

        # Title
        self.set_font("Helvetica", "B", 18)
        self.cell(0, 12, "QUOTATION", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

        # ── 1. Quote details ─────────────────────────────────────────────
        self._section("QUOTE DETAILS")
        self._kv("Quote Reference:", q.quote_id)
        self._kv("Date:", q.quote_date)
        self._kv("Machine Model:", q.machine_model)
        self._kv("Validity:", "30 days from date of issue")
        self._kv("Prepared by:", "Rushabh Doshi, Director - Sales & Marketing")

        # ── 2. Customer ──────────────────────────────────────────────────
        if q.customer_name and q.customer_name != "Valued Customer":
            self._section("PREPARED FOR")
            self._kv("Client:", q.customer_name)
            if q.company_name:
                self._kv("Company:", q.company_name)
            if q.customer_email:
                self._kv("Email:", q.customer_email)
            self._kv("Country:", q.country)

        # ── 3. Machine overview ──────────────────────────────────────────
        self._section(f"{q.machine_model} - MACHINE OVERVIEW")
        variant_name = "All-Servo with Automatic Sheet Loading" if q.is_servo else "Pneumatic"
        overview = (
            f"The {q.machine_model} is a heavy-gauge, single-station cut-sheet thermoforming "
            f"machine from the PF1 Series ({variant_name}). It features a robust closed-chamber "
            f"design that prevents sheet sag via pre-blow air pressure control, ensuring superior "
            f"forming quality on thick materials."
        )
        if q.forming_area_mm:
            overview += (
                f" With a generous {q.forming_area_mm} mm forming area ({q.forming_area_sqm} sq.m), "
                f"it delivers precision forming for thermoplastic sheets "
                f"({q.min_sheet_thickness_mm or 2}-{q.max_sheet_thickness_mm or 12} mm thick), "
                f"ideal for automotive, aerospace, industrial, and commercial applications."
            )
        if q.machine_description:
            overview += f" {q.machine_description}"
        self._para(overview)
        self.ln(2)

        # ── 4. Key features ──────────────────────────────────────────────
        self._section("KEY FEATURES")
        for feat in q.key_features[:12]:
            self._bullet(feat)
        self.ln(1)

        # ── 5. Technical specifications ──────────────────────────────────
        self._section("TECHNICAL SPECIFICATIONS")
        self._kv("Machine Model:", q.machine_model)
        self._kv("Series:", f"PF1 ({variant_name})")
        self._kv("Forming Area (Max):", f"{q.forming_area_mm} mm")
        self._kv("Forming Area:", f"{q.forming_area_sqm} sq.m")
        if q.max_tool_height_mm:
            self._kv("Max Tool Height:", f"{q.max_tool_height_mm} mm")
        if q.max_draw_depth_mm:
            self._kv("Max Draw Depth:", f"{q.max_draw_depth_mm} mm")
        self._kv("Sheet Thickness:", f"{q.min_sheet_thickness_mm or 2}-{q.max_sheet_thickness_mm or 12} mm")
        self.ln(1)

        # Drives & loading
        if q.is_servo:
            self._kv("Drive System:", "All-Servo (Mitsubishi servo motors)")
            self._kv("Clamp Frame:", "Servo-driven universal aperture (X-Y motorized)")
            self._kv("Sheet Loading:", "Automatic (servo-driven pick & place)")
            self._kv("Forming Platen:", "Servo motor driven (Z-axis)")
            self._kv("Heater Oven Drive:", "Servo motor driven")
            self._kv("Plug Assist:", "Servo driven (programmable profiles)")
            self._kv("Frame Changeover:", "< 5 minutes via touchscreen")
        else:
            self._kv("Drive System:", "Pneumatic (air cylinder driven)")
            self._kv("Clamp Frame:", "Fixed welded frames (1 frame included)")
            self._kv("Sheet Loading:", "Manual by operator")
            self._kv("Forming Platen:", "Pneumatic (4 cylinders + rack & pinion)")
            self._kv("Heater Oven Drive:", "Pneumatic (high-temp cylinders)")
            self._kv("Plug Assist:", "Pneumatic (manual height adjustment)")
            self._kv("Frame Changeover:", "1-2 hours (manual swap)")
        self.ln(1)

        # Heating
        self._kv("Heating Configuration:", "Sandwich - Top & Bottom")
        self._kv("Heater Type:", q.heater_type)
        if q.heater_power_kw:
            self._kv("Heater Power:", f"{q.heater_power_kw} kW")
        if q.heater_zones:
            self._kv("Heater Zones:", f"{q.heater_zones} independently controlled zones")
        self._kv("Heater Control:", "SSR with PID per zone (Heatronik optional)")
        self.ln(1)

        # Vacuum
        if q.vacuum_pump_capacity:
            self._kv("Vacuum Pump:", f"Oil-lubricated rotary vane ({q.vacuum_pump_capacity})")
        if q.vacuum_tank_size:
            self._kv("Vacuum Tank:", q.vacuum_tank_size)
        self._kv("Vacuum Features:", "Rapid evacuation, preblow, air ejection")
        self.ln(1)

        # Control & electrical
        self._kv("Control System:", "Mitsubishi PLC (Japan)")
        self._kv("HMI:", '10.1" industrial touchscreen (upgradeable to 15")')
        if q.is_servo:
            self._kv("Servo Drives:", "Mitsubishi for all motion axes")
        self._kv("Recipe Storage:", "SD card with real-time visualization")
        if q.total_power_kw:
            self._kv("Total Connected Load:", f"{q.total_power_kw} kW")
        self._kv("Power Supply:", q.power_supply)
        self.ln(1)

        # Cooling, safety, sag
        self._kv("Cooling:", "Centrifugal fans (ducted cooling optional)")
        self._kv("Sag Control:", "Closed chamber with light sensors + preblow")
        self._kv("Compressed Air:", "~6 bar (100 psi)")
        self._kv("Safety:", "CE compliant, perimeter guards, light curtains, E-stops")
        self.ln(1)

        # Component brands
        self._section("COMPONENT BRANDS")
        self._kv("PLC & Servos:", "Mitsubishi Electric (Japan)")
        self._kv("Pneumatics:", "Festo / SMC")
        self._kv("Sensors:", "Keyence / Sick / P+F")
        self._kv("Vacuum Pumps:", "Busch / Becker")
        self._kv("Heaters:", "Elstein / TQS / Ceramicx")
        self._kv("Switchgear:", "Eaton / Siemens")

        # ── 6. Applications ──────────────────────────────────────────────
        if q.applications:
            self._section("TYPICAL APPLICATIONS")
            for app in q.applications[:8]:
                self._bullet(app)
            self.ln(1)

        # ── 7. Pricing ───────────────────────────────────────────────────
        self._section("PRICING")
        col_w = [110, 20, 30, 30]
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(220, 220, 220)
        headers = ["Item", "Qty", "Unit Price", "Total"]
        for i, h in enumerate(headers):
            align = "R" if i >= 2 else ("C" if i == 1 else "L")
            nxy = {"new_x": "LMARGIN", "new_y": "NEXT"} if i == len(headers) - 1 else {}
            self.cell(col_w[i], 7, h, border=1, fill=True, align=align, **nxy)

        self.set_font("Helvetica", "", 9)
        for item in q.line_items:
            self.cell(col_w[0], 6, _safe(item.description[:55]), border=1)
            self.cell(col_w[1], 6, str(item.quantity), border=1, align="C")
            self.cell(col_w[2], 6, _safe(_fmt_inr(item.unit_price_inr)), border=1, align="R")
            self.cell(col_w[3], 6, _safe(_fmt_inr(item.total_price_inr)), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

        # Totals
        tw = col_w[0] + col_w[1] + col_w[2]
        self.set_font("Helvetica", "B", 9)
        self.cell(tw, 6, "Subtotal", border=1, align="R")
        self.cell(col_w[3], 6, _safe(_fmt_inr(q.subtotal_inr)), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
        if q.gst_inr > 0:
            self.cell(tw, 6, "GST (18%)", border=1, align="R")
            self.cell(col_w[3], 6, _safe(_fmt_inr(q.gst_inr)), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_fill_color(200, 230, 200)
        self.set_font("Helvetica", "B", 10)
        self.cell(tw, 8, "TOTAL", border=1, align="R", fill=True)
        self.cell(col_w[3], 8, _safe(_fmt_inr(q.total_inr)), border=1, align="R", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 5, _safe(f"Approximately {_fmt_usd(q.total_usd)} USD. Price Ex-Works Machinecraft plant, Umargam, Gujarat."), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

        # ── 8. Optional extras ───────────────────────────────────────────
        if q.available_extras:
            self._section("OPTIONAL EXTRAS (available at additional cost)")
            ecol = [65, 65, 40]
            self.set_font("Helvetica", "B", 8)
            self.set_fill_color(240, 240, 240)
            self.cell(ecol[0], 6, "Option", border=1, fill=True)
            self.cell(ecol[1], 6, "Description", border=1, fill=True)
            self.cell(ecol[2], 6, "Indicative Price", border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
            self.set_font("Helvetica", "", 8)
            for name, desc, price in q.available_extras:
                self.cell(ecol[0], 5, _safe(name[:32]), border=1)
                self.cell(ecol[1], 5, _safe(desc[:32]), border=1)
                self.cell(ecol[2], 5, _safe(price), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

        # ── 9. Terms & conditions ────────────────────────────────────────
        self._section("TERMS & CONDITIONS")
        self._kv("Lead Time:", q.delivery_time)
        self._kv("Payment Terms:", q.payment_terms)
        self._kv("Shipping:", "EXW Machinecraft plant, Umargam, Gujarat, India")
        self._kv("Warranty:", q.warranty)
        self._kv("Validity:", f"This quotation is valid until {q.valid_until}")
        self.ln(2)
        self.set_font("Helvetica", "", 8)
        terms = (
            "DELIVERY TERMS: Packing, freight, insurance, and on-site installation costs are not "
            "included unless explicitly stated. "
            "INSTALLATION & TRAINING: Machinecraft will provide on-site commissioning and basic "
            "operator training. Travel and lodging costs for technicians are extra. "
            "FAT: Machinecraft will do a dry run test and run the machine on demo tool with "
            "1x material like ABS or PS in 1x thickness."
        )
        self.multi_cell(self.w - self.l_margin - self.r_margin, 3.5, _safe(terms))
        self.ln(2)

        # Notes
        if q.notes:
            self.set_font("Helvetica", "I", 8)
            for note in q.notes:
                self._bullet(note, size=8)
            self.ln(2)

        # ── 10. Contact ──────────────────────────────────────────────────
        self._section("CONTACT INFORMATION")
        self._kv("Sales Director:", "Rushabh Doshi")
        self._kv("Phone:", "+91-22-40140000")
        self._kv("Email:", "sales@machinecraft.org")
        self._kv("Direct:", "rushabh@machinecraft.org")
        self._kv("Website:", "www.machinecraft.org")

        self.ln(8)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, _safe("For acceptance of this offer, please sign below and return a copy:"), new_x="LMARGIN", new_y="NEXT")
        self.ln(8)
        self.set_draw_color(100)
        self.line(15, self.get_y(), 100, self.get_y())
        self.line(120, self.get_y(), 190, self.get_y())
        self.ln(2)
        self.set_font("Helvetica", "I", 8)
        self.cell(100, 4, "Authorized Signatory")
        self.cell(0, 4, "Date", new_x="LMARGIN", new_y="NEXT")


# ─── Singleton & convenience ─────────────────────────────────────────────────

_instance: Optional[Quotebuilder] = None


def get_quotebuilder() -> Quotebuilder:
    global _instance
    if _instance is None:
        _instance = Quotebuilder()
    return _instance


def build_quote_pdf(
    machine_model: Optional[str] = None,
    width_mm: Optional[int] = None,
    height_mm: Optional[int] = None,
    variant: str = "C",
    customer_name: str = "",
    company_name: str = "",
    customer_email: str = "",
    country: str = "India",
    options: Optional[Dict[str, str]] = None,
) -> BuildQuoteResult:
    """
    Build a professional-grade quote and export to PDF.

    Provide either machine_model (e.g. "PF1-C-2015") or width_mm + height_mm.
    Returns BuildQuoteResult with quote_id, pdf_path, totals, model.
    """
    return get_quotebuilder().build_and_export(
        machine_model=machine_model,
        width_mm=width_mm, height_mm=height_mm, variant=variant,
        customer_name=customer_name, company_name=company_name,
        customer_email=customer_email, country=country, options=options,
    )
