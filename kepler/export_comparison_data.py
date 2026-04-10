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
            "systems": ["single_agent", "multi_agent_standard", "multi_agent_forced"],
            "description": "Three-way comparison: Single-agent vs Multi-agent (allows ambiguous) vs Multi-agent (forced binary)"
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
        
        # Run multi-agent (standard - allows ambiguous)
        print("  Running multi-agent debate (standard)...")
        ma_result_standard = multi_agent.run_full_debate(case['claim'], case['truth'])
        
        # Run multi-agent (forced binary - no ambiguous allowed)
        print("  Running multi-agent debate (forced binary)...")
        ma_result_forced = multi_agent.run_full_debate(case['claim'], case['truth'], force_binary_if_ambiguous=True)
        
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
            "multi_agent_standard": {
                "verdict": ma_result_standard.final_verdict.value,
                "confidence": round(ma_result_standard.confidence * 100, 1),
                "reasoning": ma_result_standard.verdict_reasoning,
                "mutation_types": ma_result_standard.prosecutor_response.mutation_types,
                "process_time": "~30s",
                "llm_calls": len(ma_result_standard.debate_transcript),
                "agents": {
                    "prosecutor": {
                        "all_rounds": [
                            {
                                "round": i + 1,
                                "arguments": [acc.get("explanation", "") for acc in resp.get("accusations", [])],
                                "confidence": round(resp.get("confidence", 0) * 100, 1)
                            }
                            for i, resp in enumerate(ma_result_standard.all_prosecutor_responses or [])
                        ],
                        "final_arguments": ma_result_standard.prosecutor_response.arguments,
                        "final_confidence": round(ma_result_standard.prosecutor_response.confidence * 100, 1)
                    },
                    "defense": {
                        "all_rounds": [
                            {
                                "round": i + 1,
                                "arguments": [reb.get("counter_argument", "") for reb in resp.get("rebuttals", [])],
                                "confidence": round(resp.get("confidence", 0) * 100, 1)
                            }
                            for i, resp in enumerate(ma_result_standard.all_defense_responses or [])
                        ],
                        "final_arguments": ma_result_standard.defense_response.arguments,
                        "final_confidence": round(ma_result_standard.defense_response.confidence * 100, 1)
                    },
                    "epistemologist": {
                        "all_rounds": [
                            {
                                "round": i + 1,
                                "key_uncertainty": resp.get("key_uncertainty", ""),
                                "verifiable_facts": resp.get("verifiable_facts", []),
                                "confidence": round(resp.get("recommended_confidence_range", [0, 0])[-1] * 100, 1)
                            }
                            for i, resp in enumerate(ma_result_standard.all_epistemologist_responses or [])
                        ],
                        "final_uncertainty": ma_result_standard.epistemologist_response.arguments[0] if ma_result_standard.epistemologist_response.arguments else "",
                        "final_confidence": round(ma_result_standard.epistemologist_response.confidence * 100, 1)
                    }
                }
            },
            "multi_agent_forced": {
                "verdict": ma_result_forced.final_verdict.value,
                "confidence": round(ma_result_forced.confidence * 100, 1),
                "reasoning": ma_result_forced.verdict_reasoning,
                "mutation_types": ma_result_forced.prosecutor_response.mutation_types,
                "process_time": "~30s",
                "llm_calls": len(ma_result_forced.debate_transcript),
                "forced_binary_used": ma_result_forced.forced_binary_used,
                "initial_verdict": ma_result_forced.initial_verdict.value if ma_result_forced.initial_verdict else None,
            },
            "comparison": {
                "sa_vs_ma_standard": sa_result.verdict.value == ma_result_standard.final_verdict.value,
                "sa_vs_ma_forced": sa_result.verdict.value == ma_result_forced.final_verdict.value,
                "ma_standard_vs_forced": ma_result_standard.final_verdict.value == ma_result_forced.final_verdict.value,
                "forced_changed_verdict": ma_result_forced.forced_binary_used and (ma_result_forced.initial_verdict.value != ma_result_forced.final_verdict.value)
            }
        }
        
        comparison_data["cases"].append(case_data)
        
        print(f"  ✓ Single-Agent:          {sa_result.verdict.value.upper()} ({sa_result.confidence:.0%})")
        print(f"  ✓ Multi-Agent (Standard): {ma_result_standard.final_verdict.value.upper()} ({ma_result_standard.confidence:.0%})")
        print(f"  ✓ Multi-Agent (Forced):   {ma_result_forced.final_verdict.value.upper()} ({ma_result_forced.confidence:.0%})")
        if ma_result_forced.forced_binary_used:
            print(f"    → Forced from: {ma_result_forced.initial_verdict.value.upper()}")
    
    # Calculate overall statistics
    total_cases = len(comparison_data["cases"])
    avg_sa_conf = sum(c["single_agent"]["confidence"] for c in comparison_data["cases"]) / total_cases
    avg_ma_standard_conf = sum(c["multi_agent_standard"]["confidence"] for c in comparison_data["cases"]) / total_cases
    avg_ma_forced_conf = sum(c["multi_agent_forced"]["confidence"] for c in comparison_data["cases"]) / total_cases
    
    comparison_data["statistics"] = {
        "average_confidence": {
            "single_agent": round(avg_sa_conf, 1),
            "multi_agent_standard": round(avg_ma_standard_conf, 1),
            "multi_agent_forced": round(avg_ma_forced_conf, 1)
        },
        "verdict_distribution": {
            "single_agent": {
                "faithful": sum(1 for c in comparison_data["cases"] if c["single_agent"]["verdict"] == "faithful"),
                "mutated": sum(1 for c in comparison_data["cases"] if c["single_agent"]["verdict"] == "mutated"),
                "ambiguous": sum(1 for c in comparison_data["cases"] if c["single_agent"]["verdict"] == "ambiguous")
            },
            "multi_agent_standard": {
                "faithful": sum(1 for c in comparison_data["cases"] if c["multi_agent_standard"]["verdict"] == "faithful"),
                "mutated": sum(1 for c in comparison_data["cases"] if c["multi_agent_standard"]["verdict"] == "mutated"),
                "ambiguous": sum(1 for c in comparison_data["cases"] if c["multi_agent_standard"]["verdict"] == "ambiguous")
            },
            "multi_agent_forced": {
                "faithful": sum(1 for c in comparison_data["cases"] if c["multi_agent_forced"]["verdict"] == "faithful"),
                "mutated": sum(1 for c in comparison_data["cases"] if c["multi_agent_forced"]["verdict"] == "mutated"),
                "ambiguous": sum(1 for c in comparison_data["cases"] if c["multi_agent_forced"]["verdict"] == "ambiguous")
            }
        },
        "forced_binary_stats": {
            "total_forced": sum(1 for c in comparison_data["cases"] if c["multi_agent_forced"]["forced_binary_used"]),
            "verdict_changed_by_forcing": sum(1 for c in comparison_data["cases"] if c["comparison"]["forced_changed_verdict"])
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
    print(f"  Avg confidence (Single-Agent):     {avg_sa_conf:.1f}%")
    print(f"  Avg confidence (MA Standard):      {avg_ma_standard_conf:.1f}%")
    print(f"  Avg confidence (MA Forced Binary): {avg_ma_forced_conf:.1f}%")
    print(f"\nForced Binary Stats:")
    print(f"  Cases forced to binary: {comparison_data['statistics']['forced_binary_stats']['total_forced']}/{total_cases}")
    print(f"  Verdicts changed by forcing: {comparison_data['statistics']['forced_binary_stats']['verdict_changed_by_forcing']}")
    
    
    return output_file


if __name__ == "__main__":
    import sys
    
    num_cases = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    print(f"🎯 Generating comparison data for {num_cases} cases\n")
    
    export_for_visualization(num_cases)
