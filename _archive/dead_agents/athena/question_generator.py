#!/usr/bin/env python3
"""
ATHENA Question Generator
=========================

Generates realistic customer questions based on patterns learned from
actual sales conversations. Used to test IRA's ability to respond
like Rushabh.

Patterns extracted from real customer inquiries:
1. Initial contact inquiries
2. Follow-up questions
3. Technical deep-dives
4. Pricing negotiations
5. Post-sale support
"""

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent


@dataclass
class GeneratedQuestion:
    """A generated customer question."""
    id: str
    category: str
    question: str
    context: str
    expected_topics: List[str]
    difficulty: str  # easy, medium, hard
    based_on_real: bool


# Question templates extracted from real customer patterns
QUESTION_TEMPLATES = {
    'pricing_inquiry': {
        'initial': [
            "We are looking for a thermoforming machine for {application}. Can you send us a quotation?",
            "What is the price for a {machine_type} machine with {specs}?",
            "Could you please provide pricing for your {series} series?",
            "We need a quote for a machine capable of forming {material} up to {thickness}mm thick.",
            "What would be the investment for a complete thermoforming line for {application}?",
        ],
        'followup': [
            "Thank you for the quote. Is there any flexibility on the price?",
            "The budget is around {budget}. Can we work within this range?",
            "What payment terms do you offer?",
            "Does the price include installation and training?",
        ],
    },
    'technical_specs': {
        'initial': [
            "What is the maximum sheet thickness your {series} can handle?",
            "Can you provide the technical specifications for {machine_model}?",
            "What are the dimensions and power requirements for the {machine_type}?",
            "What is the forming depth capability of your machines?",
            "Can your machines process {material} sheets?",
        ],
        'followup': [
            "What about the cycle time for parts of this size?",
            "How does the heating system work?",
            "What vacuum pump capacity is included?",
        ],
    },
    'materials': {
        'initial': [
            "We work with {material} sheets, {thickness}mm thick. Which machine do you recommend?",
            "Can your machines handle {material} with good surface finish?",
            "What materials are your machines optimized for?",
            "We need to form thick gauge {material}. What are our options?",
        ],
        'followup': [
            "What about {other_material}? Same machine?",
            "Any special settings needed for this material?",
        ],
    },
    'logistics': {
        'initial': [
            "What is the delivery time for a {machine_model}?",
            "How long does installation take?",
            "What are the shipping costs to {country}?",
            "Is training included in the package?",
        ],
        'followup': [
            "Can we expedite the delivery?",
            "Who will do the installation?",
            "How long for commissioning?",
        ],
    },
    'support': {
        'initial': [
            "We have an issue with our {machine_model}. The {component} is not working properly.",
            "We need spare parts for our machine - can you provide a list?",
            "What is included in your service contract?",
            "The machine is showing error code {error_code}. What does this mean?",
        ],
        'followup': [
            "How quickly can you send a technician?",
            "What is the cost for this repair?",
            "Do you have this part in stock?",
        ],
    },
    'application': {
        'initial': [
            "We want to produce {product_type} for {industry}. What machine would you recommend?",
            "Can your machines make {product_type} with {feature}?",
            "We are currently using {competitor} machine. What can you offer us?",
            "What output can we expect for {product_type} production?",
        ],
        'followup': [
            "What tooling would we need?",
            "Can you share examples of similar applications?",
            "What about automation options?",
        ],
    },
    'meeting_request': {
        'initial': [
            "Can we visit your factory to see the machines in operation?",
            "Are you attending {trade_show} this year?",
            "Can you arrange a demo for us?",
            "We would like to meet at your facility. When is a good time?",
        ],
        'followup': [
            "What would we see during the visit?",
            "Can we bring our materials for a trial?",
        ],
    },
}

# Variables for template filling
TEMPLATE_VARIABLES = {
    'application': ['food packaging', 'medical trays', 'automotive parts', 'blister packaging', 
                   'industrial enclosures', 'refrigerator liners', 'bathroom products'],
    'machine_type': ['vacuum forming', 'pressure forming', 'twin-sheet', 'skin packaging'],
    'series': ['PF1', 'AM-P', 'AM series', 'PF1-X'],
    'material': ['ABS', 'HIPS', 'PP', 'PET', 'HDPE', 'PC', 'PMMA', 'PVC'],
    'thickness': ['1.5', '2', '3', '4', '5', '6', '8', '10'],
    'machine_model': ['PF1-1520', 'PF1-2030', 'AM-P 680', 'PF1-X-1520', 'PF1-3030'],
    'specs': ['1500x2000mm forming area', 'automatic sheet feeding', 'servo-driven'],
    'budget': ['$50,000', '$100,000', '€80,000', '$150,000', '$200,000'],
    'country': ['Germany', 'France', 'UK', 'USA', 'Canada', 'Netherlands', 'Belgium'],
    'component': ['heater', 'vacuum pump', 'servo motor', 'PLC', 'forming platen'],
    'error_code': ['E101', 'E205', 'H03', 'F12'],
    'product_type': ['food trays', 'blister packs', 'automotive panels', 'equipment covers'],
    'industry': ['food packaging', 'medical', 'automotive', 'consumer goods'],
    'competitor': ['Illig', 'Kiefel', 'Geiss', 'CMS'],
    'trade_show': ['K-Show', 'NPE', 'Plastpol', 'Interpack'],
    'feature': ['high definition', 'undercuts', 'deep draw', 'multi-cavity'],
    'other_material': ['ABS', 'PETG', 'polycarbonate', 'acrylic'],
}


class QuestionGenerator:
    """Generates realistic customer questions for testing IRA."""
    
    def __init__(self, training_data_path: Path = None):
        self.training_data = None
        self.question_id = 0
        
        if training_data_path and training_data_path.exists():
            with open(training_data_path, 'r') as f:
                self.training_data = json.load(f)
    
    def _fill_template(self, template: str) -> str:
        """Fill template with random variables."""
        result = template
        for var, options in TEMPLATE_VARIABLES.items():
            placeholder = '{' + var + '}'
            if placeholder in result:
                result = result.replace(placeholder, random.choice(options))
        return result
    
    def generate_question(self, category: str = None, is_followup: bool = False) -> GeneratedQuestion:
        """Generate a single question."""
        if category is None:
            category = random.choice(list(QUESTION_TEMPLATES.keys()))
        
        templates = QUESTION_TEMPLATES.get(category, QUESTION_TEMPLATES['pricing_inquiry'])
        template_type = 'followup' if is_followup else 'initial'
        template_list = templates.get(template_type, templates.get('initial', []))
        
        template = random.choice(template_list)
        question = self._fill_template(template)
        
        self.question_id += 1
        
        # Determine expected topics based on category
        expected_topics = {
            'pricing_inquiry': ['price', 'quote', 'cost', 'investment'],
            'technical_specs': ['specifications', 'dimensions', 'capacity'],
            'materials': ['material', 'thickness', 'compatibility'],
            'logistics': ['delivery', 'installation', 'timeline'],
            'support': ['service', 'spare parts', 'repair'],
            'application': ['recommendation', 'suitable', 'output'],
            'meeting_request': ['visit', 'demo', 'schedule'],
        }.get(category, [])
        
        return GeneratedQuestion(
            id=f'gen_{self.question_id}',
            category=category,
            question=question,
            context='Generated from templates based on real customer patterns',
            expected_topics=expected_topics,
            difficulty='easy' if is_followup else 'medium',
            based_on_real=True,
        )
    
    def generate_from_real_data(self) -> Optional[GeneratedQuestion]:
        """Generate a question variation based on real training data."""
        if not self.training_data or not self.training_data.get('qa_pairs'):
            return None
        
        pair = random.choice(self.training_data['qa_pairs'])
        original_question = pair.get('customer_question', '')
        
        # Create a variation by modifying key elements
        self.question_id += 1
        
        return GeneratedQuestion(
            id=f'real_{self.question_id}',
            category=pair.get('category', 'general_inquiry'),
            question=original_question[:500],  # Use actual question
            context=f"Based on real conversation with {pair.get('company', 'customer')}",
            expected_topics=[],
            difficulty='medium',
            based_on_real=True,
        )
    
    def generate_batch(self, count: int = 50, mix_real: bool = True) -> List[GeneratedQuestion]:
        """Generate a batch of questions for training."""
        questions = []
        
        for i in range(count):
            # 60% from templates, 40% from real data (if available)
            use_real = mix_real and self.training_data and random.random() < 0.4
            
            if use_real:
                q = self.generate_from_real_data()
                if q:
                    questions.append(q)
                    continue
            
            # Generate from template
            category = random.choice(list(QUESTION_TEMPLATES.keys()))
            is_followup = random.random() < 0.3
            questions.append(self.generate_question(category, is_followup))
        
        return questions
    
    def generate_conversation_flow(self, turns: int = 3) -> List[GeneratedQuestion]:
        """Generate a multi-turn conversation flow."""
        questions = []
        category = random.choice(list(QUESTION_TEMPLATES.keys()))
        
        # First question is always initial
        questions.append(self.generate_question(category, is_followup=False))
        
        # Subsequent questions are followups
        for i in range(1, turns):
            # Sometimes switch category
            if random.random() < 0.3:
                category = random.choice(list(QUESTION_TEMPLATES.keys()))
            questions.append(self.generate_question(category, is_followup=True))
        
        return questions


def main():
    """Generate sample questions."""
    print("="*70)
    print("  ATLAS QUESTION GENERATOR - SAMPLE OUTPUT")
    print("="*70)
    
    generator = QuestionGenerator()
    
    print("\n--- Single Questions by Category ---\n")
    for category in QUESTION_TEMPLATES.keys():
        q = generator.generate_question(category)
        print(f"[{q.category}] {q.question}")
    
    print("\n--- Multi-turn Conversation Flow ---\n")
    flow = generator.generate_conversation_flow(turns=4)
    for i, q in enumerate(flow, 1):
        print(f"Turn {i} [{q.category}]: {q.question}")
    
    print("\n--- Batch Generation Stats ---\n")
    batch = generator.generate_batch(50, mix_real=False)
    categories = {}
    for q in batch:
        categories[q.category] = categories.get(q.category, 0) + 1
    
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
