"""
Interactive Demo Script for Presentation
Run this for the 5-minute demo!

Usage:
    export OPENAI_API_KEY="your-key"
    python demo.py
"""

import os
import sys
import time

# Add color support
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_slow(text: str, delay: float = 0.02):
    """Print text with typewriter effect."""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()


def print_header(text: str):
    """Print formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}")
    print(f"{text:^70}")
    print(f"{'='*70}{Colors.END}\n")


def print_agent(agent: str, color: str, message: str):
    """Print agent message with formatting."""
    print(f"{color}{Colors.BOLD}[{agent}]{Colors.END} {message}")


def run_demo():
    """Run the interactive presentation demo."""

    print_header("KEPLER TEAM - ADVERSARIAL TRIBUNAL")
    print_slow("Welcome to our Multi-Agent Fact Verification System")
    print()

    # Show architecture
    print_header("ARCHITECTURE OVERVIEW")
    print("""
    Our system uses 4 specialized AI agents in a courtroom-style debate:

    🔴 PROSECUTOR    - Aggressively hunts for mutations and distortions
    🟢 DEFENSE       - Argues for faithful interpretation of the claim
    🟡 EPISTEMOLOGIST - Quantifies uncertainty and epistemic limits
    ⚖️  JURY FOREMAN  - Synthesizes arguments into final verdict
    """)

    input(f"\n{Colors.YELLOW}Press Enter to see the debate in action...{Colors.END}")

    # Load and run
    from agents import DebateOrchestrator, format_debate_for_presentation
    from visualize import create_debate_visualization, create_comparison_table
    from main import load_kepler_data, STRATEGIC_CASES

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print(f"{Colors.RED}ERROR: Set OPENAI_API_KEY environment variable{Colors.END}")
        return

    data = load_kepler_data()

    # Demo Case Selection
    print_header("STRATEGIC CASE SELECTION")
    print("We selected 5 cases showcasing different mutation types:\n")

    demo_cases = [
        (0, "Numerical boundary manipulation", "COVID deaths: 'less than' vs 'more than'"),
        (1, "Added information", "Michigan protest: specific number not in source"),
        (5, "Negation framing", "Record sales: same fact, different spin"),
        (7, "Borderline numerical", "COVID cases: 359k vs 360k - acceptable?"),
        (6, "Faithful baseline", "License to Kill: accurate extraction"),
    ]

    for case_id, mutation_type, description in demo_cases:
        print(f"  Case {case_id}: {Colors.BOLD}{mutation_type}{Colors.END}")
        print(f"           {description}\n")

    # Select one case for live demo
    print_header("LIVE DEBATE DEMO")

    print("Select a case for live demonstration:")
    for i, (case_id, mt, desc) in enumerate(demo_cases):
        print(f"  [{i+1}] Case {case_id}: {desc}")

    choice = input(f"\n{Colors.YELLOW}Enter choice (1-5) or press Enter for Case 0: {Colors.END}")
    choice = int(choice) - 1 if choice.strip() else 0
    selected_case_id = demo_cases[choice][0]

    case = data[selected_case_id]

    print(f"\n{Colors.CYAN}{'─'*70}{Colors.END}")
    print(f"{Colors.BOLD}CLAIM:{Colors.END}")
    print(f"  \"{case['claim']}\"")
    print(f"\n{Colors.BOLD}TRUTH:{Colors.END}")
    print(f"  \"{case['truth']}\"")
    print(f"{Colors.CYAN}{'─'*70}{Colors.END}")

    input(f"\n{Colors.YELLOW}Press Enter to start the tribunal...{Colors.END}\n")

    # Run debate with live output
    orchestrator = DebateOrchestrator(api_key=api_key, dev_mode=True)

    # Round 1
    print_agent("PROSECUTOR", Colors.RED, "Analyzing claim for mutations...")
    prosecution = orchestrator.run_prosecution(case['claim'], case['truth'])
    print()
    for acc in prosecution.get('accusations', [])[:3]:
        print(f"  🔴 {acc.get('type', 'unknown')}: {acc.get('explanation', '')[:80]}...")
    print(f"  {Colors.RED}Prosecution confidence: {prosecution.get('confidence', 0):.0%}{Colors.END}")

    input(f"\n{Colors.YELLOW}Press Enter for defense...{Colors.END}\n")

    # Round 2
    print_agent("DEFENSE", Colors.GREEN, "Preparing rebuttals...")
    defense = orchestrator.run_defense(case['claim'], case['truth'], prosecution)
    print()
    for reb in defense.get('rebuttals', [])[:3]:
        print(f"  🟢 {reb.get('counter_argument', '')[:80]}...")
    print(f"  {Colors.GREEN}Defense confidence: {defense.get('confidence', 0):.0%}{Colors.END}")

    input(f"\n{Colors.YELLOW}Press Enter for uncertainty analysis...{Colors.END}\n")

    # Round 3
    print_agent("EPISTEMOLOGIST", Colors.YELLOW, "Quantifying uncertainty...")
    epistemology = orchestrator.run_epistemologist(case['claim'], case['truth'], prosecution, defense)
    print()
    print(f"  🟡 Key uncertainty: {epistemology.get('key_uncertainty', 'N/A')[:80]}...")
    print(f"  🟡 Verdict recommendation: {epistemology.get('verdict_recommendation', 'N/A')}")

    input(f"\n{Colors.YELLOW}Press Enter for final verdict...{Colors.END}\n")

    # Round 4
    print_agent("JURY FOREMAN", Colors.MAGENTA, "Deliberating...")
    verdict = orchestrator.run_jury_foreman(case['claim'], case['truth'], prosecution, defense, epistemology)

    print_header("FINAL VERDICT")

    verdict_value = verdict.get('verdict', 'ambiguous')
    confidence = verdict.get('confidence', 0)

    if verdict_value == 'faithful':
        print(f"{Colors.GREEN}{Colors.BOLD}✅ FAITHFUL{Colors.END}")
    elif verdict_value == 'mutated':
        print(f"{Colors.RED}{Colors.BOLD}❌ MUTATED{Colors.END}")
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠️ AMBIGUOUS{Colors.END}")

    print(f"\nConfidence: {confidence:.0%}")
    print(f"\nReasoning: {verdict.get('summary', 'No summary')}")

    if verdict.get('reasoning', {}).get('mutation_types_identified'):
        print(f"\nMutation types: {', '.join(verdict['reasoning']['mutation_types_identified'])}")

    # Compare with expected
    if selected_case_id in STRATEGIC_CASES:
        expected = STRATEGIC_CASES[selected_case_id]['expected']
        match = "✅" if expected == verdict_value else "⚠️"
        print(f"\nExpected: {expected} | Actual: {verdict_value} {match}")

    print_header("WHY MULTI-AGENT DEBATE WORKS")
    print("""
    1. ADVERSARIAL DESIGN forces consideration of both interpretations
    2. EXPLICIT UNCERTAINTY prevents overconfident verdicts
    3. TRANSPARENT REASONING enables human oversight
    4. CALIBRATED OUTPUT acknowledges genuine ambiguity

    Single-model approach would miss nuances that emerge from debate!
    """)

    print_header("THANK YOU - KEPLER TEAM")


if __name__ == "__main__":
    run_demo()
