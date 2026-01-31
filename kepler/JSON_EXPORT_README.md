# Agent Debate JSON Export

## Overview
This script runs the multi-agent debate system and exports all results to a comprehensive JSON file for visualization or further analysis.

## Quick Start

### 1. Set your OpenAI API key
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 2. Run the export script
```bash
cd kepler
python export_debates.py
```

This will:
- Load claim-truth pairs from `Kepler.csv`
- Run debates through the 4-agent tribunal system
- Export comprehensive results to `debate_results.json`

## JSON Structure

The exported JSON contains an array of debate results, each with:

```json
[
  {
    "case_id": 0,
    "claim": "External claim text",
    "truth": "Internal fact text",
    "verdict": "faithful|mutated|ambiguous",
    "confidence": 0.85,
    "reasoning": "Verdict explanation",
    "prosecutor": {
      "agent_name": "Prosecutor",
      "arguments": ["argument 1", "argument 2"],
      "evidence": ["evidence 1", "evidence 2"],
      "confidence": 0.9,
      "mutation_types": ["numerical_distortion", "missing_context"]
    },
    "defense": {
      "agent_name": "Defense",
      "arguments": ["rebuttal 1", "rebuttal 2"],
      "evidence": ["justification 1", "justification 2"],
      "confidence": 0.7
    },
    "epistemologist": {
      "agent_name": "Epistemologist",
      "arguments": ["uncertainty analysis"],
      "evidence": ["verifiable facts"],
      "confidence": 0.75
    },
    "debate_transcript": [
      {
        "agent": "Prosecutor",
        "response": "full JSON response"
      }
    ]
  }
]
```

## Customization

Edit `export_debates.py` to change:
- **Case selection**: Modify `case_indices` parameter
- **Output file**: Change `output_file` parameter
- **Model**: Toggle `dev_mode` in DebateOrchestrator (True = gpt-4.1-mini, False = gpt-4.1)

Example:
```python
run_and_export_debates(
    api_key=api_key,
    case_indices=[0, 1, 2, 3, 4, 5],  # Run first 6 cases
    output_file="my_debates.json"
)
```

## Using the JSON

The exported JSON can be used for:
- **Visualization**: Feed into web dashboards, D3.js, or other viz tools
- **Analysis**: Process with pandas, analyze verdict patterns
- **Reporting**: Generate summaries and statistics
- **API Integration**: Serve via REST API for frontend consumption

## Files

- `export_debates.py` - Main export script
- `visualize.py` - Contains `export_results_json()` function
- `agents.py` - Multi-agent debate system
- `debate_results.json` - Generated output (after running)
