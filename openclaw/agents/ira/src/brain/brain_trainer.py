#!/usr/bin/env python3
"""
BRAIN TRAINER - Duolingo-Style Continuous Knowledge Quiz
========================================================

Endless quiz that:
1. Generates fresh questions on-the-fly from Ira's knowledge base
2. Never repeats questions within a session (tracks seen fingerprints)
3. Tracks weak categories via spaced repetition — asks more of what you get wrong
4. Logs all results to training_history.json
5. Writes a training_weights.json that generate_answer.py reads to reinforce weak areas

Commands:
    /train           → Show score or help
    /train start     → Begin (or resume) continuous quiz
    /train next      → Next question (alias: just /train after starting)
    /train answer <A/B/C/D> → Answer current question
    /train score     → Detailed score breakdown
    /train reset     → Reset all stats and start fresh
"""

import hashlib
import json
import logging
import os
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from config import PROJECT_ROOT
except ImportError:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
    if not (PROJECT_ROOT / "data" / "brain").exists():
        PROJECT_ROOT = Path.cwd()
        while PROJECT_ROOT != PROJECT_ROOT.parent:
            if (PROJECT_ROOT / "data" / "brain").exists():
                break
            PROJECT_ROOT = PROJECT_ROOT.parent

BRAIN_DIR = PROJECT_ROOT / "data" / "brain"
WORKSPACE_DIR = PROJECT_ROOT / "openclaw" / "agents" / "ira" / "workspace"
TRAIN_SESSION_PATH = WORKSPACE_DIR / "train_session.json"
TRAINING_HISTORY_PATH = BRAIN_DIR / "training_history.json"
TRAINING_WEIGHTS_PATH = BRAIN_DIR / "training_weights.json"
LESSONS_FROM_TRAINING_PATH = BRAIN_DIR / "lessons_from_training.json"
CUSTOMER_ORDERS_PATH = PROJECT_ROOT / "data" / "knowledge" / "customer_orders.json"

try:
    from machine_database import MACHINE_SPECS, MachineSpec
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from machine_database import MACHINE_SPECS, MachineSpec


# ===========================================================================
# HELPERS
# ===========================================================================

def _all_machines() -> List[MachineSpec]:
    return list(MACHINE_SPECS.values())

def _machines_with(attr: str):
    return [m for m in MACHINE_SPECS.values() if getattr(m, attr, None)]

def _load_customer_orders() -> List[Dict]:
    if not CUSTOMER_ORDERS_PATH.exists():
        return []
    try:
        data = json.loads(CUSTOMER_ORDERS_PATH.read_text())
        return data.get("orders", []) if isinstance(data, dict) else data
    except (json.JSONDecodeError, IOError):
        return []

def _fmt_price(price: int) -> str:
    if price >= 10_000_000:
        return f"\u20b9{price / 10_000_000:.1f} Cr"
    if price >= 100_000:
        return f"\u20b9{price / 100_000:.0f} Lakh"
    return f"\u20b9{price:,}"

def _pick_distractors(correct, pool, n=3):
    cands = [x for x in pool if x != correct]
    return random.sample(cands, min(n, len(cands)))

def _shuffle_opts(correct: str, distractors: List[str]) -> Tuple[List[str], str]:
    opts = [correct] + distractors[:3]
    random.shuffle(opts)
    return opts, chr(65 + opts.index(correct))

def _q_fingerprint(question_text: str) -> str:
    return hashlib.md5(question_text.encode()).hexdigest()[:12]


def _parse_answer(raw_text: str, question: Dict) -> Tuple[Optional[str], str]:
    """
    Parse a natural language answer into a letter choice + commentary.

    Handles:
      "A"                          -> ("A", "")
      "B but also consider..."     -> ("B", "but also consider...")
      "none"                       -> ("NONE", "")
      "Pneumatic (air cylinder)"   -> ("A", "")  (matched option text)
      "12-16 weeks and D..."       -> ("B", "and D...")  (fuzzy match)

    Returns (choice_letter_or_NONE, commentary_text).
    """
    raw = raw_text.strip()
    if not raw:
        return None, ""

    # Check for "none" / "none of the above" / "don't know"
    none_patterns = ["none", "none of the above", "don't know", "dont know",
                     "no idea", "not sure", "idk", "skip", "n/a"]
    if raw.lower().strip() in none_patterns:
        return "NONE", ""

    # Check if starts with a single letter A-D (with optional punctuation)
    letter_match = re.match(r'^([A-Da-d])\b[.):,]?\s*(.*)', raw, re.DOTALL)
    if letter_match:
        return letter_match.group(1).upper(), letter_match.group(2).strip()

    # Try to match option text (fuzzy: check if any option text appears in the answer)
    options = question.get("options", [])
    raw_lower = raw.lower()
    best_match = None
    best_len = 0
    for i, opt in enumerate(options):
        opt_lower = opt.lower()
        # Check if the option text (or a significant prefix) appears in the answer
        # Use first 30 chars of option as matching key
        match_key = opt_lower[:30]
        if match_key in raw_lower or raw_lower in opt_lower:
            if len(opt_lower) > best_len:
                best_len = len(opt_lower)
                best_match = chr(65 + i)

    if best_match:
        return best_match, raw

    # Check for keywords from each option
    for i, opt in enumerate(options):
        opt_words = set(re.findall(r'\b\w{4,}\b', opt.lower()))
        answer_words = set(re.findall(r'\b\w{4,}\b', raw_lower))
        overlap = opt_words & answer_words
        if len(overlap) >= 2 or (len(opt_words) <= 3 and len(overlap) >= 1):
            return chr(65 + i), raw

    return None, raw


def _save_lesson(question: Dict, commentary: str, answer_choice: str):
    """Save commentary from training as a lesson for Ira."""
    if not commentary or len(commentary) < 5:
        return

    lessons = []
    if LESSONS_FROM_TRAINING_PATH.exists():
        try:
            lessons = json.loads(LESSONS_FROM_TRAINING_PATH.read_text())
        except (json.JSONDecodeError, IOError):
            lessons = []

    lessons.append({
        "question": question.get("question", ""),
        "category": question.get("category", ""),
        "answer_given": answer_choice,
        "commentary": commentary,
        "timestamp": datetime.now().isoformat(),
    })

    # Keep last 200 lessons
    lessons = lessons[-200:]
    BRAIN_DIR.mkdir(parents=True, exist_ok=True)
    LESSONS_FROM_TRAINING_PATH.write_text(json.dumps(lessons, indent=2))


# ===========================================================================
# QUESTION GENERATORS — each returns {"question", "options", "answer", "category"}
# ===========================================================================

def _gen_price():
    ms = _machines_with("price_inr")
    if len(ms) < 4: return None
    m = random.choice(ms)
    c = _fmt_price(m.price_inr)
    d = _pick_distractors(c, list(set(_fmt_price(x.price_inr) for x in ms)))
    if len(d) < 3: return None
    opts, ans = _shuffle_opts(c, d)
    return {"question": f"What is the base price of the **{m.model}**?", "options": opts, "answer": ans, "category": "pricing"}

def _gen_forming_area():
    ms = _machines_with("forming_area_mm")
    if len(ms) < 4: return None
    m = random.choice(ms)
    c = m.forming_area_mm
    d = _pick_distractors(c, list(set(x.forming_area_mm for x in ms if x.forming_area_mm)))
    if len(d) < 3: return None
    opts, ans = _shuffle_opts(c, d)
    return {"question": f"What is the forming area of the **{m.model}**?", "options": opts, "answer": ans, "category": "specs"}

def _gen_series():
    ms = _all_machines()
    m = random.choice(ms)
    c = m.series
    pool = list(set(x.series for x in ms)) + ["ATF", "HFM"]
    d = _pick_distractors(c, pool)
    if len(d) < 3: return None
    opts, ans = _shuffle_opts(c, d[:3])
    return {"question": f"Which product series does **{m.model}** belong to?", "options": opts, "answer": ans, "category": "product_knowledge"}

def _gen_heater():
    ms = _machines_with("heater_type")
    if len(ms) < 4: return None
    m = random.choice(ms)
    c = m.heater_type
    pool = list(set(x.heater_type for x in ms if x.heater_type)) + ["Halogen", "Gas Catalytic", "Infrared Rod"]
    d = _pick_distractors(c, pool)
    if len(d) < 3: return None
    opts, ans = _shuffle_opts(c, d[:3])
    return {"question": f"What type of heater does the **{m.model}** use?", "options": opts, "answer": ans, "category": "specs"}

def _gen_application():
    ms = [m for m in _all_machines() if m.applications]
    if len(ms) < 4: return None
    m = random.choice(ms)
    app = random.choice(m.applications)
    c = m.model
    d = _pick_distractors(c, [x.model for x in ms])
    if len(d) < 3: return None
    opts, ans = _shuffle_opts(c, d[:3])
    return {"question": f"Which machine is best suited for **{app}**?", "options": opts, "answer": ans, "category": "applications"}

def _gen_thickness():
    ms = [m for m in _all_machines() if m.max_sheet_thickness_mm > 0]
    if len(ms) < 4: return None
    m = random.choice(ms)
    c = f"{m.max_sheet_thickness_mm} mm"
    pool = list(set(f"{x.max_sheet_thickness_mm} mm" for x in ms if x.max_sheet_thickness_mm > 0)) + ["0.5 mm", "15 mm"]
    d = _pick_distractors(c, pool)
    if len(d) < 3: return None
    opts, ans = _shuffle_opts(c, d[:3])
    return {"question": f"What is the max sheet thickness for the **{m.model}**?", "options": opts, "answer": ans, "category": "specs"}

def _gen_vacuum():
    ms = _machines_with("vacuum_pump_capacity")
    if len(ms) < 4: return None
    m = random.choice(ms)
    c = m.vacuum_pump_capacity
    pool = list(set(x.vacuum_pump_capacity for x in ms if x.vacuum_pump_capacity)) + ["80 m\u00b3/hr", "500 m\u00b3/hr"]
    d = _pick_distractors(c, pool)
    if len(d) < 3: return None
    opts, ans = _shuffle_opts(c, d[:3])
    return {"question": f"What is the vacuum pump capacity of the **{m.model}**?", "options": opts, "answer": ans, "category": "specs"}

def _gen_customer_order():
    orders = _load_customer_orders()
    if len(orders) < 4: return None
    o = random.choice(orders)
    qtype = random.choice(["machine", "country", "app"])
    if qtype == "machine":
        c = o["machine_model"]
        d = _pick_distractors(c, [x["machine_model"] for x in orders] + ["PF1-C-3020", "AM-5060"])
        if len(d) < 3: return None
        opts, ans = _shuffle_opts(c, d[:3])
        return {"question": f"Which machine did **{o['customer']}** order?", "options": opts, "answer": ans, "category": "customers"}
    elif qtype == "country":
        c = o["country"]
        d = _pick_distractors(c, list(set(x["country"] for x in orders)) + ["Japan", "France", "Brazil"])
        if len(d) < 3: return None
        opts, ans = _shuffle_opts(c, d[:3])
        return {"question": f"Which country is **{o['customer']}** based in?", "options": opts, "answer": ans, "category": "customers"}
    else:
        c = o.get("application", "General thermoforming")
        d = _pick_distractors(c, list(set(x.get("application","") for x in orders if x.get("application"))) + ["Food packaging", "Medical devices"])
        if len(d) < 3: return None
        opts, ans = _shuffle_opts(c, d[:3])
        return {"question": f"What application did **{o['customer']}** order their machine for?", "options": opts, "answer": ans, "category": "customers"}

# Static conceptual questions — shuffled options each time
_CONCEPT_BANK = [
    ("What does the **C** variant mean in PF1-C models?",
     "Pneumatic (air cylinder)", ["CNC controlled", "Compact size", "Ceramic heaters"], "product_knowledge"),
    ("What does the **X** variant mean in PF1-X models?",
     "All-servo drive", ["Extra large", "Export model", "Extended warranty"], "product_knowledge"),
    ("What is the key difference between PF1-C and PF1-X?",
     "PF1-C is pneumatic, PF1-X is all-servo", ["PF1-C is smaller, PF1-X is larger", "PF1-C is for packaging, PF1-X is for automotive", "PF1-C has no heaters, PF1-X has heaters"], "product_knowledge"),
    ("What is the PF2 series used for?",
     "Bathtubs, spa shells, shower trays only", ["Automotive interior parts", "Food packaging and blister packs", "General-purpose heavy-gauge forming"], "product_knowledge"),
    ("What is the maximum sheet thickness for the AM series?",
     "1.5 mm", ["3 mm", "5 mm", "8 mm"], "product_knowledge"),
    ("When should you recommend the IMG series?",
     "When customer needs grain retention or Class-A surface", ["When customer needs food packaging", "When customer needs bathtub forming", "When customer needs the cheapest option"], "product_knowledge"),
    ("What does PF1's closed chamber provide?",
     "Sag control and pre-blow capability", ["Faster cycle times only", "Lower energy consumption", "Automatic mold changes"], "product_knowledge"),
    ("Does the PF2 series have automation options?",
     "No \u2014 PF2 is basic with air cylinder drive only", ["Yes \u2014 full servo automation", "Yes \u2014 optional roll feeder", "Yes \u2014 robotic loading available"], "product_knowledge"),
    ("What disclaimer must EVERY price include?",
     '"Subject to configuration and current pricing"', ['"Prices may vary by region"', '"Final price on delivery"', '"All prices are estimates only"'], "rules"),
    ("What is the standard lead time for Machinecraft machines?",
     "12-16 weeks", ["4-6 weeks", "2-3 months", "6-8 months"], "rules"),
    ("Which of these is a FAKE model Ira must never recommend?",
     "IMG-2220", ["PF1-C-2015", "AM-5060", "UNO-1208"], "rules"),
    ("When should Ira give a specific recommendation instead of asking more questions?",
     "When material, thickness, size, and application are all known", ["Always \u2014 never ask questions", "Only when the customer explicitly asks", "Only after 3+ messages"], "rules"),
    ("What is the minimum word count for a machine proposal email?",
     "1200 words", ["500 words", "300 words", "2000 words"], "rules"),
    ("If a customer asks for 3mm thick material, which series should NOT be recommended?",
     "AM series (max 1.5mm)", ["PF1 series", "IMG series", "UNO series"], "rules"),
    ("If Ira doesn't have customer data, what should it do?",
     'Say "I don\'t have that data" and suggest checking CRM', ["Generate plausible-sounding company names", "Make up a list of likely customers", "Skip the question entirely"], "rules"),
    ("What material is the PF1 series designed for?",
     "Heavy gauge thick sheets (ABS, HDPE, PC, PMMA, 2-8mm)", ["Thin films and flexible packaging", "Only polycarbonate", "Paper and cardboard"], "product_knowledge"),
    ("What is PF2's forming mechanism?",
     "Material sags freely under gravity into negative cavity molds", ["Positive pressure forming with plug assist", "Vacuum forming with pre-blow", "Mechanical press forming"], "product_knowledge"),
    ("Which PLC brand is commonly used in Machinecraft machines?",
     "Siemens", ["Allen-Bradley", "Mitsubishi", "Omron"], "specs"),
    ("What type of heater elements does Machinecraft source from Ireland?",
     "IR Quartz Ceramicx", ["Halogen Philips", "Ceramic Elstein", "Gas catalytic"], "specs"),
]

def _gen_concept():
    q_text, correct, distractors, cat = random.choice(_CONCEPT_BANK)
    opts, ans = _shuffle_opts(correct, distractors[:3])
    return {"question": q_text, "options": opts, "answer": ans, "category": cat}


GENERATORS = [
    _gen_price, _gen_forming_area, _gen_series, _gen_heater,
    _gen_application, _gen_thickness, _gen_vacuum, _gen_customer_order,
    _gen_concept, _gen_concept,  # double-weight concepts
]


# ===========================================================================
# TRAINING HISTORY & WEIGHTS (the learning loop)
# ===========================================================================

class TrainingHistory:
    """Persists all quiz results and computes category weakness weights."""

    def __init__(self):
        self._data = self._load()

    def _load(self) -> Dict:
        if TRAINING_HISTORY_PATH.exists():
            try:
                return json.loads(TRAINING_HISTORY_PATH.read_text())
            except (json.JSONDecodeError, IOError):
                pass
        return {"sessions": 0, "total_correct": 0, "total_wrong": 0,
                "category_correct": {}, "category_wrong": {},
                "wrong_questions": [], "last_updated": None}

    def _save(self):
        BRAIN_DIR.mkdir(parents=True, exist_ok=True)
        self._data["last_updated"] = datetime.now().isoformat()
        TRAINING_HISTORY_PATH.write_text(json.dumps(self._data, indent=2))

    def record(self, question: Dict, choice: str, is_correct: bool):
        """Record a single answer."""
        cat = question.get("category", "unknown")
        if is_correct:
            self._data["total_correct"] = self._data.get("total_correct", 0) + 1
            self._data.setdefault("category_correct", {})[cat] = self._data.get("category_correct", {}).get(cat, 0) + 1
        else:
            self._data["total_wrong"] = self._data.get("total_wrong", 0) + 1
            self._data.setdefault("category_wrong", {})[cat] = self._data.get("category_wrong", {}).get(cat, 0) + 1
            self._data.setdefault("wrong_questions", []).append({
                "question": question["question"],
                "your_answer": choice,
                "correct_answer": question["answer"],
                "correct_text": question["options"][ord(question["answer"]) - 65],
                "category": cat,
                "timestamp": datetime.now().isoformat(),
            })
            # Keep last 200 wrong answers
            self._data["wrong_questions"] = self._data["wrong_questions"][-200:]
        self._save()

    def record_none(self, question: Dict):
        """Record a 'none' answer — Ira doesn't know this. Flag for NN research."""
        self._data.setdefault("none_questions", []).append({
            "question": question["question"],
            "correct_text": question["options"][ord(question["answer"]) - 65],
            "category": question.get("category", "unknown"),
            "timestamp": datetime.now().isoformat(),
        })
        self._data["none_questions"] = self._data["none_questions"][-100:]
        self._save()

    def bump_session(self):
        self._data["sessions"] = self._data.get("sessions", 0) + 1
        self._save()

    def get_weak_categories(self) -> Dict[str, float]:
        """Return category -> weakness score (0-1, higher = weaker)."""
        correct = self._data.get("category_correct", {})
        wrong = self._data.get("category_wrong", {})
        all_cats = set(list(correct.keys()) + list(wrong.keys()))
        weights = {}
        for cat in all_cats:
            c = correct.get(cat, 0)
            w = wrong.get(cat, 0)
            total = c + w
            if total == 0:
                weights[cat] = 0.5
            else:
                weights[cat] = round(w / total, 2)
        return weights

    def get_category_stats(self) -> Dict[str, Dict]:
        correct = self._data.get("category_correct", {})
        wrong = self._data.get("category_wrong", {})
        all_cats = sorted(set(list(correct.keys()) + list(wrong.keys())))
        stats = {}
        for cat in all_cats:
            c = correct.get(cat, 0)
            w = wrong.get(cat, 0)
            t = c + w
            stats[cat] = {"correct": c, "wrong": w, "total": t, "accuracy": round(c / t, 2) if t else 0}
        return stats

    def write_training_weights(self):
        """
        Write training_weights.json — consumed by generate_answer.py
        to reinforce weak knowledge areas in Ira's system prompt.
        """
        weak = self.get_weak_categories()
        wrong_qs = self._data.get("wrong_questions", [])

        # Extract the most-missed facts as reinforcement hints
        reinforcements = []
        seen = set()
        for wq in reversed(wrong_qs[-50:]):
            fact = f"{wq['question']} -> {wq['correct_text']}"
            if fact not in seen:
                seen.add(fact)
                reinforcements.append({
                    "category": wq["category"],
                    "fact": f"Q: {wq['question']} A: {wq['correct_text']}",
                })
            if len(reinforcements) >= 15:
                break

        # Also include "none" questions as knowledge gaps
        none_qs = self._data.get("none_questions", [])
        knowledge_gaps = []
        for nq in reversed(none_qs[-20:]):
            knowledge_gaps.append({
                "question": nq["question"],
                "answer": nq["correct_text"],
                "category": nq["category"],
            })

        # Include lessons from commentary
        lessons = []
        if LESSONS_FROM_TRAINING_PATH.exists():
            try:
                raw_lessons = json.loads(LESSONS_FROM_TRAINING_PATH.read_text())
                for les in reversed(raw_lessons[-20:]):
                    if les.get("commentary") and len(les["commentary"]) > 10:
                        lessons.append({
                            "context": les.get("question", ""),
                            "insight": les["commentary"][:300],
                        })
            except (json.JSONDecodeError, IOError):
                pass

        weights = {
            "weak_categories": weak,
            "reinforcements": reinforcements,
            "knowledge_gaps": knowledge_gaps[:10],
            "rushabh_insights": lessons[:10],
            "total_sessions": self._data.get("sessions", 0),
            "total_questions": self._data.get("total_correct", 0) + self._data.get("total_wrong", 0),
            "generated_at": datetime.now().isoformat(),
        }
        BRAIN_DIR.mkdir(parents=True, exist_ok=True)
        TRAINING_WEIGHTS_PATH.write_text(json.dumps(weights, indent=2))


# ===========================================================================
# SESSION — continuous, never-ending
# ===========================================================================

class TrainSession:
    """Continuous quiz session. Generates one question at a time, forever."""

    def __init__(self):
        self.session_path = TRAIN_SESSION_PATH
        self._s = self._load()
        self.history = TrainingHistory()

    def _load(self) -> Dict:
        if self.session_path.exists():
            try:
                return json.loads(self.session_path.read_text())
            except (json.JSONDecodeError, IOError):
                pass
        return self._blank()

    def _blank(self) -> Dict:
        return {
            "active": False,
            "current_question": None,
            "correct": 0, "wrong": 0,
            "streak": 0, "best_streak": 0,
            "seen_fingerprints": [],
            "started_at": None,
            "question_number": 0,
        }

    def _save(self):
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        self.session_path.write_text(json.dumps(self._s, indent=2, default=str))

    # --- properties ---
    @property
    def active(self) -> bool: return self._s.get("active", False)
    @property
    def correct(self) -> int: return self._s.get("correct", 0)
    @property
    def wrong(self) -> int: return self._s.get("wrong", 0)
    @property
    def total(self) -> int: return self.correct + self.wrong
    @property
    def streak(self) -> int: return self._s.get("streak", 0)
    @property
    def best_streak(self) -> int: return self._s.get("best_streak", 0)
    @property
    def current_question(self) -> Optional[Dict]: return self._s.get("current_question")
    @property
    def question_number(self) -> int: return self._s.get("question_number", 0)

    def start(self):
        """Start or restart a continuous session."""
        self._s = self._blank()
        self._s["active"] = True
        self._s["started_at"] = datetime.now().isoformat()
        self.history.bump_session()
        self._save()

    def reset(self):
        """Full reset — clear session AND history."""
        self._s = self._blank()
        self._save()
        # Reset history too
        if TRAINING_HISTORY_PATH.exists():
            TRAINING_HISTORY_PATH.unlink()
        if TRAINING_WEIGHTS_PATH.exists():
            TRAINING_WEIGHTS_PATH.unlink()
        self.history = TrainingHistory()

    def generate_next(self) -> Dict:
        """Generate a fresh question, weighted toward weak categories."""
        seen = set(self._s.get("seen_fingerprints", []))
        weak = self.history.get_weak_categories()

        # Build weighted generator list — weak categories get more picks
        weighted_gens = []
        cat_to_gens = {
            "pricing": [_gen_price],
            "specs": [_gen_forming_area, _gen_heater, _gen_thickness, _gen_vacuum],
            "product_knowledge": [_gen_concept, _gen_series],
            "applications": [_gen_application],
            "customers": [_gen_customer_order],
            "rules": [_gen_concept],
        }
        for cat, gens in cat_to_gens.items():
            weakness = weak.get(cat, 0.5)
            weight = max(1, int(weakness * 5))  # 0.0 -> 1x, 1.0 -> 5x
            for g in gens:
                weighted_gens.extend([g] * weight)
        if not weighted_gens:
            weighted_gens = GENERATORS

        for _ in range(100):
            gen = random.choice(weighted_gens)
            try:
                q = gen()
            except Exception:
                continue
            if not q:
                continue
            fp = _q_fingerprint(q["question"])
            if fp not in seen:
                self._s["question_number"] = self._s.get("question_number", 0) + 1
                q["id"] = f"Q{self._s['question_number']:02d}"
                self._s["current_question"] = q
                seen.add(fp)
                self._s["seen_fingerprints"] = list(seen)[-500:]  # keep last 500
                self._save()
                return q

        # Fallback: allow repeats if we've exhausted the pool
        self._s["seen_fingerprints"] = []
        return self.generate_next()

    def answer_raw(self, raw_text: str) -> Optional[Dict]:
        """
        Answer the current question with natural language support.

        Accepts:
          "A", "B", "C", "D"  — direct letter
          "none"               — acknowledge Ira doesn't know this
          "Pneumatic..."       — fuzzy match to option text
          "B but also..."      — letter + commentary captured as lesson
        """
        q = self._s.get("current_question")
        if not q:
            return None

        choice, commentary = _parse_answer(raw_text, q)

        # Save any commentary as a lesson regardless of correctness
        if commentary:
            _save_lesson(q, commentary, choice or "?")

        # Handle "none" — Ira acknowledges she doesn't know
        if choice == "NONE":
            self._s["current_question"] = None
            self._save()
            correct_text = q["options"][ord(q["answer"]) - 65]
            # Record as a special "none" event — not wrong, but flagged for research
            self.history.record_none(q)
            self.history.write_training_weights()
            return {
                "is_none": True,
                "correct_answer": q["answer"],
                "correct_text": correct_text,
                "commentary": commentary,
            }

        # Could not parse any answer
        if choice is None:
            return {"parse_failed": True, "raw": raw_text}

        is_correct = choice == q["answer"]

        if is_correct:
            self._s["correct"] = self.correct + 1
            self._s["streak"] = self.streak + 1
            if self._s["streak"] > self._s.get("best_streak", 0):
                self._s["best_streak"] = self._s["streak"]
        else:
            self._s["wrong"] = self.wrong + 1
            self._s["streak"] = 0

        self.history.record(q, choice, is_correct)
        self.history.write_training_weights()

        correct_text = q["options"][ord(q["answer"]) - 65]
        self._s["current_question"] = None
        self._save()

        return {
            "is_correct": is_correct,
            "correct_answer": q["answer"],
            "correct_text": correct_text,
            "streak": self.streak,
            "your_choice": choice,
            "your_text": q["options"][ord(choice) - 65] if choice in "ABCD" else raw_text[:60],
            "commentary": commentary,
        }


# ===========================================================================
# FORMATTING
# ===========================================================================

CAT_EMOJI = {"pricing": "\U0001f4b0", "specs": "\U0001f527", "product_knowledge": "\U0001f4da",
             "applications": "\U0001f3ed", "rules": "\U0001f4cf", "customers": "\U0001f91d"}

def _fmt_q(q: Dict) -> str:
    e = CAT_EMOJI.get(q.get("category", ""), "\u2753")
    lines = [f"{e} **Question #{q['id'][1:]}** [{q.get('category','')}]\n"]
    lines.append(f"{q['question']}\n")
    for i, opt in enumerate(q["options"]):
        lines.append(f"  **{chr(65+i)}.** {opt}")
    lines.append(f"\n\u2192 `/train answer A/B/C/D`")
    return "\n".join(lines)

def _score_bar(c: int, t: int) -> str:
    if t == 0: return "\u2591" * 10 + " 0%"
    p = c / t
    f = int(p * 10)
    return "\u2588" * f + "\u2591" * (10 - f) + f" {p:.0%}"


# ===========================================================================
# COMMAND HANDLER
# ===========================================================================

def handle_train_command(text: str) -> str:
    text = text.strip()
    parts = text.split()
    session = TrainSession()

    # /train with no args — show current Q or help
    if len(parts) <= 1:
        if session.active and session.current_question:
            return _fmt_q(session.current_question) + f"\n\n\U0001f4ca {session.correct}/{session.total} correct"
        if session.active:
            q = session.generate_next()
            return _fmt_q(q) + f"\n\n\U0001f4ca {session.correct}/{session.total} correct"
        return (
            "\U0001f9e0 **Brain Training Mode**\n\n"
            "Test your Machinecraft knowledge \u2014 Duolingo style!\n"
            "Questions keep coming. Wrong answers teach Ira what to reinforce.\n\n"
            "**Commands:**\n"
            "\u2022 `/train start` \u2014 Begin continuous quiz\n"
            "\u2022 `/train answer A/B/C/D` \u2014 Answer current question\n"
            "\u2022 `/train next` \u2014 Skip to next question\n"
            "\u2022 `/train score` \u2014 Detailed breakdown\n"
            "\u2022 `/train reset` \u2014 Clear all history\n"
        )

    sub = parts[1].lower()

    # --- START ---
    if sub == "start":
        session.start()
        q = session.generate_next()
        return (
            "\U0001f3af **Quiz started!** Questions will keep coming.\n"
            "\u2501" * 28 + "\n\n" + _fmt_q(q)
        )

    # --- NEXT (skip current, get new) ---
    if sub == "next":
        if not session.active:
            return "No active quiz. Run `/train start` to begin!"
        q = session.generate_next()
        return _fmt_q(q)

    # --- ANSWER ---
    if sub == "answer":
        if not session.active:
            return "No active quiz. Run `/train start` to begin!"
        if not session.current_question:
            q = session.generate_next()
            return "No pending question. Here's a new one:\n\n" + _fmt_q(q)

        # Join everything after "answer" as the raw answer text
        raw_answer = " ".join(parts[2:]) if len(parts) > 2 else ""
        if not raw_answer:
            return "Type your answer: `/train answer A` or `/train answer none` or just type the answer text."

        result = session.answer_raw(raw_answer)
        if result is None:
            return "Something went wrong. Try `/train next`."

        # Could not parse the answer at all
        if result.get("parse_failed"):
            return (
                f"Couldn't match your answer to any option.\n"
                f"Try: `/train answer A`, `/train answer B`, etc. or `/train answer none`"
            )

        # "None" — Ira doesn't know, trigger NN research
        if result.get("is_none"):
            resp = (
                f"\U0001f914 **Noted — Ira doesn't know this yet.**\n"
                f"Correct answer: **{result['correct_answer']}**: _{result['correct_text']}_\n\n"
                f"\U0001f50d Launching NN research in background..."
            )

            # Trigger async NN research for this question
            try:
                from nn_research import research_async
                q = session.current_question or {}
                research_query = q.get("question", result.get("correct_text", ""))
                chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
                research_async(research_query, chat_id)
                resp += " Results will arrive shortly."
            except Exception as e:
                logger.warning("Could not start NN research: %s", e)
                resp += f"\n(Research unavailable: {e})"

            nq = session.generate_next()
            resp += "\n\n" + "\u2501" * 28 + "\n\n" + _fmt_q(nq)
            return resp

        # Build response
        commentary_note = ""
        if result.get("commentary"):
            commentary_note = f"\n\U0001f4dd _Noted your insight — saved as a lesson for Ira._"

        if result["is_correct"]:
            streak = result["streak"]
            fire = "\U0001f525" * min(streak, 5)
            resp = f"\u2705 **Correct!** {fire}"
            if streak >= 3:
                resp += f" ({streak} in a row!)"
            resp += commentary_note
        else:
            resp = (
                f"\u274c **Wrong.** You picked {result['your_choice']}: _{result['your_text']}_\n"
                f"Correct answer: **{result['correct_answer']}**: _{result['correct_text']}_"
            )
            resp += commentary_note

        resp += f"\n\n\U0001f4ca {session.correct}/{session.total} correct | \U0001f525 streak: {session.streak}"

        nq = session.generate_next()
        resp += "\n\n" + "\u2501" * 28 + "\n\n" + _fmt_q(nq)

        return resp

    # --- SCORE ---
    if sub in ("score", "status"):
        if not session.active and session.total == 0:
            return "No training data yet. Run `/train start` to begin!"

        lines = [
            f"\U0001f4ca **Training Score**\n",
            f"**This session:** {session.correct}/{session.total} ({_score_bar(session.correct, session.total)})",
            f"\U0001f525 Streak: {session.streak} (best: {session.best_streak})\n",
        ]

        cat_stats = session.history.get_category_stats()
        if cat_stats:
            lines.append("**All-time by category:**")
            for cat, s in sorted(cat_stats.items(), key=lambda x: x[1]["accuracy"]):
                emoji = CAT_EMOJI.get(cat, "\u2753")
                bar = _score_bar(s["correct"], s["total"])
                lines.append(f"  {emoji} {cat}: {s['correct']}/{s['total']} {bar}")

        weak = session.history.get_weak_categories()
        weakest = sorted(weak.items(), key=lambda x: -x[1])[:3]
        if weakest and weakest[0][1] > 0.3:
            lines.append(f"\n\U0001f4aa **Focus areas:** {', '.join(c for c, _ in weakest if _ > 0.3)}")

        return "\n".join(lines)

    # --- RESET ---
    if sub == "reset":
        session.reset()
        return "\U0001f5d1\ufe0f **All training data cleared.** Run `/train start` to begin fresh."

    return f"Unknown command: `{sub}`. Try `/train` for help."


# backward compat
def handle_natural_language_training(text: str) -> tuple:
    return (False, "")
