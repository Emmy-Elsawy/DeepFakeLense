"""
Standalone test execution script for intake_agent.py.
Loads mock_intake_inputs.json and runs intake_agent.py against them.
"""

from __future__ import annotations
import json
import os
import sys

# Add current directory to path just in case
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Ensure Unicode characters (like Arabic) print correctly in Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import intake_agent


def main():
    mock_file = "mock_intake_inputs.json"
    if not os.path.exists(mock_file):
        print(f"Error: {mock_file} not found.", file=sys.stderr)
        sys.exit(1)

    print(f"--- Loading Mock Inputs from {mock_file} ---")
    with open(mock_file, "r", encoding="utf-8") as f:
        cases = json.load(f)

    for case in cases:
        case_id = case.get("id", "unknown")
        input_type = case.get("input_type")
        text_claim = case.get("text_claim")
        image_url = case.get("image_url")
        language = case.get("language", "en")

        print(f"\n======================================================================")
        print(f"Running case: {case_id} (Type: {input_type}, Lang: {language})")
        print(f"Input text_claim: {text_claim}")
        print(f"Input image_url: {image_url}")
        print(f"----------------------------------------------------------------------")

        try:
            output = intake_agent.run_intake(
                input_type=input_type,
                text_claim=text_claim,
                image_url=image_url,
                language=language
            )
            print("OUTPUT JSON:")
            print(json.dumps(output, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"CRITICAL ERROR running case {case_id}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
