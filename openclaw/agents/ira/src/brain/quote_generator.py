#!/usr/bin/env python3
"""
QUOTE GENERATOR - Automated Quote Generation for Machinecraft
==============================================================

Automatically generates professional quotes matching Machinecraft's 
actual quotation format as found in data/imports/Quotes/.

Format learned from:
- PF1-C-3520 _ Machinecraft PF1 Quotation.pdf
- PF1-X-3020- Machinecraft - Offer Jan 2026.pdf
- Quote_PF1-C-3020_Paracoat.pdf

Quote Structure:
1. Header (Quote No, Date, Model, Validity, Prepared By)
2. Machine Overview (introductory paragraph)
3. Key Features (bullet points)
4. Technical Specifications (table format)
5. Target Application (if known)
6. Pricing (base machine + optional extras)
7. Terms & Conditions (lead time, payment, shipping, warranty, validity)
8. Contact Information

Usage:
    from quote_generator import QuoteGenerator, generate_quote
    
    quote = generate_quote(
        forming_size=(2000, 1500),
        variant="C",
        customer_name="John Doe",
        company_name="Acme Corp"
    )
"""

import os
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Import dependencies
try:
    from .inquiry_qualifier import InquiryQualifier, QualificationProfile, QUALIFICATION_QUESTIONS
except ImportError:
    from inquiry_qualifier import InquiryQualifier, QualificationProfile, QUALIFICATION_QUESTIONS

try:
    from .pricing_estimator import PricingEstimator, PriceEstimate, QuoteRequest, OPTION_PRICES_INR
except ImportError:
    from pricing_estimator import PricingEstimator, PriceEstimate, QuoteRequest, OPTION_PRICES_INR

try:
    from .machine_database import MACHINE_SPECS, get_machine, find_machines_by_size
except ImportError:
    from machine_database import MACHINE_SPECS, get_machine, find_machines_by_size

try:
    from .detailed_specs_generator import generate_detailed_specs
    SPECS_AVAILABLE = True
except ImportError:
    SPECS_AVAILABLE = False
    def generate_detailed_specs(model): return None

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent


@dataclass
class QuoteLineItem:
    """Single line item in a quote."""
    description: str
    quantity: int = 1
    unit_price_inr: int = 0
    total_price_inr: int = 0
    notes: str = ""


@dataclass
class GeneratedQuote:
    """Complete generated quote."""
    # Quote metadata (required)
    quote_id: str
    quote_date: str
    valid_until: str
    
    # Customer info (required first, optional second)
    customer_name: str
    company_name: str
    
    # Machine recommendation (required)
    recommended_model: str
    machine_series: str
    machine_variant: str
    
    # All optional fields below
    customer_email: str = ""
    country: str = "India"
    forming_area_mm: Tuple[int, int] = (0, 0)
    forming_area_sqm: float = 0
    
    # Requirements captured
    requirements: Dict[str, Any] = field(default_factory=dict)
    
    # Pricing
    base_price_inr: int = 0
    options_total_inr: int = 0
    subtotal_inr: int = 0
    gst_inr: int = 0  # 18% GST for India
    total_inr: int = 0
    total_usd: int = 0
    
    # Line items
    line_items: List[QuoteLineItem] = field(default_factory=list)
    
    # Additional info
    delivery_time: str = "12-16 weeks"
    payment_terms: str = "30% advance, 60% before dispatch, 10% after installation"
    warranty: str = "12 months from installation or 18 months from dispatch"
    
    # Technical specs
    technical_specs: Dict[str, Any] = field(default_factory=dict)
    key_features: List[str] = field(default_factory=list)
    
    # Status
    confidence: float = 0.9
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['forming_area_mm'] = list(self.forming_area_mm)
        return d


# Machine recommendation logic
MATERIAL_REQUIREMENTS = {
    "HDPE": {"min_thickness": 3, "max_thickness": 12, "recommended_heater": "ceramic"},
    "ABS": {"min_thickness": 1.5, "max_thickness": 8, "recommended_heater": "quartz"},
    "PP": {"min_thickness": 1, "max_thickness": 6, "recommended_heater": "ceramic"},
    "PS": {"min_thickness": 0.5, "max_thickness": 4, "recommended_heater": "quartz"},
    "PVC": {"min_thickness": 0.3, "max_thickness": 3, "recommended_heater": "ceramic"},
    "PMMA": {"min_thickness": 2, "max_thickness": 10, "recommended_heater": "ceramic"},
    "PC": {"min_thickness": 1, "max_thickness": 8, "recommended_heater": "quartz"},
    "PET": {"min_thickness": 0.3, "max_thickness": 2, "recommended_heater": "quartz"},
    "TPO": {"min_thickness": 2, "max_thickness": 6, "recommended_heater": "ceramic"},
}

APPLICATION_RECOMMENDATIONS = {
    "automotive": {
        "series": "PF1-X",
        "features": ["Servo drives for precision", "Universal frames for flexibility"],
        "options": {"frame_type": "universal", "clamping": "auto_align"},
    },
    "packaging": {
        "series": "PF1-C",
        "features": ["High cycle rate", "Cost-effective"],
        "options": {"heater_type": "quartz"},
    },
    "signage": {
        "series": "PF1-C",
        "features": ["Large format capability", "PMMA compatibility"],
        "options": {"frame_type": "fixed"},
    },
    "medical": {
        "series": "PF1-X",
        "features": ["Precision forming", "Repeatability"],
        "options": {"controller": "heatronik"},
    },
}


class QuoteGenerator:
    """
    Generates professional quotes from customer requirements.
    
    Combines qualification data with pricing to produce
    complete, professional quotes.
    """
    
    def __init__(self):
        self.qualifier = InquiryQualifier()
        self.estimator = PricingEstimator()
        self._quote_counter = self._load_quote_counter()
    
    def _load_quote_counter(self) -> int:
        """Load or initialize quote counter."""
        counter_file = PROJECT_ROOT / "data" / "quote_counter.txt"
        if counter_file.exists():
            try:
                return int(counter_file.read_text().strip())
            except (ValueError, IOError, OSError):
                pass
        return 1000
    
    def _save_quote_counter(self, counter: int):
        """Save quote counter."""
        counter_file = PROJECT_ROOT / "data" / "quote_counter.txt"
        counter_file.parent.mkdir(parents=True, exist_ok=True)
        counter_file.write_text(str(counter))
    
    def _generate_quote_id(self) -> str:
        """
        Generate unique quote ID matching Machinecraft format.
        
        Format: MT20260227 (MT + YYYYMMDD)
        """
        self._quote_counter += 1
        self._save_quote_counter(self._quote_counter)
        date_str = datetime.now().strftime("%Y%m%d")
        return f"MT{date_str}{self._quote_counter % 100:02d}"
    
    def recommend_machine(
        self,
        forming_size: Tuple[int, int],
        materials: List[str] = None,
        automation: str = "manual",
        production_volume: str = "medium",
        application: str = "",
    ) -> Tuple[str, str, Dict[str, str]]:
        """
        Recommend the best machine based on requirements.
        
        Returns:
            Tuple of (model_name, variant, recommended_options)
        """
        width, height = forming_size
        materials = materials or ["ABS"]
        
        # Determine variant based on automation and volume
        if automation == "automatic" or production_volume == "high":
            variant = "X"
        else:
            variant = "C"
        
        # Check application-specific recommendations
        if application.lower() in APPLICATION_RECOMMENDATIONS:
            app_rec = APPLICATION_RECOMMENDATIONS[application.lower()]
            if "X" in app_rec["series"]:
                variant = "X"
            recommended_options = app_rec.get("options", {})
        else:
            recommended_options = {}
        
        # Material-based heater recommendation
        primary_material = materials[0].upper() if materials else "ABS"
        if primary_material in MATERIAL_REQUIREMENTS:
            mat_req = MATERIAL_REQUIREMENTS[primary_material]
            if "recommended_heater" not in recommended_options:
                recommended_options["heater_type"] = mat_req["recommended_heater"]
        
        # Format model name
        w_cm = width // 10
        h_cm = height // 10
        w_str = str(w_cm // 10) if w_cm >= 100 else str(w_cm)
        h_str = str(h_cm // 10) if h_cm >= 100 else str(h_cm)
        model_name = f"PF1-{variant}-{w_str}{h_str}"
        
        return model_name, variant, recommended_options
    
    def generate_from_profile(
        self,
        profile: QualificationProfile,
        customer_name: str = "",
        company_name: str = "",
        customer_email: str = "",
    ) -> GeneratedQuote:
        """
        Generate a quote from a qualified inquiry profile.
        
        Args:
            profile: QualificationProfile from InquiryQualifier
            customer_name: Override customer name
            company_name: Override company name
            customer_email: Customer email
        
        Returns:
            GeneratedQuote object
        """
        # Extract requirements from profile
        if not profile.max_forming_area:
            raise ValueError("Profile must have forming area specified")
        
        forming_size = profile.max_forming_area
        materials = profile.materials or ["ABS"]
        automation = profile.sheet_loading or "manual"
        volume = profile.production_volume or "medium"
        application = profile.application or ""
        
        # Get machine recommendation
        model, variant, rec_options = self.recommend_machine(
            forming_size=forming_size,
            materials=materials,
            automation=automation,
            production_volume=volume,
            application=application,
        )
        
        # Build options dict
        options = {
            "heater_type": profile.heater_type or rec_options.get("heater_type", "ceramic"),
            "frame_type": rec_options.get("frame_type", "fixed"),
            "loading": "robotic" if automation == "automatic" else "manual",
        }
        options.update(rec_options)
        
        # Get price estimate
        estimate = self.estimator.estimate_price(
            forming_area=forming_size,
            variant=variant,
            options=options,
            country="India",  # Default, can be overridden
        )
        
        # Build line items
        line_items = [
            QuoteLineItem(
                description=f"{model} Thermoforming Machine",
                quantity=1,
                unit_price_inr=estimate.base_price_inr,
                total_price_inr=estimate.base_price_inr,
            )
        ]
        
        # Add option line items
        for opt_name, opt_price in estimate.options_breakdown.items():
            line_items.append(QuoteLineItem(
                description=opt_name,
                quantity=1,
                unit_price_inr=opt_price,
                total_price_inr=opt_price,
            ))
        
        # Calculate totals
        subtotal = estimate.total_price_inr
        gst = int(subtotal * 0.18)  # 18% GST
        total = subtotal + gst
        
        # Get technical specs
        tech_specs = {}
        if SPECS_AVAILABLE:
            specs = generate_detailed_specs(model)
            if specs:
                tech_specs = specs
        
        # Build comprehensive key features list (matching Machinecraft format)
        is_servo = variant in ["X", "S"]
        key_features = [
            f"Closed-Chamber Zero-Sag Design",
            f"{forming_size[0]} × {forming_size[1]} mm Forming Area",
            "Sandwich Heating Oven (Top & Bottom IR)",
            "PLC Control with 7\" Touchscreen HMI",
        ]
        
        if is_servo:
            key_features.extend([
                "All-Servo Drive System (precision control)",
                "Universal Motorized Aperture Setting",
                "Programmable speed/acceleration profiles",
            ])
        else:
            key_features.extend([
                "Pneumatic Forming System (rack & pinion)",
                "Fixed Clamp Frames (1 frame included)",
            ])
        
        if automation == "automatic":
            key_features.append("Automatic Sheet Loading System")
        
        heater = options.get("heater_type", "ceramic")
        if heater == "quartz":
            key_features.append("IR Quartz Heaters (25% energy saving)")
        elif heater == "halogen":
            key_features.append("IR Halogen Heaters (50% energy saving)")
        else:
            key_features.append("IR Ceramic Heaters (rugged, wide material acceptance)")
        
        key_features.append("Pre-blow / Sag Control with Light Sensors")
        
        # Generate quote
        quote = GeneratedQuote(
            quote_id=self._generate_quote_id(),
            quote_date=datetime.now().strftime("%Y-%m-%d"),
            valid_until=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            customer_name=customer_name or profile.customer_name or "Valued Customer",
            company_name=company_name or profile.company_name or "",
            recommended_model=model,
            machine_series="PF1",
            machine_variant=variant,
            customer_email=customer_email or profile.customer_email or "",
            forming_area_mm=forming_size,
            forming_area_sqm=estimate.forming_area_sqm,
            requirements={
                "materials": materials,
                "automation": automation,
                "volume": volume,
                "application": application,
                "max_depth": profile.max_forming_depth,
            },
            base_price_inr=estimate.base_price_inr,
            options_total_inr=estimate.options_price_inr,
            subtotal_inr=subtotal,
            gst_inr=gst,
            total_inr=total,
            total_usd=total // 83,  # Approx USD
            line_items=line_items,
            technical_specs=tech_specs,
            key_features=key_features,
            confidence=estimate.confidence,
            notes=estimate.notes,
        )
        
        return quote
    
    def generate_quick_quote(
        self,
        forming_size: Tuple[int, int],
        variant: str = "C",
        materials: List[str] = None,
        options: Dict[str, str] = None,
        customer_name: str = "",
        company_name: str = "",
        country: str = "India",
    ) -> GeneratedQuote:
        """
        Generate a quick quote without full qualification.
        
        Args:
            forming_size: (width_mm, height_mm)
            variant: C, X, S, etc.
            materials: List of materials
            options: Dict of options
            customer_name: Customer name
            company_name: Company name
            country: Country for pricing
        
        Returns:
            GeneratedQuote object
        """
        materials = materials or ["ABS"]
        options = options or {}
        
        # Get price estimate
        estimate = self.estimator.estimate_price(
            forming_area=forming_size,
            variant=variant,
            options=options,
            country=country,
        )
        
        # Build model name
        w_cm = forming_size[0] // 10
        h_cm = forming_size[1] // 10
        w_str = str(w_cm // 10) if w_cm >= 100 else str(w_cm)
        h_str = str(h_cm // 10) if h_cm >= 100 else str(h_cm)
        model = f"PF1-{variant}-{w_str}{h_str}"
        
        # Build line items
        line_items = [
            QuoteLineItem(
                description=f"{model} Thermoforming Machine",
                quantity=1,
                unit_price_inr=estimate.base_price_inr,
                total_price_inr=estimate.base_price_inr,
            )
        ]
        
        for opt_name, opt_price in estimate.options_breakdown.items():
            line_items.append(QuoteLineItem(
                description=opt_name,
                quantity=1,
                unit_price_inr=opt_price,
                total_price_inr=opt_price,
            ))
        
        # Calculate totals
        subtotal = estimate.total_price_inr
        is_export = country.lower() != "india"
        gst = 0 if is_export else int(subtotal * 0.18)
        total = subtotal + gst
        
        # Key features (comprehensive, matching Machinecraft format)
        is_servo = variant in ["X", "S"]
        key_features = [
            "Closed-Chamber Zero-Sag Design",
            f"{forming_size[0]} × {forming_size[1]} mm Forming Area",
            "Sandwich Heating Oven (Top & Bottom)",
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
                "Fixed Clamp Frames",
            ])
        
        key_features.append("Pre-blow / Sag Control")
        
        quote = GeneratedQuote(
            quote_id=self._generate_quote_id(),
            quote_date=datetime.now().strftime("%Y-%m-%d"),
            valid_until=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            customer_name=customer_name or "Valued Customer",
            company_name=company_name,
            recommended_model=model,
            machine_series="PF1",
            machine_variant=variant,
            country=country,
            forming_area_mm=forming_size,
            forming_area_sqm=estimate.forming_area_sqm,
            requirements={"materials": materials},
            base_price_inr=estimate.base_price_inr,
            options_total_inr=estimate.options_price_inr,
            subtotal_inr=subtotal,
            gst_inr=gst,
            total_inr=total,
            total_usd=total // 83,
            line_items=line_items,
            key_features=key_features,
            confidence=estimate.confidence,
            notes=estimate.notes,
        )
        
        return quote
    
    def format_quote_text(self, quote: GeneratedQuote, style: str = "detailed") -> str:
        """
        Format quote as text for email/Telegram.
        
        Args:
            quote: GeneratedQuote object
            style: "detailed", "summary", or "email"
        
        Returns:
            Formatted quote text
        """
        if style == "summary":
            return self._format_summary(quote)
        elif style == "email":
            return self._format_email(quote)
        else:
            return self._format_detailed(quote)
    
    def _format_detailed(self, quote: GeneratedQuote) -> str:
        """
        Format detailed quote matching Machinecraft's actual quotation format.
        
        Based on real quotes from data/imports/Quotes/
        """
        w, h = quote.forming_area_mm
        is_servo = quote.machine_variant in ["X", "S"]
        
        # Format price in Indian lakh notation (₹85,00,000)
        def format_inr_lakhs(amount: int) -> str:
            if amount >= 10000000:
                crores = amount / 10000000
                return f"₹{crores:.2f} Cr"
            elif amount >= 100000:
                lakhs = amount / 100000
                return f"₹{lakhs:.0f} Lakhs"
            else:
                return f"₹{amount:,}"
        
        lines = [
            "MACHINECRAFT TECHNOLOGIES",
            "Plot 92, Dehri Road, Umbergaon, Dist. Valsad, Gujarat-396170, India",
            "Tel: +91-22-40140000 | Email: sales@machinecraft.org | Web: www.machinecraft.org",
            "",
            "═" * 70,
            "QUOTATION",
            "═" * 70,
            "",
            f"Quote No:     {quote.quote_id}",
            f"Date:         {quote.quote_date}",
            f"Model:        {quote.recommended_model}",
            f"Validity:     30 days from date of issue",
            f"Prepared by:  Rushabh Doshi, Director — Sales & Marketing",
            "",
        ]
        
        # Customer section (if provided)
        if quote.customer_name and quote.customer_name != "Valued Customer":
            lines.extend([
                "─" * 70,
                "PREPARED FOR",
                "─" * 70,
                f"Client Name:  {quote.customer_name}",
            ])
            if quote.company_name:
                lines.append(f"Company:      {quote.company_name}")
            if quote.customer_email:
                lines.append(f"Email:        {quote.customer_email}")
            lines.append("")
        
        # Machine Overview
        lines.extend([
            "═" * 70,
            f"{quote.recommended_model} — Heavy-Gauge Single-Station Thermoforming Machine",
            "═" * 70,
            "",
            "MACHINE OVERVIEW",
            "",
            f"The {quote.recommended_model} is a heavy-gauge, single-station cut-sheet thermoforming",
            "machine designed for versatility and high performance. All models in the PF1 Series",
            "feature a robust closed-chamber design that prevents sheet sag by allowing pre-blow",
            "air pressure control, ensuring superior forming quality on thick materials.",
            "",
            f"With a generous {w} x {h} mm forming area, the {quote.recommended_model} delivers",
            "precision forming for a variety of thermoplastic sheets (typically 2–12 mm thick),",
            "making it ideal for automotive, aerospace, industrial, and commercial applications",
            "that demand excellent detail and consistency.",
            "",
        ])
        
        # Key Features
        lines.extend([
            "KEY FEATURES",
            "",
            "• Closed-Chamber Zero-Sag Design — Air-tight chamber below the sheet line with",
            "  pulsated air maintains sheet level during heating, preventing sag",
            "",
            f"• {w} x {h} mm Forming Area — Generous size for large-format components",
            "",
            "• Sandwich Heating Oven (Top & Bottom) — IR heating elements with individual",
            "  SSR and digital PID control via HMI for precise, even heating",
            "",
        ])
        
        if is_servo:
            lines.extend([
                "• All-Servo Drive System — Servo motors for forming platen, heater ovens,",
                "  clamp frames, and plug assist with programmable speed/acceleration profiles",
                "",
                "• Universal Motorized Aperture Setting — Motorized window plate adjustment",
                "  in both axes using touchscreen settings (no manual adjustment needed)",
                "",
            ])
        else:
            lines.extend([
                "• Pneumatic Forming System — Forming platen driven by cylinders with rack &",
                "  pinion mechanism; plug assist with manual height adjustment",
                "",
            ])
        
        lines.extend([
            "• Rugged Construction & Intelligent Control — Heavy-duty steel frame with",
            "  precision motion components; modern PLC control system with 7\" HMI touchscreen",
            "",
        ])
        
        # Technical Specifications
        lines.extend([
            "─" * 70,
            "TECHNICAL SPECIFICATIONS",
            "─" * 70,
            "",
            f"{'Specification':<30} {quote.recommended_model}",
            "─" * 70,
            f"{'Machine Model':<30} {quote.recommended_model}",
            f"{'Forming Area (Max)':<30} {w} x {h} mm (L x W)",
            f"{'Max Stroke Z Direction':<30} {quote.requirements.get('max_depth', 600)} mm",
            f"{'Sheet Thickness Range':<30} Typically 2–12 mm (material-dependent)",
            "",
        ])
        
        if is_servo:
            lines.extend([
                f"{'Clamp Frame System':<30} Universal Motorized Aperture Setting",
                f"{'Sheet Loading/Unloading':<30} Automatic Sheet Loading System",
                f"{'Forming Platen Drive':<30} Servo Motor Driven",
                f"{'Heater Oven Drive':<30} Servo Motor Driven",
                f"{'Clamp Frame Drive':<30} Servo Motor Driven",
                f"{'Plug Assist Drive':<30} Servo Motor Driven",
            ])
        else:
            lines.extend([
                f"{'Clamp Frame System':<30} Fixed Welded Frames (1 frame included)",
                f"{'Sheet Loading/Unloading':<30} Manual Loading by Operator",
                f"{'Forming Platen Drive':<30} Pneumatic (4 cylinders + rack & pinion)",
                f"{'Heater Oven Drive':<30} Pneumatic (high-temp cylinders)",
                f"{'Clamp Frame Drive':<30} Pneumatic (2 cylinders + rack & pinion)",
                f"{'Plug Assist Drive':<30} Pneumatic (manual height adjustment)",
            ])
        
        heater_type = quote.requirements.get("heater_type", "IR Ceramic")
        heater_power = int(quote.forming_area_sqm * 40)
        vacuum_capacity = max(100, int(quote.forming_area_sqm * 50))
        total_power = heater_power + (45 if is_servo else 20)
        
        lines.extend([
            "",
            f"{'Heating Oven Configuration':<30} Sandwich — Top & Bottom, {heater_type}",
            f"{'Heater Power (approx)':<30} {heater_power} kW",
            f"{'Vacuum System':<30} ~{vacuum_capacity} m³/hr capacity",
            f"{'Compressed Air Requirement':<30} ~6 bar (100 psi)",
            f"{'Cooling System':<30} Centrifugal Fans",
            f"{'Control System & HMI':<30} PLC + 7\" color touchscreen HMI",
            f"{'Pre-blow / Sag Control':<30} Yes (closed chamber with light sensors)",
            f"{'Total Connected Load':<30} ~{total_power} kW",
            "",
        ])
        
        # Pricing Section
        lines.extend([
            "═" * 70,
            "PRICING",
            "═" * 70,
            "",
            f"{'Item':<45} {'Price (INR)':<20}",
            "─" * 70,
        ])
        
        for item in quote.line_items:
            price_str = format_inr_lakhs(item.total_price_inr)
            lines.append(f"{item.description:<45} {price_str:<20}")
        
        lines.extend([
            "─" * 70,
            f"{'Subtotal':<45} {format_inr_lakhs(quote.subtotal_inr):<20}",
        ])
        
        if quote.gst_inr > 0:
            lines.append(f"{'GST (18%)':<45} {format_inr_lakhs(quote.gst_inr):<20}")
            lines.append(f"{'TOTAL':<45} {format_inr_lakhs(quote.total_inr):<20}")
        else:
            lines.append(f"{'TOTAL (Ex-Works)':<45} {format_inr_lakhs(quote.subtotal_inr):<20}")
        
        lines.extend([
            "",
            f"Approximate USD: ${quote.total_usd:,}",
            "Price is Ex-Works Machinecraft plant, Umargam, Gujarat, India.",
            "",
        ])
        
        # Optional Extras
        lines.extend([
            "OPTIONAL EXTRAS",
            "",
            f"{'Item':<35} {'Description':<25} {'Price':<15}",
            "─" * 70,
            f"{'Additional Clamp Frames':<35} {'Custom-sized frames':<25} {'On Request':<15}",
            f"{'Installation & Commissioning':<35} {'At customer site':<25} {'On Request':<15}",
            f"{'Operator Training':<35} {'At customer site':<25} {'On Request':<15}",
        ])
        
        if not is_servo:
            lines.append(f"{'Automatic Sheet Loading':<35} {'Powered loading system':<25} {'On Request':<15}")
            lines.append(f"{'Universal Frame System':<35} {'Motorized adjustment':<25} {'On Request':<15}")
        
        lines.extend([
            f"{'Enhanced Vacuum System':<35} {'Higher capacity pump':<25} {'On Request':<15}",
            f"{'IoT / Remote Monitoring':<35} {'VPN-based support module':<25} {'On Request':<15}",
            "",
        ])
        
        # Terms & Conditions
        lines.extend([
            "═" * 70,
            "TERMS & CONDITIONS",
            "═" * 70,
            "",
            f"{'Lead Time':<20} {quote.delivery_time} from PO & advance payment",
            f"{'Payment Terms':<20} {quote.payment_terms}",
            f"{'Shipping':<20} EXW Machinecraft plant, Umargam, Gujarat, India",
            f"{'Warranty':<20} {quote.warranty}",
            f"{'Validity':<20} This quotation is valid for 30 days from date of issue",
            "",
            "DELIVERY TERMS: Packing, freight, insurance, and on-site installation costs",
            "are not included unless explicitly stated.",
            "",
            "INSTALLATION & TRAINING: Machinecraft will provide on-site commissioning and",
            "basic training. Travel and lodging costs for technicians will be extra.",
            "",
            "FAT: Machinecraft will do a dry run test and also run the machine on demo",
            "tool with 1x material like ABS or PS in 1x thickness.",
            "",
        ])
        
        # Notes (if any)
        if quote.notes:
            lines.extend(["NOTES:", ""])
            for note in quote.notes:
                lines.append(f"• {note}")
            lines.append("")
        
        # Contact Information
        lines.extend([
            "═" * 70,
            "CONTACT INFORMATION",
            "═" * 70,
            "",
            "Rushabh Doshi          Director — Sales & Marketing",
            "Sales Team             +91-22-40140000",
            "Email                  sales@machinecraft.org",
            "Direct Email           rushabh@machinecraft.org",
            "Technical Support      support@machinecraft.org",
            "Website                www.machinecraft.org",
            "",
            "─" * 70,
            "For acceptance of this offer, please sign below and return a copy:",
            "",
            "Accepted by (Authorized Signatory): ____________________ Date: _____________",
            "",
            "Machinecraft Technologies — 505, Palm Springs, Link Road, Malad (W),",
            "Mumbai 400064, India.",
            "Factory: Plot 92, Umbergaon Station-Dehri Rd, Valsad, Gujarat 396170, India.",
            "Email: contact@machinecraft.org | Web: www.machinecraft.org",
            "",
            "© 2026 Machinecraft Technologies. All Rights Reserved.",
        ])
        
        return "\n".join(lines)
    
    def _format_summary(self, quote: GeneratedQuote) -> str:
        """Format brief summary for Telegram."""
        w, h = quote.forming_area_mm
        is_servo = quote.machine_variant in ["X", "S"]
        variant_desc = "All-Servo" if is_servo else "Pneumatic"
        
        # Format price in lakhs for readability
        def fmt_lakhs(amt: int) -> str:
            if amt >= 100000:
                return f"₹{amt/100000:.1f}L"
            return f"₹{amt:,}"
        
        lines = [
            f"📋 **Quote {quote.quote_id}**",
            "",
            f"🏭 **{quote.recommended_model}** ({variant_desc})",
            f"📐 Forming Area: {w} × {h} mm",
            "",
            "💰 **Pricing:**",
            f"   Base Machine: {fmt_lakhs(quote.base_price_inr)}",
        ]
        
        if quote.options_total_inr > 0:
            lines.append(f"   Options: +{fmt_lakhs(quote.options_total_inr)}")
        
        if quote.gst_inr > 0:
            lines.append(f"   GST (18%): +{fmt_lakhs(quote.gst_inr)}")
            lines.append(f"   **Total: {fmt_lakhs(quote.total_inr)}**")
        else:
            lines.append(f"   **Total (Ex-Works): {fmt_lakhs(quote.subtotal_inr)}**")
        
        lines.append(f"   _(${quote.total_usd:,} USD approx.)_")
        
        lines.extend([
            "",
            "📝 **Key Specs:**",
            f"   • Closed-chamber zero-sag design",
            f"   • Sandwich heating (top & bottom)",
        ])
        
        if is_servo:
            lines.append(f"   • All-servo drives with auto sheet loading")
        else:
            lines.append(f"   • Pneumatic drives, manual loading")
        
        lines.extend([
            "",
            f"⏱ Lead Time: {quote.delivery_time}",
            f"📅 Valid: 30 days",
            "",
            "_Price Ex-Works Umargam, Gujarat. GST & freight extra._",
        ])
        
        return "\n".join(lines)
    
    def _format_email(self, quote: GeneratedQuote) -> str:
        """Format for email - professional Machinecraft style."""
        w, h = quote.forming_area_mm
        is_servo = quote.machine_variant in ["X", "S"]
        
        def fmt_lakhs(amt: int) -> str:
            if amt >= 100000:
                return f"₹{amt/100000:.0f} Lakhs"
            return f"₹{amt:,}"
        
        lines = [
            f"Please find below our quotation for your thermoforming machine requirement.",
            "",
            f"**QUOTE REFERENCE: {quote.quote_id}**",
            "",
            f"**Machine Model:** {quote.recommended_model}",
            f"**Type:** {'All-Servo (PF1-X Series)' if is_servo else 'Pneumatic (PF1-C Series)'}",
            f"**Forming Area:** {w} × {h} mm ({quote.forming_area_sqm} sq.m)",
            "",
            "**MACHINE HIGHLIGHTS:**",
            "",
            "• Closed-chamber zero-sag design with pre-blow capability",
            "• Sandwich heating oven (top & bottom IR elements)",
            "• PLC control with 7\" touchscreen HMI",
        ]
        
        if is_servo:
            lines.extend([
                "• All-servo drives (forming platen, heaters, clamp frames, plug assist)",
                "• Universal motorized aperture setting (automatic format changeover)",
                "• Automatic sheet loading system",
            ])
        else:
            lines.extend([
                "• Pneumatic forming system with rack & pinion mechanism",
                "• Fixed clamp frames (1 frame included, extras available)",
                "• Manual sheet loading",
            ])
        
        lines.extend([
            "",
            "**PRICING:**",
            "",
            f"• Base Machine: {fmt_lakhs(quote.base_price_inr)}",
        ])
        
        if quote.options_total_inr > 0:
            lines.append(f"• Selected Options: {fmt_lakhs(quote.options_total_inr)}")
        
        if quote.gst_inr > 0:
            lines.extend([
                f"• GST (18%): {fmt_lakhs(quote.gst_inr)}",
                f"• **TOTAL: {fmt_lakhs(quote.total_inr)}** (approx. ${quote.total_usd:,} USD)",
            ])
        else:
            lines.append(f"• **TOTAL (Ex-Works): {fmt_lakhs(quote.subtotal_inr)}** (approx. ${quote.total_usd:,} USD)")
        
        lines.extend([
            "",
            "_Price is Ex-Works Machinecraft plant, Umargam, Gujarat._",
            "",
            "**TERMS:**",
            "",
            f"• Lead Time: {quote.delivery_time} from PO & advance",
            f"• Payment: {quote.payment_terms}",
            f"• Warranty: {quote.warranty}",
            "• Validity: 30 days from date of issue",
            "",
            "**NOT INCLUDED:** Packing, freight, insurance, installation & commissioning",
            "(available at additional cost).",
        ])
        
        if quote.notes:
            lines.extend(["", "**NOTES:**", ""])
            for note in quote.notes[:3]:
                lines.append(f"• {note}")
        
        lines.extend([
            "",
            "Please let me know if you have any questions or would like to discuss",
            "alternative configurations. I can prepare a detailed formal quotation",
            "document once we finalize the specifications.",
        ])
        
        return "\n".join(lines)


# Convenience functions
def generate_quote(
    forming_size: Tuple[int, int],
    variant: str = "C",
    materials: List[str] = None,
    automation: str = "manual",
    customer_name: str = "",
    company_name: str = "",
    country: str = "India",
) -> GeneratedQuote:
    """
    Quick quote generation.
    
    Args:
        forming_size: (width_mm, height_mm)
        variant: C, X, S
        materials: List of materials
        automation: "manual" or "automatic"
        customer_name: Customer name
        company_name: Company name
        country: Country for pricing
    
    Returns:
        GeneratedQuote object
    """
    generator = QuoteGenerator()
    
    options = {}
    if automation == "automatic":
        options["loading"] = "robotic"
        if variant == "C":
            variant = "X"  # Upgrade to servo for automation
    
    return generator.generate_quick_quote(
        forming_size=forming_size,
        variant=variant,
        materials=materials,
        options=options,
        customer_name=customer_name,
        company_name=company_name,
        country=country,
    )


def format_quote(quote: GeneratedQuote, style: str = "summary") -> str:
    """Format a quote for display."""
    generator = QuoteGenerator()
    return generator.format_quote_text(quote, style)


def track_quote_sent(
    quote: GeneratedQuote,
    customer_email: str,
    thread_id: Optional[str] = None,
) -> bool:
    """
    Track a quote being sent to a customer in the CRM pipeline.
    
    Args:
        quote: The GeneratedQuote that was sent
        customer_email: Customer's email address
        thread_id: Email thread ID for linking
    
    Returns:
        True if tracking succeeded
    """
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "crm"))
        from quote_lifecycle import get_tracker
        
        tracker = get_tracker()
        tracker.record_quote_sent(
            quote_id=quote.quote_id,
            customer_email=customer_email,
            product=quote.recommended_model,
            amount=quote.total_usd or (quote.total_inr / 84),  # Convert to USD if needed
            currency="USD" if quote.total_usd else "INR",
            customer_name=quote.customer_name,
            company=quote.company_name,
            thread_id=thread_id,
            notes=f"Quote for {quote.recommended_model}, forming area {quote.forming_area_mm}",
        )
        return True
    except Exception as e:
        print(f"[quote_generator] Failed to track quote: {e}")
        return False


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Quote Generator CLI")
    parser.add_argument("--width", type=int, default=2000, help="Forming width (mm)")
    parser.add_argument("--height", type=int, default=1500, help="Forming height (mm)")
    parser.add_argument("--variant", default="C", help="Machine variant (C, X, S)")
    parser.add_argument("--customer", default="Test Customer", help="Customer name")
    parser.add_argument("--format", default="detailed", choices=["detailed", "summary", "email"])
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("QUOTE GENERATOR TEST")
    print("=" * 60)
    
    # Generate quote
    quote = generate_quote(
        forming_size=(args.width, args.height),
        variant=args.variant,
        customer_name=args.customer,
    )
    
    # Format and print
    print(format_quote(quote, args.format))
    
    print("\n" + "=" * 60)
    print(f"Quote ID: {quote.quote_id}")
    print(f"Confidence: {quote.confidence * 100:.0f}%")
    print("=" * 60)
