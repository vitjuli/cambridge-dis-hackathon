"""
Export comparison data for v0 visualization
Creates a comprehensive JSON file with both single-agent and multi-agent results
"""

import json
import csv
import os
from pathlib import Path
from single_agent_baseline import SingleAgentVerifier
from agents import DebateOrchestrator


def load_kepler_data(filepath: str = "Kepler.csv", limit: int = None) -> list[dict]:
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
            if limit and len(data) >= limit:
                break
    return data


def export_for_visualization(num_cases: int = 5):
    """Export comparison data formatted for v0 visualization."""
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: Set OPENAI_API_KEY environment variable")
        return
    
    # Load data
    data = load_kepler_data(limit=num_cases)
    print(f"📚 Loaded {len(data)} cases for comparison\n")
    
    # Initialize both systems
    single_agent = SingleAgentVerifier(api_key)
    multi_agent = DebateOrchestrator(api_key)
    
    comparison_data = {
        "metadata": {
            "total_cases": len(data),
            "systems": ["single_agent", "multi_agent"],
            "description": "Comparison of single-agent baseline vs multi-agent debate ensemble"
        },
        "cases": []
    }
    
    for idx, case in enumerate(data):
        print(f"\n{'='*70}")
        print(f"Processing Case {idx}: {case['claim'][:60]}...")
        print(f"{'='*70}")
        
        # Run single-agent
        print("  Running single-agent...")
        sa_result = single_agent.verify_claim(case['claim'], case['truth'])
        
        # Run multi-agent
        print("  Running multi-agent debate...")
        ma_result = multi_agent.run_full_debate(case['claim'], case['truth'])
        
        # Format for visualization
        case_data = {
            "case_id": idx,
            "claim": case['claim'],
            "truth": case['truth'],
            "single_agent": {
                "verdict": sa_result.verdict.value,
                "confidence": round(sa_result.confidence * 100, 1),
                "reasoning": sa_result.reasoning,
                "mutation_types": sa_result.mutation_types,
                "process_time": "~5s",
                "llm_calls": 1
            },
            "multi_agent": {
                "verdict": ma_result.final_verdict.value,
                "confidence": round(ma_result.confidence * 100, 1),
                "reasoning": ma_result.verdict_reasoning,
                "mutation_types": ma_result.prosecutor_response.mutation_types,
                "process_time": "~30s",
                "llm_calls": len(ma_result.debate_transcript),
                "agents": {
                    "prosecutor": {
                        "arguments": ma_result.prosecutor_response.arguments,
                        "confidence": round(ma_result.prosecutor_response.confidence * 100, 1)
                    },
                    "defense": {
                        "arguments": ma_result.defense_response.arguments,
                        "confidence": round(ma_result.defense_response.confidence * 100, 1)
                    },
                    "epistemologist": {
                        "key_uncertainty": ma_result.epistemologist_response.arguments[0] if ma_result.epistemologist_response.arguments else "",
                        "confidence": round(ma_result.epistemologist_response.confidence * 100, 1)
                    }
                }
            },
            "comparison": {
                "verdict_match": sa_result.verdict.value == ma_result.final_verdict.value,
                "confidence_diff": abs(round((sa_result.confidence - ma_result.confidence) * 100, 1)),
                "mutation_types_match": set(sa_result.mutation_types) == set(ma_result.prosecutor_response.mutation_types or [])
            }
        }
        
        comparison_data["cases"].append(case_data)
        
        print(f"  ✓ Single-Agent: {sa_result.verdict.value.upper()} ({sa_result.confidence:.0%})")
        print(f"  ✓ Multi-Agent:  {ma_result.final_verdict.value.upper()} ({ma_result.confidence:.0%})")
    
    # Calculate overall statistics
    total_cases = len(comparison_data["cases"])
    verdict_matches = sum(1 for c in comparison_data["cases"] if c["comparison"]["verdict_match"])
    avg_sa_conf = sum(c["single_agent"]["confidence"] for c in comparison_data["cases"]) / total_cases
    avg_ma_conf = sum(c["multi_agent"]["confidence"] for c in comparison_data["cases"]) / total_cases
    
    comparison_data["statistics"] = {
        "verdict_agreement_rate": round(verdict_matches / total_cases * 100, 1),
        "average_confidence": {
            "single_agent": round(avg_sa_conf, 1),
            "multi_agent": round(avg_ma_conf, 1)
        },
        "verdict_distribution": {
            "single_agent": {
                "faithful": sum(1 for c in comparison_data["cases"] if c["single_agent"]["verdict"] == "faithful"),
                "mutated": sum(1 for c in comparison_data["cases"] if c["single_agent"]["verdict"] == "mutated"),
                "ambiguous": sum(1 for c in comparison_data["cases"] if c["single_agent"]["verdict"] == "ambiguous")
            },
            "multi_agent": {
                "faithful": sum(1 for c in comparison_data["cases"] if c["multi_agent"]["verdict"] == "faithful"),
                "mutated": sum(1 for c in comparison_data["cases"] if c["multi_agent"]["verdict"] == "mutated"),
                "ambiguous": sum(1 for c in comparison_data["cases"] if c["multi_agent"]["verdict"] == "ambiguous")
            }
        }
    }
    
    # Export
    output_file = "visualization_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comparison_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*70}")
    print(f"✅ Comparison data exported to {output_file}")
    print(f"{'='*70}")
    print(f"\nStatistics:")
    print(f"  Total cases: {total_cases}")
    print(f"  Verdict agreement: {comparison_data['statistics']['verdict_agreement_rate']}%")
    print(f"  Avg confidence (SA): {avg_sa_conf:.1f}%")
    print(f"  Avg confidence (MA): {avg_ma_conf:.1f}%")
    
    return output_file


if __name__ == "__main__":
    import sys
    
    num_cases = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"🎯 Generating comparison data for {num_cases} cases\n")
    
    export_for_visualization(num_cases)
