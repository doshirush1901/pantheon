# 🎭 APOLLO - Sales Simulation & Learning System

*"I become your customer so IRA can practice and learn."*

APOLLO is a comprehensive training system for IRA that:
1. **Simulates** realistic customer conversations
2. **Scores** IRA's responses mathematically
3. **Learns** from errors and Rushabh's corrections
4. **Improves** over time through feedback loops

## Features

- **6 Customer Personas**: From easy (startup) to very hard (tough negotiator)
- **Multi-turn Conversations**: Simulates realistic sales cycles (4-8 emails)
- **Accuracy Scoring**: Mathematical formula comparing IRA vs expected responses
- **Learning Engine**: Tracks error patterns, recommends knowledge sources
- **Pipeline Validation**: Ensures IRA follows all steps (ingest → retrieve → generate → verify)
- **Escalation Detection**: Knows when to ask Rushabh for help

## Quick Start

```bash
# Single simulation (interactive)
python agents/apollo/run_simulation.py --persona european

# Single simulation (auto mode)
python agents/apollo/run_simulation.py --persona indian_auto --turns 5 --auto

# Batch simulation (all personas)
python agents/apollo/batch_simulate.py --turns 4

# Evaluate past simulations
python agents/apollo/evaluator.py
```

## Available Personas

| Key | Name | Industry | Budget | Difficulty |
|-----|------|----------|--------|------------|
| `european` | Jean-François Deltenre | Automotive Interior | EUR 200K | Medium |
| `indian_auto` | Rajesh Sharma | Tier-1 Auto Supplier | INR 1 Cr | Medium |
| `startup` | Mike Chen | Sustainable Packaging | USD 60K | Easy |
| `us_distributor` | Josh Szabo | Machinery Distribution | USD 150K | Medium |
| `large_project` | Dr. Ahmed Al-Rashid | Turnkey Facility | USD 750K | Hard |
| `tough_negotiator` | Viktor Petrov | Food Packaging | EUR 180K | **Very Hard** |

## Files

```
agents/apollo/
├── AGENTS.md                    # Agent identity & persona definitions
├── README.md                    # This file
├── __init__.py                  # Package init
│
├── # SIMULATION
├── run_simulation.py            # Interactive single simulation
├── batch_simulate.py            # Batch simulation across personas
├── email_simulation.py          # Real email simulation (sends actual emails)
├── simulator.py                 # Core simulation engine (template-based)
│
├── # CREATIVE TRAINING (NEW!)
├── creative_customer_agent.py   # LLM-powered customer simulation
├── sales_flow_training.py       # Full training loop with evaluation
│
├── # EVALUATION & LEARNING
├── evaluator.py                 # LLM-as-judge evaluation
├── accuracy_scorer.py           # Mathematical accuracy scoring
├── learning_engine.py           # Error tracking & improvement
├── pipeline_validator.py        # Ensures IRA follows all steps
└── training_loop.py             # Main training loop with learning
```

## Creative Training Mode (NEW!)

The creative training system uses GPT-4 to generate realistic customer emails 
based on patterns extracted from real Rushabh conversations:

```bash
# Single creative simulation
python agents/apollo/creative_customer_agent.py --persona dutch_hydroponics

# Full training loop with evaluation
python agents/apollo/sales_flow_training.py --persona polish_automotive

# Batch training across all personas
python agents/apollo/sales_flow_training.py --batch --iterations 3

# Generate full training dataset
python agents/apollo/sales_flow_training.py --generate-dataset --size 50
```

### How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SALES FLOW TRAINING LOOP                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐     ┌──────────────────┐                     │
│  │ Sales Patterns   │────▶│ Creative Agent   │                     │
│  │ (from emails)    │     │ (GPT-4 powered)  │                     │
│  └──────────────────┘     └────────┬─────────┘                     │
│                                     │                               │
│                           Generates "Customer" Email                │
│                                     │                               │
│                                     ▼                               │
│                          ┌──────────────────┐                      │
│                          │      IRA         │                      │
│                          │ (Full Pipeline)  │                      │
│                          │ Mem0+RAG+Brain   │                      │
│                          └────────┬─────────┘                      │
│                                   │                                 │
│                           IRA's Response                            │
│                                   │                                 │
│                                   ▼                                 │
│                          ┌──────────────────┐                      │
│                          │   Evaluator      │                      │
│                          │ Score + Feedback │                      │
│                          └────────┬─────────┘                      │
│                                   │                                 │
│                    ┌──────────────┴──────────────┐                 │
│                    │                             │                  │
│                    ▼                             ▼                  │
│         ┌──────────────────┐          ┌──────────────────┐        │
│         │ Training Example │          │ Next Stage Email │        │
│         │ (for ingestion)  │          │ (continues loop) │        │
│         └──────────────────┘          └──────────────────┘        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Enhanced Personas (Based on Real Customers)

| Key | Based On | Cycle | Difficulty |
|-----|----------|-------|------------|
| `dutch_hydroponics` | DutchTides (22 months) | Long | Hard |
| `polish_automotive` | JoPlast (7 months) | Medium | Medium |
| `belgian_manufacturer` | Batelaan (3 months) | Fast | Easy |
| `irish_fabricator` | Donite | Medium | Medium |
| `italian_skeptic` | European skeptics | Long | Hard |
| `tough_negotiator` | Price fighters | Variable | Very Hard |

## Output

Simulations are saved to `data/simulations/`:
- `sim_*.json` - Individual simulation conversations
- `batch_*.json` - Batch simulation results
- `evaluation_*.json` - Evaluation scores

## Evaluation Criteria

Each simulation is scored 1-5 on:

1. **Response Relevance** - Does IRA answer what the customer asked?
2. **Technical Accuracy** - Is the information correct?
3. **Sales Effectiveness** - Does IRA move the deal forward?
4. **Tone & Professionalism** - Does IRA sound like a helpful salesperson?
5. **Conciseness** - Is the response appropriately sized?

## Sales Cycle Stages

APOLLO simulates realistic progression:

1. **Initial Inquiry** (Turn 1-2): General interest, spec questions
2. **Technical Discussion** (Turn 3-4): Deep technical questions, comparisons
3. **Commercial Negotiation** (Turn 5-6): Pricing, terms, objections
4. **Closing** (Turn 7+): Order or graceful decline

## Example Output

```
📊 SUMMARY
   Simulations Evaluated: 3
   Average Overall Score: 4.67/5

🎯 DEAL OUTCOMES
   High Likelihood:  3
   Medium Likelihood: 0
   Low Likelihood:   0
```

## Latest Benchmark (Feb 2026)

```
📊 SUMMARY (6 personas, 5 turns each)
   Average Score: 4.43/5
   Deal Success Rate: 83% (5/6 high likelihood)

📈 CATEGORY SCORES
   Relevance:           4.83/5 ████████████████████
   Tone:                4.83/5 ████████████████████
   Conciseness:         4.50/5 ██████████████████
   Technical Accuracy:  4.17/5 █████████████████
   Sales Effectiveness: 4.00/5 ████████████████

🎯 AREAS FOR IMPROVEMENT
   - Currency consistency (always quote in customer's currency)
   - Proactive CTAs (suggest next steps earlier)
   - Competitor comparisons (stronger data vs Kiefel/ILLIG)
   - Pricing consistency under negotiation pressure
```

## Accuracy Formula

IRA's accuracy is measured using a weighted formula:

```
Score = 0.40×Factual + 0.25×Completeness + 0.20×Semantic + 0.15×Style
```

| Component | Weight | Description |
|-----------|--------|-------------|
| Factual Accuracy | 40% | Are prices, specs, lead times correct? |
| Completeness | 25% | Did IRA answer all parts of the question? |
| Semantic Similarity | 20% | Does the meaning match expected response? |
| Style Match | 15% | Does it sound like Rushabh? |

## Learning Algorithm

The learning engine tracks:

1. **Error Patterns**: Recurring mistakes (e.g., wrong EUR→INR conversion)
2. **Knowledge Gaps**: Topics where IRA lacks information
3. **Escalation Rules**: When to ask Rushabh (competitors, special pricing)
4. **Correction Memory**: Past corrections to apply to similar queries

```python
# Improvement formula
Accuracy(t+1) = Accuracy(t) + α×(Expected - Actual) + β×Corrections

# α = learning rate from errors (0.1)
# β = weight of Rushabh's corrections (0.3)
```

## Training Commands

```bash
# Run training loop (learns from errors)
python agents/apollo/training_loop.py --iterations 20

# Interactive mode (allows corrections)
python agents/apollo/training_loop.py --iterations 10 --interactive

# Check learning progress
python agents/apollo/learning_engine.py
```

## Usage Tips

1. **Test new features**: Run batch simulations before/after making changes to IRA
2. **Identify gaps**: Look at "Areas for Improvement" in evaluation reports
3. **Train specific scenarios**: Use specific personas to test edge cases
4. **Compare models**: Run with `--simulate-ira` to compare GPT baseline vs real IRA
5. **Stress test**: Use `tough_negotiator` to test objection handling
6. **Review escalations**: Check which queries IRA couldn't handle confidently
