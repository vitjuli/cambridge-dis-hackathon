#!/usr/bin/env python3
"""
Kepler Team - Cambridge DIS Hackathon
Multi-Agent Debate Runner

Usage:
    python run_debate.py                     # Run strategic cases with gpt-4o-mini
    python run_debate.py --case 0            # Run single case
    python run_debate.py --cases 0,1,5       # Run specific cases
    python run_debate.py --presentation      # Use gpt-4o for final demo
    python run_debate.py --output results.json  # Custom output file
"""

import os
import csv
import argparse
from debate_engine import DebateEngine, save_all_transcripts, Colors


# Strategic cases showcasing different mutation types
STRATEGIC_CASES = [0, 1, 5, 6, 7]

CASE_DESCRIPTIONS = {
    0: "Numerical boundary: 'less than 14,550' vs 'more than 14,500'",
    1: "Added information: '1,000 motorists' not in source",
    5: "Negation framing: 'failed to sell' vs neutral",
    6: "Faithful baseline: accurate extraction",
    7: "Borderline: 359k vs 360k",
}


def load_data(filepath: str = "Kepler.csv") -> list[dict]:
    """Load claim-truth pairs."""
    data = []
    # Try multiple paths
    paths_to_try = [
        filepath,
        os.path.join(os.path.dirname(__file__), "..", "Kepler.csv"),
        os.path.join(os.path.dirname(__file__), "Kepler.csv"),
        "../Kepler.csv",
    ]

    for path in paths_to_try:
        if os.path.exists(path):
            filepath = path
            break

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if row.get('claim') and row.get('truth'):
                data.append({
                    'id': idx,
                    'claim': row['claim'].strip(),
                    'truth': row['truth'].strip()
                })
    return data


def main():
    parser = argparse.ArgumentParser(description="Run multi-agent fact verification debate")
    parser.add_argument("--case", type=int, help="Single case index to run")
    parser.add_argument("--cases", type=str, help="Comma-separated case indices")
    parser.add_argument("--all", action="store_true", help="Run all cases")
    parser.add_argument("--presentation", action="store_true", help="Use gpt-4o for presentation")
    parser.add_argument("--output", type=str, default="debate_transcript.json", help="Output JSON file")
    parser.add_argument("--api-key", type=str, help="OpenAI API key")

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print(f"{Colors.RED}ERROR: Set OPENAI_API_KEY or use --api-key{Colors.END}")
        return 1

    # Load data
    data = load_data()
    print(f"Loaded {len(data)} cases from Kepler.csv")

    # Determine which cases to run
    if args.case is not None:
        case_indices = [args.case]
    elif args.cases:
        case_indices = [int(x.strip()) for x in args.cases.split(",")]
    elif args.all:
        case_indices = list(range(len(data)))
    else:
        case_indices = STRATEGIC_CASES
        print(f"\n{Colors.CYAN}Using strategic case selection:{Colors.END}")
        for idx in case_indices:
            desc = CASE_DESCRIPTIONS.get(idx, "")
            print(f"  Case {idx}: {desc}")

    # Filter valid indices
    case_indices = [i for i in case_indices if i < len(data)]

    # Initialize engine
    model = "gpt-4o" if args.presentation else "gpt-4o-mini"
    print(f"\n{Colors.BOLD}Model: {model}{Colors.END}")
    print(f"Cases to analyze: {case_indices}\n")

    engine = DebateEngine(api_key=api_key, model=model)

    # Run debates
    transcripts = []
    for idx in case_indices:
        case = data[idx]

        if idx in CASE_DESCRIPTIONS:
            print(f"\n{Colors.YELLOW}Case description: {CASE_DESCRIPTIONS[idx]}{Colors.END}")

        transcript = engine.run_debate(
            case_id=case['id'],
            claim=case['claim'],
            truth=case['truth']
        )
        transcripts.append(transcript)

    # Save all transcripts
    save_all_transcripts(transcripts, args.output)

    # Print summary
    print(f"\n{Colors.BOLD}{'='*72}")
    print(f"{'SUMMARY':^72}")
    print(f"{'='*72}{Colors.END}\n")

    for t in transcripts:
        verdict = t.round3_consensus.final_verdict.value
        conf = t.round3_consensus.confidence
        emoji = {"faithful": "✅", "mutated": "❌", "uncertain": "⚠️"}[verdict]
        print(f"Case {t.case_id}: {emoji} {verdict.upper()} ({conf:.0%})")
        print(f"  {Colors.DIM}{t.claim[:60]}...{Colors.END}")

    return 0


if __name__ == "__main__":
    exit(main())
