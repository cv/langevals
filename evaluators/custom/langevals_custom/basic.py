import re
from typing import Literal, Optional
from langevals_core.base_evaluator import (
    BaseEvaluator,
    EvaluatorEntry,
    EvaluationResult,
    SingleEvaluationResult,
)
from pydantic import BaseModel, Field


class CustomBasicEntry(EvaluatorEntry):
    input: Optional[str] = None
    output: Optional[str] = None


class CustomBasicRule(BaseModel):
    field: Literal["input", "output"] = "output"
    rule: Literal[
        "contains",
        "not_contains",
        "matches_regex",
        "not_matches_regex",
    ]
    value: str


class CustomBasicSettings(BaseModel):
    rules: list[CustomBasicRule] = []


class CustomBasicResult(EvaluationResult):
    score: float = Field(description="Returns 1 if all rules pass, 0 if any rule fails")
    passed: Optional[bool]


class CustomBasicEvaluator(
    BaseEvaluator[CustomBasicEntry, CustomBasicSettings, CustomBasicResult]
):
    """
    Allows you to check for simple text matches or regex evaluation.
    """

    name = "Custom Basic Evaluator"
    category = "custom"
    is_guardrail = True

    def evaluate(self, entry: CustomBasicEntry) -> SingleEvaluationResult:
        passed = True
        score = 1
        details = None

        if len(self.settings.rules) == 0:
            return CustomBasicResult(
                score=0, passed=False, details="No rules were defined"
            )

        for rule in self.settings.rules:
            if not self.check_rule(rule, entry):
                passed = False
                score = 0
                details = f'Rule {rule.rule} "{rule.value}" failed for {rule.field} "{entry.output if rule.field == "output" else entry.input}"'
                break

        return CustomBasicResult(score=score, passed=passed, details=details)

    def check_rule(self, rule: CustomBasicRule, entry: CustomBasicEntry) -> bool:
        if rule.field == "input":
            field = entry.input or ""
        else:
            field = entry.output or ""

        if rule.rule == "contains":
            return rule.value in field
        elif rule.rule == "not_contains":
            return rule.value not in field
        elif rule.rule == "matches_regex":
            return bool(re.match(rule.value, field))
        elif rule.rule == "not_matches_regex":
            return not bool(re.match(rule.value, field))
        else:
            return False
