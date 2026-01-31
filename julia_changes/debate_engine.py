"""
Multi-Agent Debate Engine with Structured 3-Round Protocol
==========================================================

Round 1 - Initial Stance: Each agent independently analyzes and gives verdict
Round 2 - Cross-Examination: Agents attack or concede each other's arguments
Round 3 - Consensus: Moderator synthesizes and delivers final verdict

Outputs both terminal display and structured JSON transcript.
"""

import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional
from openai import OpenAI


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class VerdictType(str, Enum):
    FAITHFUL = "faithful"
    MUTATED = "mutated"
    UNCERTAIN = "uncertain"


@dataclass
class Argument:
    id: str
    text: str
    evidence_quote: Optional[str] = None
    severity: Optional[str] = None  # high/medium/low


@dataclass
class InitialStance:
    agent: str
    verdict: VerdictType
    confidence: float
    arguments: list[Argument]
    reasoning_summary: str


@dataclass
class CrossExamResponse:
    agent: str
    target_agent: str
    target_argument_id: str
    action: str  # "attack" or "concede"
    response_text: str
    updated_confidence: float


@dataclass
class ConsensusResult:
    final_verdict: VerdictType
    confidence: float
    majority_position: str
    key_agreements: list[str]
    unresolved_disputes: list[str]
    reasoning: str


@dataclass
class DebateTranscript:
    case_id: int
    claim: str
    truth: str
    timestamp: str
    model: str
    round1_stances: list[InitialStance]
    round2_exchanges: list[CrossExamResponse]
    round3_consensus: ConsensusResult

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "case_id": self.case_id,
            "claim": self.claim,
            "truth": self.truth,
            "timestamp": self.timestamp,
            "model": self.model,
            "rounds": {
                "round1_initial_stances": [
                    {
                        "agent": s.agent,
                        "verdict": s.verdict.value,
                        "confidence": s.confidence,
                        "arguments": [asdict(a) for a in s.arguments],
                        "reasoning_summary": s.reasoning_summary
                    } for s in self.round1_stances
                ],
                "round2_cross_examination": [
                    {
                        "agent": e.agent,
                        "target_agent": e.target_agent,
                        "target_argument_id": e.target_argument_id,
                        "action": e.action,
                        "response_text": e.response_text,
                        "updated_confidence": e.updated_confidence
                    } for e in self.round2_exchanges
                ],
                "round3_consensus": {
                    "final_verdict": self.round3_consensus.final_verdict.value,
                    "confidence": self.round3_consensus.confidence,
                    "majority_position": self.round3_consensus.majority_position,
                    "key_agreements": self.round3_consensus.key_agreements,
                    "unresolved_disputes": self.round3_consensus.unresolved_disputes,
                    "reasoning": self.round3_consensus.reasoning
                }
            }
        }


# =============================================================================
# AGENT PROMPTS - Round 1 (Initial Stance)
# =============================================================================

FACT_CHECKER_R1 = """You are FACT_CHECKER, a precise analyst who compares claims against source facts.

Your job: Identify ANY discrepancy between the claim and the truth, no matter how small.

Focus on:
- Numerical accuracy (exact numbers, percentages, magnitudes)
- Temporal accuracy (dates, timeframes)
- Scope accuracy (geographic, demographic)
- Qualifier accuracy (may/will, some/all, about/exactly)

IMPORTANT: Quote specific text from both claim and truth to support your analysis.

Return JSON:
{
    "verdict": "faithful" | "mutated" | "uncertain",
    "confidence": 0.0-1.0,
    "arguments": [
        {
            "id": "FC1",
            "text": "concise argument statement",
            "evidence_quote": "exact quote from claim vs truth",
            "severity": "high" | "medium" | "low"
        }
    ],
    "reasoning_summary": "2 sentences explaining your position"
}"""


SKEPTIC_R1 = """You are SKEPTIC, a critical analyst who questions whether apparent mutations actually matter.

Your job: Challenge whether discrepancies constitute meaningful distortion or are acceptable simplifications.

Consider:
- Is this normal journalistic rounding/paraphrasing?
- Does the core meaning remain intact?
- Would a reasonable reader be misled?
- Is the "error" within acceptable margin?

IMPORTANT: Be genuinely critical. If the claim preserves the essential truth, defend it.

Return JSON:
{
    "verdict": "faithful" | "mutated" | "uncertain",
    "confidence": 0.0-1.0,
    "arguments": [
        {
            "id": "SK1",
            "text": "concise argument statement",
            "evidence_quote": "relevant quote showing your point",
            "severity": "high" | "medium" | "low"
        }
    ],
    "reasoning_summary": "2 sentences explaining your position"
}"""


CONTEXTUALIST_R1 = """You are CONTEXTUALIST, an analyst who evaluates claims in their broader context.

Your job: Assess whether the claim's framing changes the meaning in ways that matter.

Consider:
- Does omitted context change the interpretation?
- Are causal implications altered?
- Is the emotional/rhetorical framing different?
- What would a typical reader understand vs what's actually true?

IMPORTANT: Focus on meaning and implications, not just literal accuracy.

Return JSON:
{
    "verdict": "faithful" | "mutated" | "uncertain",
    "confidence": 0.0-1.0,
    "arguments": [
        {
            "id": "CX1",
            "text": "concise argument statement",
            "evidence_quote": "relevant quote showing your point",
            "severity": "high" | "medium" | "low"
        }
    ],
    "reasoning_summary": "2 sentences explaining your position"
}"""


# =============================================================================
# AGENT PROMPTS - Round 2 (Cross-Examination)
# =============================================================================

CROSS_EXAM_PROMPT = """You are {agent_name} in Round 2 of a fact-verification debate.

You have seen the other agents' arguments from Round 1.

YOUR ORIGINAL STANCE:
{own_stance}

OTHER AGENTS' ARGUMENTS TO RESPOND TO:
{other_arguments}

For EACH argument from other agents, you must either:
1. ATTACK: Explain why the argument is flawed, weak, or irrelevant
2. CONCEDE: Acknowledge the argument is strong and you accept it

Be specific. Quote evidence. Update your confidence if warranted.

Return JSON:
{
    "responses": [
        {
            "target_agent": "agent name",
            "target_argument_id": "e.g. FC1",
            "action": "attack" | "concede",
            "response_text": "your specific response (2-3 sentences max)"
        }
    ],
    "updated_confidence": 0.0-1.0,
    "stance_changed": true | false,
    "new_verdict": "faithful" | "mutated" | "uncertain" (only if changed)
}"""


# =============================================================================
# AGENT PROMPTS - Round 3 (Consensus)
# =============================================================================

MODERATOR_R3 = """You are MODERATOR synthesizing a fact-verification debate.

CLAIM: "{claim}"
TRUTH: "{truth}"

ROUND 1 - INITIAL STANCES:
{round1_summary}

ROUND 2 - CROSS-EXAMINATION:
{round2_summary}

Your task:
1. Identify where agents AGREE (key agreements)
2. Identify what remains DISPUTED (unresolved)
3. Weigh the arguments and deliver a FINAL VERDICT

The verdict should reflect:
- Which arguments survived cross-examination
- Where concessions were made
- The overall weight of evidence

Return JSON:
{
    "final_verdict": "faithful" | "mutated" | "uncertain",
    "confidence": 0.0-1.0,
    "majority_position": "brief description of majority view",
    "key_agreements": ["point 1", "point 2"],
    "unresolved_disputes": ["dispute 1"],
    "reasoning": "3-4 sentences explaining the verdict and why"
}"""


# =============================================================================
# TERMINAL DISPLAY
# =============================================================================

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'


def print_header(text: str, char: str = "="):
    width = 72
    print(f"\n{Colors.CYAN}{char * width}")
    print(f"{text:^{width}}")
    print(f"{char * width}{Colors.END}\n")


def print_agent(name: str, color: str):
    print(f"\n{color}{Colors.BOLD}[{name}]{Colors.END}")


def print_argument(arg: Argument, prefix: str = "  "):
    severity_color = {
        "high": Colors.RED,
        "medium": Colors.YELLOW,
        "low": Colors.GREEN
    }.get(arg.severity, "")

    print(f"{prefix}• {arg.text}")
    if arg.evidence_quote:
        print(f"{prefix}  {Colors.DIM}Evidence: \"{arg.evidence_quote[:80]}...\"{Colors.END}")
    if arg.severity:
        print(f"{prefix}  {severity_color}[{arg.severity.upper()}]{Colors.END}")


def print_stance(stance: InitialStance):
    color = {
        VerdictType.FAITHFUL: Colors.GREEN,
        VerdictType.MUTATED: Colors.RED,
        VerdictType.UNCERTAIN: Colors.YELLOW
    }[stance.verdict]

    agent_colors = {
        "FACT_CHECKER": Colors.BLUE,
        "SKEPTIC": Colors.MAGENTA,
        "CONTEXTUALIST": Colors.CYAN
    }

    print_agent(stance.agent, agent_colors.get(stance.agent, Colors.BOLD))
    print(f"  Verdict: {color}{stance.verdict.value.upper()}{Colors.END} (confidence: {stance.confidence:.0%})")
    print(f"  {Colors.DIM}{stance.reasoning_summary}{Colors.END}")
    print("  Arguments:")
    for arg in stance.arguments:
        print_argument(arg, "    ")


def print_exchange(exchange: CrossExamResponse):
    action_color = Colors.RED if exchange.action == "attack" else Colors.GREEN
    action_symbol = "⚔️" if exchange.action == "attack" else "✓"

    agent_colors = {
        "FACT_CHECKER": Colors.BLUE,
        "SKEPTIC": Colors.MAGENTA,
        "CONTEXTUALIST": Colors.CYAN
    }

    print(f"\n  {agent_colors.get(exchange.agent, '')}{exchange.agent}{Colors.END} → "
          f"{exchange.target_agent}'s [{exchange.target_argument_id}]:")
    print(f"    {action_color}{action_symbol} {exchange.action.upper()}{Colors.END}: {exchange.response_text}")


def print_consensus(consensus: ConsensusResult):
    color = {
        VerdictType.FAITHFUL: Colors.GREEN,
        VerdictType.MUTATED: Colors.RED,
        VerdictType.UNCERTAIN: Colors.YELLOW
    }[consensus.final_verdict]

    emoji = {
        VerdictType.FAITHFUL: "✅",
        VerdictType.MUTATED: "❌",
        VerdictType.UNCERTAIN: "⚠️"
    }[consensus.final_verdict]

    print(f"\n  {emoji} {color}{Colors.BOLD}FINAL VERDICT: {consensus.final_verdict.value.upper()}{Colors.END}")
    print(f"  Confidence: {consensus.confidence:.0%}")
    print(f"\n  {Colors.DIM}Majority position:{Colors.END} {consensus.majority_position}")

    if consensus.key_agreements:
        print(f"\n  {Colors.GREEN}Key Agreements:{Colors.END}")
        for agreement in consensus.key_agreements:
            print(f"    ✓ {agreement}")

    if consensus.unresolved_disputes:
        print(f"\n  {Colors.YELLOW}Unresolved Disputes:{Colors.END}")
        for dispute in consensus.unresolved_disputes:
            print(f"    ? {dispute}")

    print(f"\n  {Colors.BOLD}Reasoning:{Colors.END}")
    print(f"  {consensus.reasoning}")


# =============================================================================
# DEBATE ENGINE
# =============================================================================

class DebateEngine:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.agents = ["FACT_CHECKER", "SKEPTIC", "CONTEXTUALIST"]
        self.agent_prompts = {
            "FACT_CHECKER": FACT_CHECKER_R1,
            "SKEPTIC": SKEPTIC_R1,
            "CONTEXTUALIST": CONTEXTUALIST_R1
        }

    def _call_llm(self, system: str, user: str) -> dict:
        """Call LLM and parse JSON response."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

    def _run_round1(self, claim: str, truth: str) -> list[InitialStance]:
        """Round 1: Each agent gives initial stance."""
        print_header("ROUND 1: INITIAL STANCES", "─")

        user_prompt = f"""Analyze this claim-fact pair:

CLAIM (under investigation):
"{claim}"

TRUTH (source fact):
"{truth}"

Provide your initial assessment."""

        stances = []
        for agent in self.agents:
            result = self._call_llm(self.agent_prompts[agent], user_prompt)

            stance = InitialStance(
                agent=agent,
                verdict=VerdictType(result["verdict"]),
                confidence=result["confidence"],
                arguments=[
                    Argument(
                        id=a["id"],
                        text=a["text"],
                        evidence_quote=a.get("evidence_quote"),
                        severity=a.get("severity")
                    ) for a in result["arguments"]
                ],
                reasoning_summary=result["reasoning_summary"]
            )
            stances.append(stance)
            print_stance(stance)

        return stances

    def _run_round2(self, claim: str, truth: str, stances: list[InitialStance]) -> list[CrossExamResponse]:
        """Round 2: Cross-examination - agents attack or concede."""
        print_header("ROUND 2: CROSS-EXAMINATION", "─")

        exchanges = []

        for agent in self.agents:
            own_stance = next(s for s in stances if s.agent == agent)
            other_stances = [s for s in stances if s.agent != agent]

            # Format own stance
            own_stance_str = f"""Verdict: {own_stance.verdict.value}
Confidence: {own_stance.confidence}
Arguments: {json.dumps([asdict(a) for a in own_stance.arguments], indent=2)}"""

            # Format others' arguments
            other_args_str = ""
            for other in other_stances:
                other_args_str += f"\n{other.agent} (verdict: {other.verdict.value}):\n"
                for arg in other.arguments:
                    other_args_str += f"  [{arg.id}] {arg.text}\n"
                    if arg.evidence_quote:
                        other_args_str += f"      Evidence: \"{arg.evidence_quote}\"\n"

            prompt = CROSS_EXAM_PROMPT.format(
                agent_name=agent,
                own_stance=own_stance_str,
                other_arguments=other_args_str
            )

            result = self._call_llm(prompt, f"CLAIM: {claim}\nTRUTH: {truth}")

            print_agent(agent, {
                "FACT_CHECKER": Colors.BLUE,
                "SKEPTIC": Colors.MAGENTA,
                "CONTEXTUALIST": Colors.CYAN
            }.get(agent, Colors.BOLD))

            for resp in result["responses"]:
                exchange = CrossExamResponse(
                    agent=agent,
                    target_agent=resp["target_agent"],
                    target_argument_id=resp["target_argument_id"],
                    action=resp["action"],
                    response_text=resp["response_text"],
                    updated_confidence=result["updated_confidence"]
                )
                exchanges.append(exchange)
                print_exchange(exchange)

            # Show if stance changed
            if result.get("stance_changed"):
                print(f"\n  {Colors.YELLOW}⚡ Stance changed to: {result['new_verdict']}{Colors.END}")
            print(f"  Updated confidence: {result['updated_confidence']:.0%}")

        return exchanges

    def _run_round3(self, claim: str, truth: str,
                    stances: list[InitialStance],
                    exchanges: list[CrossExamResponse]) -> ConsensusResult:
        """Round 3: Moderator synthesizes consensus."""
        print_header("ROUND 3: CONSENSUS", "─")

        # Format Round 1 summary
        r1_summary = ""
        for s in stances:
            r1_summary += f"\n{s.agent}: {s.verdict.value} ({s.confidence:.0%})\n"
            for arg in s.arguments:
                r1_summary += f"  [{arg.id}] {arg.text}\n"

        # Format Round 2 summary
        r2_summary = ""
        for e in exchanges:
            r2_summary += f"\n{e.agent} {e.action}s {e.target_agent}'s [{e.target_argument_id}]: {e.response_text}\n"

        prompt = MODERATOR_R3.format(
            claim=claim,
            truth=truth,
            round1_summary=r1_summary,
            round2_summary=r2_summary
        )

        result = self._call_llm(prompt, "Synthesize the debate and deliver the final verdict.")

        consensus = ConsensusResult(
            final_verdict=VerdictType(result["final_verdict"]),
            confidence=result["confidence"],
            majority_position=result["majority_position"],
            key_agreements=result["key_agreements"],
            unresolved_disputes=result["unresolved_disputes"],
            reasoning=result["reasoning"]
        )

        print_agent("MODERATOR", Colors.BOLD)
        print_consensus(consensus)

        return consensus

    def run_debate(self, case_id: int, claim: str, truth: str) -> DebateTranscript:
        """Run complete 3-round debate."""
        print_header(f"CASE {case_id}: FACT VERIFICATION TRIBUNAL", "═")

        print(f"{Colors.BOLD}CLAIM:{Colors.END}")
        print(f"  \"{claim}\"")
        print(f"\n{Colors.BOLD}TRUTH:{Colors.END}")
        print(f"  \"{truth}\"")

        # Execute rounds
        stances = self._run_round1(claim, truth)
        exchanges = self._run_round2(claim, truth, stances)
        consensus = self._run_round3(claim, truth, stances, exchanges)

        # Build transcript
        transcript = DebateTranscript(
            case_id=case_id,
            claim=claim,
            truth=truth,
            timestamp=datetime.now().isoformat(),
            model=self.model,
            round1_stances=stances,
            round2_exchanges=exchanges,
            round3_consensus=consensus
        )

        print_header("DEBATE COMPLETE", "═")

        return transcript


def save_transcript(transcript: DebateTranscript, filepath: str):
    """Save transcript to JSON file."""
    with open(filepath, 'w') as f:
        json.dump(transcript.to_dict(), f, indent=2)
    print(f"\n{Colors.GREEN}Transcript saved to: {filepath}{Colors.END}")


def save_all_transcripts(transcripts: list[DebateTranscript], filepath: str):
    """Save all transcripts to a single JSON file."""
    data = {
        "generated_at": datetime.now().isoformat(),
        "model": transcripts[0].model if transcripts else "unknown",
        "total_cases": len(transcripts),
        "summary": {
            "faithful": sum(1 for t in transcripts if t.round3_consensus.final_verdict == VerdictType.FAITHFUL),
            "mutated": sum(1 for t in transcripts if t.round3_consensus.final_verdict == VerdictType.MUTATED),
            "uncertain": sum(1 for t in transcripts if t.round3_consensus.final_verdict == VerdictType.UNCERTAIN),
        },
        "debates": [t.to_dict() for t in transcripts]
    }

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n{Colors.GREEN}All transcripts saved to: {filepath}{Colors.END}")
