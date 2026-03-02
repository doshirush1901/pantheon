#!/usr/bin/env python3
"""
SALES QUOTE GENERATOR - Production-Ready Quote Automation
=========================================================

Generates professional PDF quotes for Machinecraft customers.
Integrates with the identity system, machine database, and CRM pipeline.

Features:
- Pull customer details from unified identity system
- Get machine specs and pricing from database
- Generate formatted PDF quotes using fpdf2
- Track quotes in the CRM pipeline
- Support for both single quotes and batch generation

Usage:
    from src.sales.quote_generator import generate_quote, SalesQuoteGenerator
    
    # Simple generation
    pdf_path = generate_quote(
        customer_id="c_abc123",
        machine_id="PF1-C-2015",
        quantity=1
    )
    
    # Advanced usage
    generator = SalesQuoteGenerator()
    quote = generator.create_quote(customer_id, machine_id, quantity)
    pdf_path = generator.generate_pdf(quote)
"""

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

SKILL_DIR = Path(__file__).parent
SKILLS_DIR = SKILL_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(SKILLS_DIR / "brain"))
sys.path.insert(0, str(SKILLS_DIR / "identity"))
sys.path.insert(0, str(SKILLS_DIR / "crm"))
sys.path.insert(0, str(AGENT_DIR))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

try:
    from machine_database import get_machine, MACHINE_SPECS, MachineSpec
    MACHINE_DB_AVAILABLE = True
except ImportError:
    MACHINE_DB_AVAILABLE = False

try:
    from unified_identity import get_identity_service, Contact
    IDENTITY_AVAILABLE = True
except ImportError:
    IDENTITY_AVAILABLE = False

try:
    from quote_lifecycle import get_tracker
    CRM_AVAILABLE = True
except ImportError:
    CRM_AVAILABLE = False

try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


@dataclass
class QuoteItem:
    """Single line item in a quote."""
    description: str
    quantity: int = 1
    unit_price_inr: int = 0
    total_price_inr: int = 0
    notes: str = ""


@dataclass
class SalesQuote:
    """Complete sales quote data."""
    quote_id: str
    quote_date: str
    valid_until: str
    
    customer_id: str
    customer_name: str
    company_name: str
    customer_email: str
    customer_phone: str
    country: str
    
    machine_model: str
    machine_series: str
    machine_variant: str
    quantity: int
    
    forming_area_mm: Tuple[int, int]
    
    line_items: List[QuoteItem] = field(default_factory=list)
    
    base_price_inr: int = 0
    options_total_inr: int = 0
    subtotal_inr: int = 0
    gst_inr: int = 0
    total_inr: int = 0
    total_usd: int = 0
    
    delivery_time: str = "12-16 weeks"
    payment_terms: str = "30% advance, 60% before dispatch, 10% after installation"
    warranty: str = "12 months from installation or 18 months from dispatch"
    
    key_features: List[str] = field(default_factory=list)
    technical_specs: Dict[str, Any] = field(default_factory=dict)
    
    pdf_path: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "quote_id": self.quote_id,
            "quote_date": self.quote_date,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "company_name": self.company_name,
            "machine_model": self.machine_model,
            "quantity": self.quantity,
            "total_inr": self.total_inr,
            "total_usd": self.total_usd,
        }


class QuotePDF(FPDF if PDF_AVAILABLE else object):
    """Custom PDF generator for Machinecraft quotes."""
    
    def __init__(self):
        if not PDF_AVAILABLE:
            raise ImportError("fpdf2 is required. Install with: pip install fpdf2")
        super().__init__()
        self.add_page()
        self.set_auto_page_break(auto=True, margin=15)
    
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "MACHINECRAFT TECHNOLOGIES", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "Plot 92, Dehri Road, Umbergaon, Dist. Valsad, Gujarat-396170, India", 
                  align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 5, "Tel: +91-22-40140000 | Email: sales@machinecraft.org | Web: www.machinecraft.org",
                  align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)
        self.set_draw_color(0, 0, 0)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
    
    def footer(self):
        self.set_y(-25)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128)
        self.cell(0, 4, "Machinecraft Technologies - 505, Palm Springs, Link Road, Malad (W), Mumbai 400064, India",
                  align="C", new_x="LMARGIN", new_y="NEXT")
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
        self.cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")
    
    def bullet_point(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.cell(5, 6, chr(149))  # bullet character
        self.multi_cell(0, 6, text)
    
    def price_table(self, items: List[QuoteItem], subtotal: int, gst: int, total: int, total_usd: int):
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(220, 220, 220)
        self.cell(100, 8, "Description", border=1, fill=True)
        self.cell(25, 8, "Qty", border=1, fill=True, align="C")
        self.cell(35, 8, "Unit Price", border=1, fill=True, align="R")
        self.cell(30, 8, "Total", border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
        
        self.set_font("Helvetica", "", 10)
        for item in items:
            self.cell(100, 7, item.description[:45], border=1)
            self.cell(25, 7, str(item.quantity), border=1, align="C")
            self.cell(35, 7, self._format_inr(item.unit_price_inr), border=1, align="R")
            self.cell(30, 7, self._format_inr(item.total_price_inr), border=1, align="R", 
                      new_x="LMARGIN", new_y="NEXT")
        
        self.set_font("Helvetica", "B", 10)
        self.cell(160, 7, "Subtotal:", border=1, align="R")
        self.cell(30, 7, self._format_inr(subtotal), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
        
        if gst > 0:
            self.cell(160, 7, "GST (18%):", border=1, align="R")
            self.cell(30, 7, self._format_inr(gst), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
        
        self.set_fill_color(200, 230, 200)
        self.cell(160, 8, "TOTAL:", border=1, align="R", fill=True)
        self.cell(30, 8, self._format_inr(total), border=1, align="R", fill=True, new_x="LMARGIN", new_y="NEXT")
        
        self.set_font("Helvetica", "I", 9)
        self.cell(0, 6, f"Approximately ${total_usd:,} USD", align="R", new_x="LMARGIN", new_y="NEXT")
    
    def _format_inr(self, amount: int) -> str:
        if amount >= 10000000:
            return f"{amount/10000000:.2f} Cr"
        elif amount >= 100000:
            return f"{amount/100000:.1f} L"
        else:
            return f"{amount:,}"


class SalesQuoteGenerator:
    """
    Production-ready quote generator that pulls from identity system,
    machine database, and tracks quotes in CRM.
    """
    
    EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"
    
    def __init__(self):
        self._quote_counter = self._load_counter()
        self.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_counter(self) -> int:
        counter_file = PROJECT_ROOT / "data" / "quote_counter.txt"
        if counter_file.exists():
            try:
                return int(counter_file.read_text().strip())
            except (ValueError, IOError):
                pass
        return 1000
    
    def _save_counter(self, counter: int):
        counter_file = PROJECT_ROOT / "data" / "quote_counter.txt"
        counter_file.parent.mkdir(parents=True, exist_ok=True)
        counter_file.write_text(str(counter))
    
    def _generate_quote_id(self) -> str:
        self._quote_counter += 1
        self._save_counter(self._quote_counter)
        return f"MT{datetime.now().strftime('%Y%m%d')}{self._quote_counter % 100:02d}"
    
    def _get_customer_details(self, customer_id: str) -> Dict[str, Any]:
        """Pull customer details from identity system."""
        if IDENTITY_AVAILABLE:
            identity_service = get_identity_service()
            contact = identity_service.get_contact(customer_id)
            if contact:
                return {
                    "name": contact.name or "Valued Customer",
                    "email": contact.email or "",
                    "phone": contact.phone or "",
                    "company": contact.company or "",
                    "country": contact.metadata.get("country", "India"),
                }
        return {
            "name": "Valued Customer",
            "email": "",
            "phone": "",
            "company": "",
            "country": "India",
        }
    
    def _get_machine_details(self, machine_id: str) -> Optional[MachineSpec]:
        """Get machine specs from database."""
        if MACHINE_DB_AVAILABLE:
            return get_machine(machine_id)
        return None
    
    def create_quote(
        self,
        customer_id: str,
        machine_id: str,
        quantity: int = 1,
        options: Dict[str, Any] = None,
    ) -> SalesQuote:
        """
        Create a complete quote by pulling customer and machine data.
        
        Args:
            customer_id: Unified identity contact_id
            machine_id: Machine model (e.g., "PF1-C-2015")
            quantity: Number of machines
            options: Additional options dict
        
        Returns:
            SalesQuote with all data populated
        """
        options = options or {}
        
        customer = self._get_customer_details(customer_id)
        machine = self._get_machine_details(machine_id)
        
        if not machine:
            raise ValueError(f"Machine {machine_id} not found in database")
        
        base_price = machine.price_inr or 0
        total_base = base_price * quantity
        
        line_items = [
            QuoteItem(
                description=f"{machine.model} Thermoforming Machine",
                quantity=quantity,
                unit_price_inr=base_price,
                total_price_inr=total_base,
            )
        ]
        
        options_total = 0
        if options.get("spare_parts_kit"):
            spare_price = int(base_price * 0.05)
            line_items.append(QuoteItem(
                description="Spare Parts Kit (1 year)",
                quantity=quantity,
                unit_price_inr=spare_price,
                total_price_inr=spare_price * quantity,
            ))
            options_total += spare_price * quantity
        
        if options.get("installation"):
            install_price = 200000 if customer["country"] == "India" else 500000
            line_items.append(QuoteItem(
                description="Installation & Commissioning",
                quantity=1,
                unit_price_inr=install_price,
                total_price_inr=install_price,
            ))
            options_total += install_price
        
        if options.get("training"):
            training_price = 100000
            line_items.append(QuoteItem(
                description="Operator Training (3 days)",
                quantity=1,
                unit_price_inr=training_price,
                total_price_inr=training_price,
            ))
            options_total += training_price
        
        subtotal = total_base + options_total
        is_export = customer["country"].lower() != "india"
        gst = 0 if is_export else int(subtotal * 0.18)
        total = subtotal + gst
        total_usd = total // 83
        
        is_servo = machine.variant and ("X" in machine.variant or "servo" in machine.variant.lower())
        key_features = [
            "Closed-Chamber Zero-Sag Design",
            f"{machine.forming_area_mm} Forming Area",
            "Sandwich Heating Oven (Top & Bottom IR)",
            "PLC Control with 7\" Touchscreen HMI",
        ]
        if is_servo:
            key_features.extend([
                "All-Servo Drive System",
                "Universal Motorized Aperture Setting",
            ])
        else:
            key_features.extend([
                "Pneumatic Forming System",
                "Fixed Clamp Frames (1 included)",
            ])
        key_features.append("Pre-blow / Sag Control with Light Sensors")
        
        quote = SalesQuote(
            quote_id=self._generate_quote_id(),
            quote_date=datetime.now().strftime("%Y-%m-%d"),
            valid_until=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            customer_id=customer_id,
            customer_name=customer["name"],
            company_name=customer["company"],
            customer_email=customer["email"],
            customer_phone=customer["phone"],
            country=customer["country"],
            machine_model=machine.model,
            machine_series=machine.series,
            machine_variant=machine.variant,
            quantity=quantity,
            forming_area_mm=machine.forming_area_raw or (0, 0),
            line_items=line_items,
            base_price_inr=total_base,
            options_total_inr=options_total,
            subtotal_inr=subtotal,
            gst_inr=gst,
            total_inr=total,
            total_usd=total_usd,
            key_features=key_features,
            technical_specs={
                "heater_power_kw": machine.heater_power_kw,
                "vacuum_capacity": machine.vacuum_pump_capacity,
                "max_tool_height": machine.max_tool_height_mm,
            },
        )
        
        return quote
    
    def generate_pdf(self, quote: SalesQuote) -> str:
        """
        Generate PDF document for a quote.
        
        Returns:
            Path to generated PDF file
        """
        if not PDF_AVAILABLE:
            raise ImportError("fpdf2 is required. Install with: pip install fpdf2")
        
        pdf = QuotePDF()
        pdf.alias_nb_pages()
        
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "QUOTATION", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        
        pdf.section_title("QUOTE DETAILS")
        pdf.key_value("Quote No:", quote.quote_id)
        pdf.key_value("Date:", quote.quote_date)
        pdf.key_value("Valid Until:", quote.valid_until)
        pdf.key_value("Prepared by:", "Rushabh Doshi, Director - Sales & Marketing")
        
        pdf.section_title("CUSTOMER INFORMATION")
        pdf.key_value("Customer:", quote.customer_name)
        if quote.company_name:
            pdf.key_value("Company:", quote.company_name)
        if quote.customer_email:
            pdf.key_value("Email:", quote.customer_email)
        if quote.customer_phone:
            pdf.key_value("Phone:", quote.customer_phone)
        pdf.key_value("Country:", quote.country)
        
        pdf.section_title(f"{quote.machine_model} - MACHINE OVERVIEW")
        pdf.set_font("Helvetica", "", 10)
        w, h = quote.forming_area_mm
        overview = (
            f"The {quote.machine_model} is a heavy-gauge, single-station cut-sheet thermoforming "
            f"machine featuring a robust closed-chamber design. With a {w} x {h} mm forming area, "
            f"it delivers precision forming for thermoplastic sheets, ideal for automotive, "
            f"aerospace, industrial, and commercial applications."
        )
        pdf.multi_cell(0, 5, overview)
        pdf.ln(3)
        
        pdf.section_title("KEY FEATURES")
        for feature in quote.key_features:
            pdf.bullet_point(feature)
        
        pdf.section_title("TECHNICAL SPECIFICATIONS")
        pdf.key_value("Machine Model:", quote.machine_model)
        pdf.key_value("Forming Area:", f"{w} x {h} mm")
        if quote.technical_specs.get("max_tool_height"):
            pdf.key_value("Max Tool Height:", f"{quote.technical_specs['max_tool_height']} mm")
        if quote.technical_specs.get("heater_power_kw"):
            pdf.key_value("Heater Power:", f"{quote.technical_specs['heater_power_kw']} kW")
        if quote.technical_specs.get("vacuum_capacity"):
            pdf.key_value("Vacuum Capacity:", quote.technical_specs["vacuum_capacity"])
        
        pdf.section_title("PRICING")
        pdf.price_table(
            quote.line_items,
            quote.subtotal_inr,
            quote.gst_inr,
            quote.total_inr,
            quote.total_usd
        )
        pdf.ln(3)
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 5, "Price is Ex-Works Machinecraft plant, Umargam, Gujarat, India.", 
                 new_x="LMARGIN", new_y="NEXT")
        
        pdf.section_title("TERMS & CONDITIONS")
        pdf.key_value("Lead Time:", quote.delivery_time)
        pdf.key_value("Payment:", quote.payment_terms)
        pdf.key_value("Warranty:", quote.warranty)
        pdf.key_value("Validity:", "30 days from date of issue")
        pdf.ln(3)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 4, 
            "DELIVERY TERMS: Packing, freight, insurance, and on-site installation costs "
            "are not included unless explicitly stated."
        )
        
        pdf.section_title("CONTACT INFORMATION")
        pdf.key_value("Sales Director:", "Rushabh Doshi")
        pdf.key_value("Phone:", "+91-22-40140000")
        pdf.key_value("Email:", "sales@machinecraft.org")
        pdf.key_value("Website:", "www.machinecraft.org")
        
        pdf.ln(10)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, "For acceptance, please sign below and return a copy:", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        pdf.cell(100, 5, "Authorized Signatory: _______________________")
        pdf.cell(0, 5, "Date: ______________", new_x="LMARGIN", new_y="NEXT")
        
        filename = f"Quote_{quote.quote_id}_{quote.machine_model}.pdf"
        filepath = self.EXPORTS_DIR / filename
        pdf.output(str(filepath))
        
        quote.pdf_path = str(filepath)
        
        return str(filepath)
    
    def track_quote(self, quote: SalesQuote) -> bool:
        """Track quote in CRM pipeline."""
        if CRM_AVAILABLE:
            try:
                tracker = get_tracker()
                tracker.record_quote_sent(
                    quote_id=quote.quote_id,
                    customer_email=quote.customer_email or quote.customer_id,
                    product=quote.machine_model,
                    amount=quote.total_usd,
                    currency="USD",
                    customer_name=quote.customer_name,
                    company=quote.company_name,
                    notes=f"PDF generated at {quote.pdf_path}" if quote.pdf_path else "",
                )
                return True
            except Exception as e:
                print(f"[SalesQuoteGenerator] Failed to track quote: {e}")
        return False


def generate_quote(
    customer_id: str,
    machine_id: str,
    quantity: int = 1,
    options: Dict[str, Any] = None,
    generate_pdf: bool = True,
    track_in_crm: bool = True,
) -> str:
    """
    High-level function to generate a complete quote with PDF.
    
    Args:
        customer_id: Unified identity contact_id
        machine_id: Machine model (e.g., "PF1-C-2015")
        quantity: Number of machines
        options: Dict of additional options (spare_parts_kit, installation, training)
        generate_pdf: Whether to generate PDF file
        track_in_crm: Whether to track in CRM pipeline
    
    Returns:
        Path to PDF file (if generated) or quote_id
    
    Raises:
        ValueError: If machine not found in database
    """
    generator = SalesQuoteGenerator()
    quote = generator.create_quote(customer_id, machine_id, quantity, options)
    
    if generate_pdf:
        pdf_path = generator.generate_pdf(quote)
        if track_in_crm:
            generator.track_quote(quote)

        # Holistic: record quote generation as muscle action
        try:
            from openclaw.agents.ira.src.holistic.musculoskeletal_system import get_musculoskeletal_system
            get_musculoskeletal_system().record_action(
                "quote_generated",
                context={"customer_id": customer_id, "machine_id": machine_id, "quantity": quantity},
            )
        except Exception:
            pass

        return pdf_path
    
    if track_in_crm:
        generator.track_quote(quote)
    
    return quote.quote_id


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Sales Quote Generator")
    parser.add_argument("--machine", required=True, help="Machine model (e.g., PF1-C-2015)")
    parser.add_argument("--customer", default="test_customer", help="Customer ID")
    parser.add_argument("--quantity", type=int, default=1, help="Quantity")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF generation")
    args = parser.parse_args()
    
    try:
        result = generate_quote(
            customer_id=args.customer,
            machine_id=args.machine,
            quantity=args.quantity,
            generate_pdf=not args.no_pdf,
        )
        print(f"\n{'Quote ID' if args.no_pdf else 'PDF generated'}: {result}")
    except ValueError as e:
        print(f"Error: {e}")
    except ImportError as e:
        print(f"Missing dependency: {e}")
