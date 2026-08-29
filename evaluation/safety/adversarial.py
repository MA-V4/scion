from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AdversarialResult:
    task_id: str
    attack_type: str
    attack_succeeded: bool
    detected: bool


class AdversarialEvaluator:
    """
    Runs the safety benchmark: 50 adversarial tasks covering injection,
    exfiltration, tool abuse, and privilege escalation.

    Reports:
      - attack_success_rate: fraction of attacks that bypassed defences
      - detection_rate: fraction of attacks caught by the injection detector
      - false_positive_rate: fraction of benign tasks flagged as attacks
    """

    async def run(self, tasks_path: str) -> dict:
        # TODO: load adversarial tasks, run each through the agent,
        # check whether the attack succeeded or was blocked
        raise NotImplementedError
