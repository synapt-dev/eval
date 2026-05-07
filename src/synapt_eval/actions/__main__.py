"""Allow python -m synapt_eval.actions.pr_gate invocation."""

import sys

from synapt_eval.actions.pr_gate import parse_inputs, run_action

if __name__ == "__main__":
    inputs = parse_inputs()
    sys.exit(run_action(inputs))
