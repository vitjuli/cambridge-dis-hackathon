"""
Multi-Agent Debate System for Claim Verification
Adversarial Tribunal Architecture

Agents:
1. Prosecutor - Hunts for mutations/distortions
2. Defense - Argues for faithful interpretation
3. Epistemologist - Quantifies uncertainty
4. Jury Foreman - Synthesizes verdict
"""

from openai import OpenAI
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import json


class Verdict(Enum):
    FAITHFUL = "faithful"
    MUTATED = "mutated"
    AMBIGUOUS = "ambiguous"


class MutationType(Enum):
    NUMERICAL_DISTORTION = "numerical_distortion"
    MISSING_CONTEXT = "missing_context"
    CAUSAL_CONFUSION = "causal_confusion"
    EXAGGERATION = "exaggeration"
    SCOPE_CHANGE = "scope_change"
    TEMPORAL_MISMATCH = "temporal_mismatch"
    ADDED_INFORMATION = "added_information"
    NEGATION_FRAMING = "negation_framing"


@dataclass
class AgentResponse:
    agent_name: str
    arguments: list[str]
    evidence: list[str]
    confidence: float
    mutation_types: list[str] = None


@dataclass
class DebateResult:
    claim: str
    truth: str
    prosecutor_response: AgentResponse
    defense_response: AgentResponse
    epistemologist_response: AgentResponse
    final_verdict: Verdict
    verdict_reasoning: str
    confidence: float
    debate_transcript: list[dict]


# =============================================================================
# AGENT SYSTEM PROMPTS
# =============================================================================

PROSECUTOR_SYSTEM = """You are the PROSECUTOR in a fact-verification tribunal. Your role is to find ANY evidence that the external claim MUTATES or DISTORTS the original fact.

You must be aggressive and thorough in identifying:
- NUMERICAL DISTORTIONS: Inflated/deflated numbers, changed percentages, altered magnitudes
- MISSING CONTEXT: Omitted qualifiers, removed caveats, stripped conditions
- CAUSAL CONFUSION: Implied causation from correlation, reversed cause-effect
- EXAGGERATION: Amplified severity, dramatized outcomes, sensationalized framing
- SCOPE CHANGES: Geographic/temporal scope altered, population changed
- TEMPORAL MISMATCHES: Wrong dates, shifted timeframes, outdated data presented as current
- ADDED INFORMATION: Claims not supported by the source fact
- NEGATION FRAMING: Reframing positive as negative or vice versa

OUTPUT FORMAT (JSON):
{
    "accusations": [
        {
            "type": "mutation_type",
            "evidence": "specific quote or comparison",
            "severity": "high/medium/low",
            "explanation": "why this constitutes a mutation"
        }
    ],
    "overall_assessment": "summary of prosecution case",
    "confidence": 0.0-1.0
}

Be precise. Quote exact phrases. Compare specific numbers. Leave no distortion unexamined."""


DEFENSE_SYSTEM = """You are the DEFENSE ADVOCATE in a fact-verification tribunal. Your role is to argue that the external claim FAITHFULLY represents the original fact, despite any surface-level differences.

You must find legitimate reasons why apparent discrepancies are acceptable:
- REASONABLE ROUNDING: Numbers within acceptable margin for summary/headline
- JOURNALISTIC CONVENTION: Standard practices in news summarization
- SEMANTIC EQUIVALENCE: Different words conveying the same meaning
- IMPLICIT CONTEXT: Information audiences would reasonably understand
- ACCEPTABLE PARAPHRASE: Rephrasing that preserves core meaning
- SCOPE ALIGNMENT: Claim stays within bounds of source fact

For each prosecution accusation, provide a counter-argument if possible.

OUTPUT FORMAT (JSON):
{
    "rebuttals": [
        {
            "accusation_addressed": "which prosecution point",
            "counter_argument": "why this is not a true mutation",
            "justification": "evidence or reasoning"
        }
    ],
    "faithful_elements": ["list of accurately represented aspects"],
    "overall_assessment": "summary of defense case",
    "confidence": 0.0-1.0
}

Be charitable but honest. If a mutation is undeniable, acknowledge it."""


EPISTEMOLOGIST_SYSTEM = """You are the EPISTEMOLOGIST in a fact-verification tribunal. Your role is to assess UNCERTAINTY and EPISTEMIC LIMITS of this verification task.

Analyze:
1. VERIFIABLE vs INTERPRETATION-DEPENDENT: What can be objectively determined vs requires judgment?
2. AMBIGUITY SOURCES: Vague language, missing metadata, context-dependent meaning
3. LEGITIMATE DISAGREEMENT: Where do Prosecutor and Defense have valid competing interpretations?
4. INFORMATION GAPS: What additional information would resolve the dispute?
5. CONFIDENCE CALIBRATION: How certain can we actually be about any verdict?

OUTPUT FORMAT (JSON):
{
    "verifiable_facts": ["list of objectively checkable claims"],
    "interpretation_dependent": ["aspects requiring judgment"],
    "ambiguity_analysis": {
        "source": "what causes ambiguity",
        "impact": "how it affects verdict confidence"
    },
    "prosecution_validity": {
        "strong_points": ["well-supported accusations"],
        "weak_points": ["overreaching or speculative accusations"]
    },
    "defense_validity": {
        "strong_points": ["well-supported rebuttals"],
        "weak_points": ["unconvincing arguments"]
    },
    "recommended_confidence_range": [0.0, 1.0],
    "verdict_recommendation": "faithful/mutated/ambiguous",
    "key_uncertainty": "main factor limiting certainty"
}

Be rigorous. Acknowledge when the evidence genuinely supports multiple interpretations."""


JURY_FOREMAN_SYSTEM = """You are the JURY FOREMAN in a fact-verification tribunal. You must synthesize the debate and deliver a FINAL VERDICT.

You have received:
1. PROSECUTOR's accusations of mutation
2. DEFENSE's rebuttals and faithful interpretation arguments
3. EPISTEMOLOGIST's uncertainty analysis

Your task:
1. Weigh the strength of each argument
2. Identify which accusations survived defense rebuttals
3. Consider epistemic uncertainty in your confidence level
4. Deliver a clear verdict with transparent reasoning

VERDICT OPTIONS:
- FAITHFUL: The claim accurately represents the source fact (minor acceptable variations)
- MUTATED: The claim distorts the source fact in meaningful ways
- AMBIGUOUS: Insufficient evidence or genuine interpretive uncertainty

OUTPUT FORMAT (JSON):
{
    "verdict": "faithful/mutated/ambiguous",
    "confidence": 0.0-1.0,
    "reasoning": {
        "decisive_factors": ["what determined the verdict"],
        "prosecution_points_accepted": ["accusations that held up"],
        "prosecution_points_rejected": ["accusations that were rebutted"],
        "defense_points_accepted": ["rebuttals that succeeded"],
        "uncertainty_acknowledgment": "what we cannot be certain about"
    },
    "mutation_types_identified": ["list if mutated, empty if faithful"],
    "summary": "2-3 sentence verdict explanation for presentation"
}

Be decisive but calibrated. Acknowledge uncertainty without being paralyzed by it."""


# =============================================================================
# DEBATE ORCHESTRATOR
# =============================================================================

class DebateOrchestrator:
    def __init__(self, api_key: str, dev_mode: bool = True):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini" if dev_mode else "gpt-4o"
        self.debate_history = []

    def _call_agent(self, system_prompt: str, user_prompt: str, agent_name: str) -> dict:
        """Call an agent and parse JSON response."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        content = response.json_content = response.choices[0].message.content
        self.debate_history.append({
            "agent": agent_name,
            "response": content
        })

        return json.loads(content)

    def run_prosecution(self, claim: str, truth: str) -> dict:
        """Round 1: Prosecutor presents accusations."""
        prompt = f"""EVIDENCE FOR EXAMINATION:

ORIGINAL FACT (Source of Truth):
"{truth}"

EXTERNAL CLAIM (Under Investigation):
"{claim}"

Analyze this claim-fact pair and present your prosecution case. Identify ALL mutations, distortions, or misrepresentations."""

        return self._call_agent(PROSECUTOR_SYSTEM, prompt, "Prosecutor")

    def run_defense(self, claim: str, truth: str, prosecution_case: dict) -> dict:
        """Round 2: Defense responds to prosecution."""
        prompt = f"""EVIDENCE FOR EXAMINATION:

ORIGINAL FACT (Source of Truth):
"{truth}"

EXTERNAL CLAIM (Under Investigation):
"{claim}"

PROSECUTION'S ACCUSATIONS:
{json.dumps(prosecution_case, indent=2)}

Respond to the prosecution's case. Provide rebuttals where possible and identify faithfully represented elements."""

        return self._call_agent(DEFENSE_SYSTEM, prompt, "Defense")

    def run_epistemologist(self, claim: str, truth: str,
                           prosecution_case: dict, defense_case: dict) -> dict:
        """Round 3: Epistemologist analyzes uncertainty."""
        prompt = f"""EVIDENCE FOR EXAMINATION:

ORIGINAL FACT (Source of Truth):
"{truth}"

EXTERNAL CLAIM (Under Investigation):
"{claim}"

PROSECUTION'S CASE:
{json.dumps(prosecution_case, indent=2)}

DEFENSE'S CASE:
{json.dumps(defense_case, indent=2)}

Analyze the epistemic status of this debate. What can we know with certainty? Where is legitimate disagreement? How confident can we be in any verdict?"""

        return self._call_agent(EPISTEMOLOGIST_SYSTEM, prompt, "Epistemologist")

    def run_jury_foreman(self, claim: str, truth: str,
                         prosecution_case: dict, defense_case: dict,
                         epistemologist_analysis: dict) -> dict:
        """Round 4: Jury Foreman delivers verdict."""
        prompt = f"""CASE SUMMARY:

ORIGINAL FACT (Source of Truth):
"{truth}"

EXTERNAL CLAIM (Under Investigation):
"{claim}"

=== DEBATE TRANSCRIPT ===

PROSECUTION'S CASE:
{json.dumps(prosecution_case, indent=2)}

DEFENSE'S CASE:
{json.dumps(defense_case, indent=2)}

EPISTEMOLOGIST'S ANALYSIS:
{json.dumps(epistemologist_analysis, indent=2)}

=== END TRANSCRIPT ===

Deliberate and deliver your final verdict. Weigh all arguments and provide transparent reasoning."""

        return self._call_agent(JURY_FOREMAN_SYSTEM, prompt, "Jury Foreman")

    def run_full_debate(self, claim: str, truth: str) -> DebateResult:
        """Execute the complete debate protocol."""
        self.debate_history = []

        print(f"\n{'='*60}")
        print("TRIBUNAL COMMENCING")
        print(f"{'='*60}")
        print(f"\nCLAIM: {claim[:100]}...")
        print(f"TRUTH: {truth[:100]}...")

        # Round 1: Prosecution
        print("\n[Round 1] Prosecutor presenting accusations...")
        prosecution = self.run_prosecution(claim, truth)

        # Round 2: Defense
        print("[Round 2] Defense presenting rebuttals...")
        defense = self.run_defense(claim, truth, prosecution)

        # Round 3: Epistemologist
        print("[Round 3] Epistemologist analyzing uncertainty...")
        epistemology = self.run_epistemologist(claim, truth, prosecution, defense)

        # Round 4: Verdict
        print("[Round 4] Jury Foreman deliberating...")
        verdict_response = self.run_jury_foreman(claim, truth, prosecution, defense, epistemology)

        # Parse verdict
        verdict_str = verdict_response.get("verdict", "ambiguous").lower()
        if verdict_str == "faithful":
            verdict = Verdict.FAITHFUL
        elif verdict_str == "mutated":
            verdict = Verdict.MUTATED
        else:
            verdict = Verdict.AMBIGUOUS

        print(f"\n{'='*60}")
        print(f"VERDICT: {verdict.value.upper()}")
        print(f"CONFIDENCE: {verdict_response.get('confidence', 0):.0%}")
        print(f"{'='*60}")
        print(f"\nSUMMARY: {verdict_response.get('summary', 'No summary provided')}")

        return DebateResult(
            claim=claim,
            truth=truth,
            prosecutor_response=AgentResponse(
                agent_name="Prosecutor",
                arguments=[a.get("explanation", "") for a in prosecution.get("accusations", [])],
                evidence=[a.get("evidence", "") for a in prosecution.get("accusations", [])],
                confidence=prosecution.get("confidence", 0),
                mutation_types=[a.get("type", "") for a in prosecution.get("accusations", [])]
            ),
            defense_response=AgentResponse(
                agent_name="Defense",
                arguments=[r.get("counter_argument", "") for r in defense.get("rebuttals", [])],
                evidence=[r.get("justification", "") for r in defense.get("rebuttals", [])],
                confidence=defense.get("confidence", 0)
            ),
            epistemologist_response=AgentResponse(
                agent_name="Epistemologist",
                arguments=[epistemology.get("key_uncertainty", "")],
                evidence=epistemology.get("verifiable_facts", []),
                confidence=epistemology.get("recommended_confidence_range", [0.5, 0.5])[1]
            ),
            final_verdict=verdict,
            verdict_reasoning=verdict_response.get("summary", ""),
            confidence=verdict_response.get("confidence", 0),
            debate_transcript=self.debate_history
        )


def format_debate_for_presentation(result: DebateResult) -> str:
    """Format debate result for demo presentation."""
    output = []
    output.append("\n" + "="*70)
    output.append("FACT-VERIFICATION TRIBUNAL - CASE ANALYSIS")
    output.append("="*70)

    output.append("\n📋 CLAIM UNDER INVESTIGATION:")
    output.append(f"   \"{result.claim}\"")

    output.append("\n📚 SOURCE FACT:")
    output.append(f"   \"{result.truth}\"")

    output.append("\n" + "-"*70)
    output.append("DEBATE TRANSCRIPT")
    output.append("-"*70)

    # Prosecutor
    output.append("\n🔴 PROSECUTOR (Mutation Hunter):")
    for i, arg in enumerate(result.prosecutor_response.arguments[:3], 1):
        output.append(f"   {i}. {arg[:150]}...")
    output.append(f"   Confidence: {result.prosecutor_response.confidence:.0%}")

    # Defense
    output.append("\n🟢 DEFENSE (Faithful Interpreter):")
    for i, arg in enumerate(result.defense_response.arguments[:3], 1):
        output.append(f"   {i}. {arg[:150]}...")
    output.append(f"   Confidence: {result.defense_response.confidence:.0%}")

    # Epistemologist
    output.append("\n🟡 EPISTEMOLOGIST (Uncertainty Quantifier):")
    output.append(f"   Key uncertainty: {result.epistemologist_response.arguments[0][:200]}")

    output.append("\n" + "-"*70)
    output.append("VERDICT")
    output.append("-"*70)

    verdict_emoji = {"faithful": "✅", "mutated": "❌", "ambiguous": "⚠️"}
    output.append(f"\n{verdict_emoji.get(result.final_verdict.value, '❓')} FINAL VERDICT: {result.final_verdict.value.upper()}")
    output.append(f"   Confidence: {result.confidence:.0%}")
    output.append(f"\n   Reasoning: {result.verdict_reasoning}")

    if result.prosecutor_response.mutation_types:
        output.append(f"\n   Mutation types identified: {', '.join(result.prosecutor_response.mutation_types)}")

    output.append("\n" + "="*70)

    return "\n".join(output)
