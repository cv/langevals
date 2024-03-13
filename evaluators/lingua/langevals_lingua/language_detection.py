from typing import Literal, Optional
from langevals_core.base_evaluator import (
    BaseEvaluator,
    EvaluatorEntry,
    EvaluationResult,
    EvaluationResultSkipped,
    SingleEvaluationResult,
)
from pydantic import BaseModel, Field
from lingua import IsoCode639_1, LanguageDetectorBuilder


class LinguaLanguageDetectionEntry(EvaluatorEntry):
    input: str
    output: str


AvailableLanguages = Literal[
    "AF",
    "AR",
    "AZ",
    "BE",
    "BG",
    "BN",
    "BS",
    "CA",
    "CS",
    "CY",
    "DA",
    "DE",
    "EL",
    "EN",
    "EO",
    "ES",
    "ET",
    "EU",
    "FA",
    "FI",
    "FR",
    "GA",
    "GU",
    "HE",
    "HI",
    "HR",
    "HU",
    "HY",
    "ID",
    "IS",
    "IT",
    "JA",
    "KA",
    "KK",
    "KO",
    "LA",
    "LG",
    "LT",
    "LV",
    "MI",
    "MK",
    "MN",
    "MR",
    "MS",
    "NB",
    "NL",
    "NN",
    "PA",
    "PL",
    "PT",
    "RO",
    "RU",
    "SK",
    "SL",
    "SN",
    "SO",
    "SQ",
    "SR",
    "ST",
    "SV",
    "SW",
    "TA",
    "TE",
    "TH",
    "TL",
    "TN",
    "TR",
    "TS",
    "UK",
    "UR",
    "VI",
    "XH",
    "YO",
    "ZH",
    "ZU",
]


class LinguaLanguageDetectionSettings(BaseModel):
    check_for: Literal["input_matches_output", "output_matches_language"] = Field(
        default="input_matches_output", description="What should be checked"
    )
    expected_language: Optional[AvailableLanguages] = Field(
        default=None,
        description="(Optional) The specific language that the output is expected to be",
    )
    min_words: int = Field(
        default=7,
        description="Minimum number of words to check, as the language detection can be unreliable for very short texts. Inputs shorter than the minimum will be skipped.",
    )
    threshold: float = Field(
        default=0.25,
        description="Minimum confidence threshold for the language detection. If the confidence is lower than this, the evaluation will be skipped.",
    )


class LinguaLanguageDetectionRawResponse(BaseModel):
    input: Optional[dict[AvailableLanguages, float]] = None
    output: dict[AvailableLanguages, float]


class LinguaLanguageDetectionResult(EvaluationResult):
    score: float = Field(description="How many languages were detected")
    passed: Optional[bool] = Field(
        description="Passes if the detected language on the output matches the detected language on the input, or if the output matches the expected language"
    )
    raw_response: LinguaLanguageDetectionRawResponse


detector = (
    LanguageDetectorBuilder.from_all_languages()
    .with_preloaded_language_models()
    .build()
)


class LinguaLanguageDetectionEvaluator(
    BaseEvaluator[
        LinguaLanguageDetectionEntry,
        LinguaLanguageDetectionSettings,
        LinguaLanguageDetectionResult,
    ]
):
    """
    This evaluator detects the language of the input and output text to check for example if the generated answer is in the same language as the prompt,
    or if it's in a specific expected language.
    """

    name = "Lingua Language Detection"
    category = "quality"
    docs_url = "https://github.com/pemistahl/lingua-py"
    is_guardrail = True

    def evaluate(self, entry: LinguaLanguageDetectionEntry) -> SingleEvaluationResult:
        words = entry.input.split(" ")
        if self.settings.check_for == "input_matches_output":
            if len(words) < self.settings.min_words:
                return EvaluationResultSkipped(
                    details=f"Skipped because the input has less than {self.settings.min_words} words"
                )
        words = entry.output.split(" ")
        if len(words) < self.settings.min_words:
            return EvaluationResultSkipped(
                details=f"Skipped because the output has less than {self.settings.min_words} words"
            )

        output_languages = detector.compute_language_confidence_values(entry.output)
        output_languages = dict(
            [
                (lang.language.iso_code_639_1.name, lang.value)
                for lang in output_languages
                if lang.value > self.settings.threshold
            ]
        )
        if len(output_languages) == 0:
            return EvaluationResultSkipped(
                details=f"Skipped because no language could be detected on the output with a confidence higher than {self.settings.threshold}"
            )

        if self.settings.check_for == "output_matches_language":
            passed = (
                self.settings.expected_language is None
                or self.settings.expected_language not in output_languages
            )
            return LinguaLanguageDetectionResult(
                score=len(output_languages),
                passed=passed,
                details=f"Languages detected: {', '.join(output_languages.keys())}",
                raw_response=LinguaLanguageDetectionRawResponse(
                    output=output_languages
                ),
            )

        input_languages = detector.compute_language_confidence_values(entry.input)
        input_languages = dict(
            [
                (lang.language.iso_code_639_1.name, lang.value)
                for lang in input_languages
                if lang.value > self.settings.threshold
            ]
        )
        if len(input_languages) == 0:
            return EvaluationResultSkipped(
                details=f"Skipped because no language could be detected on the input with a confidence higher than {self.settings.threshold}"
            )

        passed = any(lang in input_languages for lang in output_languages)
        details = "" if passed else "Input and output languages do not match. "
        if self.settings.expected_language is not None:
            passed = passed and self.settings.expected_language in output_languages
            if not passed:
                details = f"Input and output do not match the expected language: {self.settings.expected_language}. "

        return LinguaLanguageDetectionResult(
            score=len(output_languages | input_languages),
            passed=passed,
            details=f"{details}Input languages detected: {', '.join(input_languages.keys())}. Output languages detected: {', '.join(output_languages.keys())}",
            raw_response=LinguaLanguageDetectionRawResponse(
                output=output_languages, input=input_languages
            ),
        )
