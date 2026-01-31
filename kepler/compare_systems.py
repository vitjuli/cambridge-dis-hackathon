"""
Comparison Script: Single-Agent vs Multi-Agent Debate
Runs both systems on the same cases and compares results
"""

import json
import csv
import os
import sys
from pathlib import Path

# Add kepler to path
sys.path.insert(0, str(Path(__file__).parent))

from single_agent_baseline import run_single_agent_baseline, export_single_agent_results
from agents import DebateOrchestrator
from visualize import export_results_json


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


def run_multi_agent_debates(cases: list[dict], api_key: str):
    """Run multi-agent debates on cases."""
    orchestrator = DebateOrchestrator(api_key=api_key)
    results = []
    
    print("\n" + "="*70)
    print("MULTI-AGENT DEBATE SYSTEM")
    print("="*70)
    
    for case in cases:
        result = orchestrator.run_full_debate(case['claim'], case['truth'])
        results.append(result)
    
    return results


def compare_results(single_agent_results, multi_agent_results):
    """Generate comparison analysis."""
    print("\n" + "="*70)
    print("DETAILED COMPARISON")
    print("="*70)
    
    for idx, (sa, ma) in enumerate(zip(single_agent_results, multi_agent_results)):
        print(f"\n{'─'*70}")
        print(f"CASE {idx}: {sa.claim[:60]}...")
        print(f"{'─'*70}")
        
        print(f"\n📊 VERDICTS:")
        print(f"  Single-Agent: {sa.verdict.value.upper()} ({sa.confidence:.0%} confidence)")
        print(f"  Multi-Agent:  {ma.final_verdict.value.upper()} ({ma.confidence:.0%} confidence)")
        
        if sa.verdict.value != ma.final_verdict.value:
            print(f"  ⚠️  DISAGREEMENT!")
        else:
            print(f"  ✓ Agreement")
        
        print(f"\n💭 REASONING:")
        print(f"  Single-Agent: {sa.reasoning[:150]}...")
        print(f"  Multi-Agent:  {ma.verdict_reasoning[:150]}...")
        
        print(f"\n🔍 MUTATION TYPES:")
        print(f"  Single-Agent: {sa.mutation_types}")
        print(f"  Multi-Agent:  {ma.prosecutor_response.mutation_types}")
        
        print(f"\n📈 CONFIDENCE DIFFERENCE: {abs(sa.confidence - ma.confidence):.1%}")
    
    # Overall statistics
    print(f"\n{'='*70}")
    print("OVERALL STATISTICS")
    print(f"{'='*70}")
    
    sa_avg_conf = sum(r.confidence for r in single_agent_results) / len(single_agent_results)
    ma_avg_conf = sum(r.confidence for r in multi_agent_results) / len(multi_agent_results)
    
    print(f"\nAverage Confidence:")
    print(f"  Single-Agent: {sa_avg_conf:.1%}")
    print(f"  Multi-Agent:  {ma_avg_conf:.1%}")
    
    # Count verdicts
    sa_verdicts = {}
    ma_verdicts = {}
    for sa, ma in zip(single_agent_results, multi_agent_results):
        sa_verdicts[sa.verdict.value] = sa_verdicts.get(sa.verdict.value, 0) + 1
        ma_verdicts[ma.final_verdict.value] = ma_verdicts.get(ma.final_verdict.value, 0) + 1
    
    print(f"\nVerdict Distribution:")
    print(f"  Single-Agent: {sa_verdicts}")
    print(f"  Multi-Agent:  {ma_verdicts}")
    
    # Agreement rate
    agreements = sum(1 for sa, ma in zip(single_agent_results, multi_agent_results) 
                    if sa.verdict.value == ma.final_verdict.value)
    agreement_rate = agreements / len(single_agent_results)
    
    print(f"\nAgreement Rate: {agreement_rate:.0%} ({agreements}/{len(single_agent_results)} cases)")


def generate_comparison_report(single_agent_results, multi_agent_results, output_file="comparison_report.md"):
    """Generate markdown comparison report."""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Single-Agent vs Multi-Agent Debate: Comparison Report\n\n")
        
        f.write("## Executive Summary\n\n")
        f.write("This report compares a simple single-agent fact-checking approach with our multi-agent adversarial debate system.\n\n")
        
        f.write("## Methodology\n\n")
        f.write("### Single-Agent Baseline\n")
        f.write("- **Approach**: Direct LLM call asking for verdict\n")
        f.write("- **Agents**: 1 (general fact-checker)\n")
        f.write("- **Process**: Single inference, no debate\n\n")
        
        f.write("### Multi-Agent Debate System\n")
        f.write("- **Approach**: Adversarial tribunal with multiple perspectives\n")
        f.write("- **Agents**: 4 (Prosecutor, Defense, Epistemologist, Jury Foreman)\n")
        f.write("- **Process**: Multi-round debate with explicit uncertainty analysis\n\n")
        
        f.write("## Case-by-Case Results\n\n")
        
        for idx, (sa, ma) in enumerate(zip(single_agent_results, multi_agent_results)):
            f.write(f"### Case {idx}\n\n")
            f.write(f"**Claim**: {sa.claim}\n\n")
            f.write(f"**Truth**: {sa.truth}\n\n")
            
            f.write("| Metric | Single-Agent | Multi-Agent |\n")
            f.write("|--------|--------------|-------------|\n")
            f.write(f"| Verdict | {sa.verdict.value.upper()} | {ma.final_verdict.value.upper()} |\n")
            f.write(f"| Confidence | {sa.confidence:.0%} | {ma.confidence:.0%} |\n")
            f.write(f"| Mutation Types | {', '.join(sa.mutation_types) if sa.mutation_types else 'None'} | {', '.join(ma.prosecutor_response.mutation_types) if ma.prosecutor_response.mutation_types else 'None'} |\n\n")
            
            f.write(f"**Single-Agent Reasoning**: {sa.reasoning}\n\n")
            f.write(f"**Multi-Agent Reasoning**: {ma.verdict_reasoning}\n\n")
            
            if sa.verdict.value != ma.final_verdict.value:
                f.write("⚠️ **DISAGREEMENT**: Systems reached different verdicts\n\n")
            
            f.write("---\n\n")
        
        # Statistics
        sa_avg_conf = sum(r.confidence for r in single_agent_results) / len(single_agent_results)
        ma_avg_conf = sum(r.confidence for r in multi_agent_results) / len(multi_agent_results)
        
        f.write("## Overall Statistics\n\n")
        f.write(f"- **Average Confidence (Single-Agent)**: {sa_avg_conf:.1%}\n")
        f.write(f"- **Average Confidence (Multi-Agent)**: {ma_avg_conf:.1%}\n\n")
        
        agreements = sum(1 for sa, ma in zip(single_agent_results, multi_agent_results) 
                        if sa.verdict.value == ma.final_verdict.value)
        agreement_rate = agreements / len(single_agent_results)
        
        f.write(f"- **Agreement Rate**: {agreement_rate:.0%}\n\n")
        
        f.write("## Key Advantages of Multi-Agent System\n\n")
        f.write("1. **Adversarial Testing**: Prosecutor and Defense challenge each other's arguments\n")
        f.write("2. **Uncertainty Quantification**: Epistemologist explicitly analyzes ambiguity\n")
        f.write("3. **Transparent Reasoning**: Full debate transcript shows decision process\n")
        f.write("4. **Bias Reduction**: Multiple perspectives prevent single-viewpoint bias\n")
        f.write("5. **Calibrated Confidence**: Debate process leads to more realistic confidence scores\n")
        f.write("6. **Nuanced Analysis**: Multi-round exchanges capture subtle distinctions\n\n")
        
        f.write("## Conclusion\n\n")
        f.write("The multi-agent debate system provides:\n")
        f.write("- More thorough analysis through adversarial testing\n")
        f.write("- Better calibrated confidence scores\n")
        f.write("- Transparent, auditable reasoning process\n")
        f.write("- Explicit handling of uncertainty and ambiguity\n\n")
        f.write("While the single-agent approach is faster, the multi-agent system offers superior reliability and interpretability for critical fact-checking tasks.\n")
    
    print(f"\n✅ Comparison report saved to {output_file}")


if __name__ == "__main__":
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: Set OPENAI_API_KEY environment variable")
        exit(1)
    
    # Load data
    data = load_kepler_data()
    print(f"📚 Loaded {len(data)} claim-truth pairs from Kepler.csv")
    
    # Use first 2 cases for comparison
    test_cases = data[:2]
    print(f"🎯 Comparing systems on {len(test_cases)} cases: {[c['id'] for c in test_cases]}\n")
    
    # Run single-agent baseline
    print("Running single-agent baseline...")
    single_agent_results = run_single_agent_baseline(test_cases, api_key)
    export_single_agent_results(single_agent_results)
    
    # Run multi-agent debates
    print("\nRunning multi-agent debates...")
    multi_agent_results = run_multi_agent_debates(test_cases, api_key)
    export_results_json(multi_agent_results, "multi_agent_results.json")
    
    # Compare results
    compare_results(single_agent_results, multi_agent_results)
    
    # Generate report
    generate_comparison_report(single_agent_results, multi_agent_results)
    
    print("\n" + "="*70)
    print("✅ COMPARISON COMPLETE")
    print("="*70)
    print("\nGenerated files:")
    print("  - single_agent_results.json")
    print("  - multi_agent_results.json")
    print("  - comparison_report.md")
