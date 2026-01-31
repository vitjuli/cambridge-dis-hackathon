"""
Run debates and export results to JSON
Simple script to generate comprehensive JSON output of all agent debates
"""

import os
from agents import DebateOrchestrator
from visualize import export_results_json
import csv


def load_kepler_data(filepath: str = "Kepler.csv") -> list[dict]:
    """Load claim-truth pairs from Kepler.csv"""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if row['claim'] and row['truth']:
                data.append({
                    'id': idx,
                    'claim': row['claim'].strip(),
                    'truth': row['truth'].strip()
                })
    return data


def run_and_export_debates(
    api_key: str,
    case_indices: list[int] = None,
    output_file: str = "debate_results.json"
):
    """Run debates and export to JSON."""
    
    # Load data
    data = load_kepler_data()
    print(f"📚 Loaded {len(data)} claim-truth pairs from Kepler.csv")
    
    # Use strategic cases if none specified
    if case_indices is None:
        case_indices = [0, 1, 5, 6, 7]  # Strategic selection
    
    # Filter to valid indices
    case_indices = [i for i in case_indices if i < len(data)]
    selected_cases = [data[i] for i in case_indices]
    
    print(f"\n🎯 Analyzing {len(selected_cases)} cases: {case_indices}")
    
    # Initialize orchestrator
    orchestrator = DebateOrchestrator(api_key=api_key, dev_mode=True)
    
    # Run debates
    results = []
    for case in selected_cases:
        print(f"\n{'='*70}")
        print(f"⚖️  CASE {case['id']}")
        print(f"{'='*70}")
        
        result = orchestrator.run_full_debate(case['claim'], case['truth'])
        results.append(result)
    
    # Export to JSON
    print(f"\n{'='*70}")
    print("💾 Exporting results to JSON...")
    export_results_json(results, output_file)
    
    print(f"\n✅ Complete! {len(results)} debates exported to {output_file}")
    print(f"📄 JSON file ready for visualization or further analysis")
    
    return results


if __name__ == "__main__":
    # Get API key from environment
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: Set OPENAI_API_KEY environment variable")
        exit(1)
    
    # Run debates and export
    run_and_export_debates(
        api_key=api_key,
        case_indices=[0, 1, 5, 6, 7],  # Customize as needed
        output_file="debate_results.json"
    )
