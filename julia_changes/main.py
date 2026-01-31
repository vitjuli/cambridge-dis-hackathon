"""
Kepler Team - Cambridge DIS Hackathon
Multi-Agent Fact Verification System

Usage:
    python main.py                    # Run with default strategic cases
    python main.py --all              # Run all cases (expensive!)
    python main.py --cases 1,3,7      # Run specific case indices
    python main.py --interactive      # Interactive case selection
    python main.py --presentation     # Presentation mode (uses gpt-4o)
"""

import os
import csv
import argparse
from typing import Optional
from agents import DebateOrchestrator, format_debate_for_presentation, DebateResult


# =============================================================================
# DATA LOADING
# =============================================================================

def load_kepler_data(filepath: str = "Kepler.csv") -> list[dict]:
    """Load claim-truth pairs from Kepler.csv"""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if row['claim'] and row['truth']:  # Skip empty rows
                data.append({
                    'id': idx,
                    'claim': row['claim'].strip(),
                    'truth': row['truth'].strip()
                })
    return data


def display_cases(data: list[dict]) -> None:
    """Display all available cases for selection."""
    print("\n" + "="*70)
    print("AVAILABLE CASES")
    print("="*70)
    for case in data:
        print(f"\n[Case {case['id']}]")
        print(f"  CLAIM: {case['claim'][:80]}...")
        print(f"  TRUTH: {case['truth'][:80]}...")
    print("\n" + "="*70)


# =============================================================================
# STRATEGIC CASE SELECTION
# =============================================================================

# Pre-analyzed strategic subset showcasing different mutation types
STRATEGIC_CASES = {
    # Case 0: Numerical boundary manipulation ("less than 14,550" vs "more than 14,500")
    0: {
        "rationale": "Subtle numerical boundary shift - tests precision detection",
        "expected": "mutated",
        "mutation_type": "numerical_distortion"
    },
    # Case 1: Added specificity not in source ("more than 1,000 motorists")
    1: {
        "rationale": "Claim adds specific number not present in source",
        "expected": "mutated",
        "mutation_type": "added_information"
    },
    # Case 5: Negation framing ("failed to sell" vs factual statement)
    5: {
        "rationale": "Negation framing of same underlying fact",
        "expected": "ambiguous",
        "mutation_type": "negation_framing"
    },
    # Case 7: Minor numerical difference (359,000 vs 360,000)
    7: {
        "rationale": "Borderline acceptable rounding - tests judgment",
        "expected": "ambiguous",
        "mutation_type": "numerical_distortion"
    },
    # Case 6: Clear faithful representation (License to Kill)
    6: {
        "rationale": "Accurate extraction from source - should be faithful",
        "expected": "faithful",
        "mutation_type": None
    },
}


def get_strategic_analysis() -> str:
    """Return analysis of strategic case selection for presentation."""
    analysis = """
STRATEGIC CASE SELECTION RATIONALE
==================================

We selected 5 cases that demonstrate the full spectrum of claim verification challenges:

1. CLEAR MUTATION (Case 0 - COVID Deaths)
   - Claim: "Less than 14,550 people have died"
   - Truth: "more than 14,500 deaths"
   - Why selected: Tests detection of subtle numerical boundary manipulation

2. ADDED INFORMATION (Case 1 - Michigan Protest)
   - Claim: "more than 1,000 motorists"
   - Truth: "a convoy of motorists" (no number specified)
   - Why selected: Tests detection of fabricated specificity

3. NEGATION FRAMING (Case 5 - Dave Matthews Band)
   - Claim: "failed to sell more than 30 million"
   - Truth: "did not sold over 30 million"
   - Why selected: Same fact, different framing - tests semantic analysis

4. BORDERLINE CASE (Case 7 - COVID Cases)
   - Claim: "more than 359,000 cases"
   - Truth: "more than 360,000 cases"
   - Why selected: Tests threshold for acceptable rounding

5. FAITHFUL BASELINE (Case 6 - License to Kill)
   - Claim accurately extracts information from source
   - Why selected: Ensures system doesn't over-flag mutations

This selection demonstrates our system handles:
✓ Numerical precision
✓ Information addition
✓ Semantic framing
✓ Edge cases
✓ True positives AND true negatives
"""
    return analysis


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def run_hackathon(
    api_key: str,
    cases: Optional[list[int]] = None,
    presentation_mode: bool = False,
    interactive: bool = False
) -> list[DebateResult]:
    """Run the fact verification tribunal."""

    # Load data
    data = load_kepler_data()
    print(f"Loaded {len(data)} claim-truth pairs from Kepler.csv")

    # Case selection
    if interactive:
        display_cases(data)
        case_input = input("\nEnter case numbers to analyze (comma-separated): ")
        selected_indices = [int(x.strip()) for x in case_input.split(",")]
    elif cases is not None:
        selected_indices = cases
    else:
        # Use strategic selection
        selected_indices = list(STRATEGIC_CASES.keys())
        print("\nUsing strategic case selection:")
        print(get_strategic_analysis())

    # Filter to valid indices
    selected_indices = [i for i in selected_indices if i < len(data)]
    selected_cases = [data[i] for i in selected_indices]

    print(f"\nAnalyzing {len(selected_cases)} cases...")

    # Initialize orchestrator
    orchestrator = DebateOrchestrator(
        api_key=api_key,
        dev_mode=not presentation_mode
    )

    model_name = "gpt-4o" if presentation_mode else "gpt-4o-mini"
    print(f"Using model: {model_name}")

    # Run debates
    results = []
    for case in selected_cases:
        print(f"\n{'#'*70}")
        print(f"CASE {case['id']}")
        print(f"{'#'*70}")

        if case['id'] in STRATEGIC_CASES:
            meta = STRATEGIC_CASES[case['id']]
            print(f"Strategic rationale: {meta['rationale']}")
            print(f"Expected verdict: {meta['expected']}")

        result = orchestrator.run_full_debate(case['claim'], case['truth'])
        results.append(result)

        # Print formatted result
        print(format_debate_for_presentation(result))

        # Compare with expected if available
        if case['id'] in STRATEGIC_CASES:
            expected = STRATEGIC_CASES[case['id']]['expected']
            actual = result.final_verdict.value
            match = "✅ MATCH" if expected == actual else "⚠️ DIFFERS"
            print(f"\nExpected: {expected}, Got: {actual} {match}")

    return results


def generate_presentation_summary(results: list[DebateResult]) -> str:
    """Generate summary for 5-minute presentation."""
    summary = []
    summary.append("\n" + "="*70)
    summary.append("PRESENTATION SUMMARY - KEPLER TEAM")
    summary.append("="*70)

    summary.append("\n## APPROACH: ADVERSARIAL TRIBUNAL")
    summary.append("""
Our system uses 4 specialized agents in a courtroom-style debate:
1. PROSECUTOR - Aggressively hunts for mutations
2. DEFENSE - Argues for faithful interpretation
3. EPISTEMOLOGIST - Quantifies uncertainty
4. JURY FOREMAN - Synthesizes final verdict
""")

    summary.append("\n## RESULTS SUMMARY")
    summary.append("-"*40)

    verdicts = {"faithful": 0, "mutated": 0, "ambiguous": 0}
    for r in results:
        verdicts[r.final_verdict.value] += 1

    summary.append(f"Total cases analyzed: {len(results)}")
    summary.append(f"  ✅ Faithful: {verdicts['faithful']}")
    summary.append(f"  ❌ Mutated: {verdicts['mutated']}")
    summary.append(f"  ⚠️ Ambiguous: {verdicts['ambiguous']}")

    avg_confidence = sum(r.confidence for r in results) / len(results) if results else 0
    summary.append(f"  Average confidence: {avg_confidence:.0%}")

    summary.append("\n## KEY FINDINGS")
    summary.append("-"*40)

    for r in results:
        emoji = {"faithful": "✅", "mutated": "❌", "ambiguous": "⚠️"}[r.final_verdict.value]
        summary.append(f"\n{emoji} {r.final_verdict.value.upper()} ({r.confidence:.0%})")
        summary.append(f"   Claim: {r.claim[:60]}...")
        summary.append(f"   Reason: {r.verdict_reasoning[:100]}...")

    summary.append("\n## WHY MULTI-AGENT DEBATE WORKS")
    summary.append("-"*40)
    summary.append("""
1. ADVERSARIAL DESIGN forces consideration of both interpretations
2. EXPLICIT UNCERTAINTY via Epistemologist prevents overconfidence
3. TRANSPARENT REASONING via debate transcript enables human oversight
4. CALIBRATED VERDICTS - ambiguous when evidence is genuinely mixed
""")

    return "\n".join(summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kepler Team Fact Verification System")
    parser.add_argument("--all", action="store_true", help="Run all cases")
    parser.add_argument("--cases", type=str, help="Comma-separated case indices")
    parser.add_argument("--interactive", action="store_true", help="Interactive case selection")
    parser.add_argument("--presentation", action="store_true", help="Use gpt-4o for presentation")
    parser.add_argument("--api-key", type=str, help="OpenAI API key (or set OPENAI_API_KEY env var)")

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: No API key provided. Set OPENAI_API_KEY or use --api-key")
        exit(1)

    # Determine cases to run
    cases = None
    if args.all:
        cases = list(range(20))  # All cases
    elif args.cases:
        cases = [int(x.strip()) for x in args.cases.split(",")]

    # Run
    results = run_hackathon(
        api_key=api_key,
        cases=cases,
        presentation_mode=args.presentation,
        interactive=args.interactive
    )

    # Generate presentation summary
    print(generate_presentation_summary(results))
