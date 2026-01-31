"""
Single-Agent Baseline for Claim Verification
Simple, direct approach without debate - for comparison with multi-agent system
"""

from openai import OpenAI
import json
import os
from dataclasses import dataclass
from enum import Enum


class Verdict(Enum):
    FAITHFUL = "faithful"
    MUTATED = "mutated"
    AMBIGUOUS = "ambiguous"


@dataclass
class SingleAgentResult:
    claim: str
    truth: str
    verdict: Verdict
    confidence: float
    reasoning: str
    mutation_types: list[str]
    raw_response: dict


SINGLE_AGENT_SYSTEM = """You are a fact-checking AI that verifies whether external claims faithfully represent source facts.

Your task is to analyze claim-fact pairs and determine if the claim is:
- FAITHFUL: Accurately represents the source fact
- MUTATED: Contains distortions, exaggerations, or misrepresentations
- AMBIGUOUS: Unclear or interpretable either way

Respond with JSON containing:
{
  "verdict": "faithful" | "mutated" | "ambiguous",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "mutation_types": ["type1", "type2"] or [],
  "key_evidence": ["evidence point 1", "evidence point 2"]
}

Be decisive and provide a clear verdict."""


class SingleAgentVerifier:
    def __init__(self, api_key: str, dev_mode: bool = True):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4.1-mini" if dev_mode else "gpt-4.1"
    
    def verify_claim(self, claim: str, truth: str) -> SingleAgentResult:
        """Verify a claim against source truth using single-agent approach."""
        
        prompt = f"""Analyze this claim-fact pair:

ORIGINAL FACT (Source of Truth):
"{truth}"

EXTERNAL CLAIM (To Verify):
"{claim}"

Determine if the claim faithfully represents the fact, is mutated/distorted, or is ambiguous."""

        messages = [
            {"role": "system", "content": SINGLE_AGENT_SYSTEM},
            {"role": "user", "content": prompt}
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        result = json.loads(content)
        
        # Parse verdict
        verdict_str = result.get("verdict", "ambiguous").lower()
        if verdict_str == "faithful":
            verdict = Verdict.FAITHFUL
        elif verdict_str == "mutated":
            verdict = Verdict.MUTATED
        else:
            verdict = Verdict.AMBIGUOUS
        
        return SingleAgentResult(
            claim=claim,
            truth=truth,
            verdict=verdict,
            confidence=result.get("confidence", 0),
            reasoning=result.get("reasoning", ""),
            mutation_types=result.get("mutation_types", []),
            raw_response=result
        )


def run_single_agent_baseline(cases: list[dict], api_key: str) -> list[SingleAgentResult]:
    """Run single-agent verification on all cases."""
    verifier = SingleAgentVerifier(api_key)
    results = []
    
    print("\n" + "="*70)
    print("SINGLE-AGENT BASELINE VERIFICATION")
    print("="*70)
    
    for idx, case in enumerate(cases):
        print(f"\n📋 Case {idx}: {case['claim'][:60]}...")
        
        result = verifier.verify_claim(case['claim'], case['truth'])
        results.append(result)
        
        print(f"   Verdict: {result.verdict.value.upper()}")
        print(f"   Confidence: {result.confidence:.0%}")
        print(f"   Reasoning: {result.reasoning[:100]}...")
    
    return results


def export_single_agent_results(results: list[SingleAgentResult], filepath: str = "single_agent_results.json"):
    """Export single-agent results to JSON."""
    export_data = []
    
    for idx, r in enumerate(results):
        export_data.append({
            "case_id": idx,
            "claim": r.claim,
            "truth": r.truth,
            "verdict": r.verdict.value,
            "confidence": r.confidence,
            "reasoning": r.reasoning,
            "mutation_types": r.mutation_types,
            "key_evidence": r.raw_response.get("key_evidence", []),
            "raw_response": r.raw_response
        })
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Single-agent results exported to {filepath}")


if __name__ == "__main__":
    import csv
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: Set OPENAI_API_KEY environment variable")
        exit(1)
    
    # Load data
    data = []
    with open('Kepler.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if row['claim'] and row['truth']:
                data.append({
                    'id': idx,
                    'claim': row['claim'].strip(),
                    'truth': row['truth'].strip()
                })
    
    print(f"📚 Loaded {len(data)} claim-truth pairs from Kepler.csv")
    
    # Run on first 2 cases for comparison
    test_cases = data[:2]
    print(f"🎯 Analyzing {len(test_cases)} cases: {[c['id'] for c in test_cases]}")
    
    # Run single-agent verification
    results = run_single_agent_baseline(test_cases, api_key)
    
    # Export results
    export_single_agent_results(results)