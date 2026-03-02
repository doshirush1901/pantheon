#!/usr/bin/env python3
"""
IRA Pantheon Test Runner (OpenClaw Native)

This script demonstrates the new OpenClaw-native architecture where:
- The Pantheon members are skills, not separate agents
- The LLM (Athena) is the orchestrator
- Skills are invoked through clean service functions

Usage:
    python run_agents.py          # Interactive mode
    python run_agents.py --test   # Run test suite
    python run_agents.py -m "Your question here"
"""

import asyncio
import logging
import sys
from typing import Optional

# Add the project to path
sys.path.insert(0, ".")
sys.path.insert(0, "openclaw/agents/ira")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("ira.pantheon")


async def process_message(message: str, user_id: str = "test_user") -> str:
    """
    Process a message through the Pantheon pipeline.
    
    This demonstrates how the LLM would orchestrate the skills:
    1. Analyze intent
    2. Research the query
    3. Write a response
    4. Verify for accuracy
    5. Reflect on the interaction
    """
    from openclaw.agents.ira.src.agents import (
        analyze_intent,
        create_plan,
        research,
        write,
        verify,
        reflect,
        synthesize_response
    )
    
    logger.info("=" * 60)
    logger.info(f"Processing: {message[:80]}...")
    logger.info("=" * 60)
    
    # Step 1: Analyze Intent (Athena thinks)
    intent = analyze_intent(message)
    plan = create_plan(message, intent, user_id)
    
    logger.info(f"[Athena] Intent detected: {intent}")
    logger.info(f"[Athena] Plan: {plan.steps}")
    
    # Step 2: Research (Clio searches)
    logger.info("[Clio] Researching...")
    research_output = await research(message, {"user_id": user_id, "intent": intent})
    logger.info(f"[Clio] Found {len(research_output)} chars of research")
    
    # Step 3: Write (Calliope crafts)
    logger.info("[Calliope] Drafting response...")
    context = {
        "user_id": user_id,
        "intent": intent,
        "channel": "cli",
        "research_output": research_output
    }
    draft = await write(message, context)
    logger.info(f"[Calliope] Draft ready ({len(draft)} chars)")
    
    # Step 4: Verify (Vera checks)
    logger.info("[Vera] Verifying accuracy...")
    verified_response = await verify(draft, message, context)
    logger.info("[Vera] Verification complete")
    
    # Step 5: Synthesize (Athena finalizes)
    final_response = synthesize_response(
        research_output=research_output,
        writing_output=draft,
        verification_output=verified_response
    )
    
    # Step 6: Reflect (Sophia learns - awaited with error handling)
    try:
        await reflect({
            "user_message": message,
            "response": final_response,
            "intent": intent
        })
    except Exception as e:
        logger.warning("Reflection failed (non-fatal): %s", e, exc_info=True)
    
    logger.info("-" * 60)
    
    return final_response


async def run_tests():
    """Run the test suite."""
    print("\n" + "=" * 60)
    print("  IRA PANTHEON TEST SUITE (OpenClaw Native)")
    print("=" * 60 + "\n")
    
    test_cases = [
        {
            "query": "What are the specs for PF1-C-2015?",
            "description": "Specs Query",
            "expect": ["2000", "1500", "forming"],
        },
        {
            "query": "Suggest a machine for 4mm thick ABS sheets.",
            "description": "Thick Material + AM Warning",
            "expect": ["PF1", "1.5mm", "AM"],
        },
        {
            "query": "What's the price for PF1-C-2015?",
            "description": "Pricing with Disclaimer",
            "expect": ["₹", "subject to"],
        },
        {
            "query": "Draft an email to John at ABC Corp about the PF1-5060.",
            "description": "Email Draft",
            "expect": ["Hi", "John", "PF1-5060"],
        },
    ]
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test['description']} ---")
        print(f"Query: {test['query']}")
        
        try:
            response = await process_message(test['query'])
            
            # Check expectations
            all_found = True
            for expected in test['expect']:
                if expected.lower() not in response.lower():
                    all_found = False
                    print(f"  ✗ Missing expected content: '{expected}'")
            
            if all_found and len(response) > 50:
                print(f"✓ PASS - Response length: {len(response)} chars")
                print(f"  Preview: {response[:150]}...")
                passed += 1
            else:
                print(f"✗ FAIL")
                print(f"  Response: {response[:200]}")
                failed += 1
                
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1
        
        await asyncio.sleep(0.5)
    
    print("\n" + "=" * 60)
    print(f"  RESULTS: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")
    
    return passed, failed


async def interactive_mode():
    """Run in interactive mode."""
    print("\n" + "=" * 60)
    print("  IRA PANTHEON - Interactive Mode")
    print("  (OpenClaw Native Architecture)")
    print("=" * 60)
    print("\nType 'quit' to exit, 'test' to run tests\n")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("Goodbye!")
                break
            
            if user_input.lower() == 'test':
                await run_tests()
                continue
            
            response = await process_message(user_input)
            print(f"\nIra: {response}")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


async def single_query(message: str):
    """Process a single query."""
    response = await process_message(message)
    print(f"\n{response}\n")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="IRA Pantheon Test Runner")
    parser.add_argument("--test", action="store_true", help="Run test suite")
    parser.add_argument("--tools", action="store_true", help="Use LLM tool mode (Athena chooses skills)")
    parser.add_argument("-m", "--message", type=str, help="Process a single message")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive mode")
    args = parser.parse_args()
    
    if args.test:
        asyncio.run(run_tests())
    elif args.message:
        asyncio.run(single_query(args.message, use_tools=args.tools))
    else:
        asyncio.run(interactive_mode())


if __name__ == "__main__":
    main()
