"""
View complete raw LLM responses from debate_results.json
Properly formats the escaped JSON strings in debate_transcript
"""

import json
import sys

def print_raw_response(agent, response_str, case_id):
    """Print a single raw response nicely formatted."""
    print(f"\n{'='*80}")
    print(f"CASE {case_id} - {agent.upper()} - COMPLETE RAW LLM RESPONSE")
    print(f"{'='*80}")
    
    try:
        # Parse the escaped JSON string
        parsed = json.loads(response_str)
        # Pretty print it
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print("Raw string:")
        print(response_str)
    
    print(f"{'='*80}\n")


def main():
    # Load debate results
    try:
        with open('debate_results.json', 'r', encoding='utf-8') as f:
            debates = json.load(f)
    except FileNotFoundError:
        print("❌ debate_results.json not found")
        print("Run 'python kepler/export_debates.py' first")
        return
    
    print(f"\n📊 Found {len(debates)} debate cases\n")
    
    # Check command line args
    if len(sys.argv) > 1:
        case_id = int(sys.argv[1])
        debate = next((d for d in debates if d['case_id'] == case_id), None)
        if not debate:
            print(f"❌ Case {case_id} not found")
            return
        
        print(f"📋 CLAIM: {debate['claim'][:80]}...")
        print(f"📚 TRUTH: {debate['truth'][:80]}...")
        
        # for entry in debate['debate_transcript']:
        #     print_raw_response(entry['agent'], entry['response'], case_id)
    else:
        # Interactive mode
        print("Available cases:")
        for d in debates:
            print(f"  Case {d['case_id']}: {d['claim'][:60]}...")
        
        choice = input("\nEnter case number to view raw responses: ").strip()
        if choice.isdigit():
            case_id = int(choice)
            debate = next((d for d in debates if d['case_id'] == case_id), None)
            if debate:
                print(f"\n📋 CLAIM: {debate['claim']}")
                print(f"📚 TRUTH: {debate['truth']}\n")
                
                # for entry in debate['debate_transcript']:
                #     print_raw_response(entry['agent'], entry['response'], case_id)
            else:
                print(f"❌ Case {case_id} not found")


if __name__ == "__main__":
    main()
