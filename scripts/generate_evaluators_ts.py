import inspect
import json
import os
from typing import Any, Dict, Literal, Optional, Union, get_args, get_origin
from langevals_core.base_evaluator import (
    EvalCategories,
    EvaluationResult,
)

from pydantic import BaseModel
from langevals.utils import (
    EvaluatorDefinitions,
    get_evaluator_classes,
    get_evaluator_definitions,
    load_evaluator_modules,
)

os.system("npm list -g prettier &> /dev/null || npm install -g prettier")


def stringify_field_types(field_types):
    if len(field_types) == 0:
        return "Record<string, never>"

    settings = "{\n"
    for field_name, field_type in field_types.items():
        settings += f"        {field_name}: {field_type};\n"
    settings += "      }"

    return settings


def extract_evaluator_info(definitions: EvaluatorDefinitions) -> Dict[str, Any]:
    evaluator_info = {
        "name": definitions.name,
        "description": definitions.description,
        "category": definitions.category,
        "docsUrl": definitions.docs_url,
        "isGuardrail": definitions.is_guardrail,
        "settingsTypes": {},
        "settingsDescriptions": {},
        "result": {},
    }

    def get_field_type_to_typescript(field):
        if inspect.isclass(field) and issubclass(field, BaseModel):
            return stringify_field_types(
                {
                    field_name: get_field_type_to_typescript(field.annotation)
                    for field_name, field in field.model_fields.items()
                }
            )
        if field == str:
            return "string"
        elif field == int:
            return "number"
        elif field == float:
            return "number"
        elif field == bool:
            return "boolean"
        elif get_origin(field) == Literal:
            return " | ".join([f'"{value}"' for value in get_args(field)])
        elif get_origin(field) == Optional:
            return get_field_type_to_typescript(get_args(field)[0]) + " | undefined"
        elif get_origin(field) == Union:
            return " | ".join(
                [get_field_type_to_typescript(arg) for arg in get_args(field)]
            )
        elif get_origin(field) == list:
            return get_field_type_to_typescript(get_args(field)[0]) + "[]"
        elif field == type(None):
            return "undefined"

        raise ValueError(
            f"Unsupported field type for typescript conversion: {field} on {definitions.category}/{definitions.evaluator_name} settings"
        )

    for field_name, field in definitions.settings_type.model_fields.items():
        default = (
            field.default.model_dump()
            if isinstance(field.default, BaseModel)
            else field.default
        )
        evaluator_info["settingsDescriptions"][field_name] = {
            "description": field.description,
            "default": default,
        }
        evaluator_info["settingsTypes"][field_name] = get_field_type_to_typescript(
            field.annotation
        )

    base_score_description = EvaluationResult.model_fields["score"].description
    score_field = definitions.result_type.model_fields.get("score")
    if (
        score_field
        and score_field.description
        and score_field.description != base_score_description
    ):
        evaluator_info["result"]["score"] = {"description": score_field.description}

    base_passed_description = EvaluationResult.model_fields["passed"].description
    passed_field = definitions.result_type.model_fields.get("passed")
    if (
        passed_field
        and passed_field.description
        and passed_field.description != base_passed_description
    ):
        evaluator_info["result"]["passed"] = {"description": passed_field.description}

    return evaluator_info


def generate_typescript_definitions(evaluators_info: Dict[str, Dict[str, Any]]) -> str:
    categories_union = " | ".join([f'"{value}"' for value in get_args(EvalCategories)])
    ts_definitions = (
        f"export type EvaluatorDefinition<T extends EvaluatorTypes> = {{\n"
        f"    name: string;\n"
        f"    description: string;\n"
        f"    category: {categories_union};\n"
        f"    docsUrl?: string;\n"
        f"    isGuardrail: boolean;\n"
        f"    settings: {{\n"
        f'        [K in keyof Evaluators[T]["settings"]]: {{\n'
        f"        description?: string;\n"
        f'        default: Evaluators[T]["settings"][K];\n'
        f"        }};\n"
        f"    }};\n"
        f"    result: {{\n"
        f"        score?: {{\n"
        f"        description: string;\n"
        f"        }};\n"
        f"        passed?: {{\n"
        f"        description: string;\n"
        f"        }};\n"
        f"    }};\n"
        f"}};\n\n"
        f"export type EvaluatorTypes = keyof Evaluators;\n\n"
    )
    ts_definitions += "export type Evaluators = {\n"
    for evaluator_name, evaluator_info in evaluators_info.items():
        ts_definitions += f'  "{evaluator_name}": {{\n'
        ts_definitions += (
            f"    settings: {stringify_field_types(evaluator_info['settingsTypes'])};\n"
        )
        ts_definitions += (
            f'    result: {json.dumps(evaluator_info["result"], indent=6)};\n'
        )
        ts_definitions += "  };\n"
    ts_definitions += "};\n\n"

    ts_definitions += "export const AVAILABLE_EVALUATORS: {\n"
    ts_definitions += "  [K in EvaluatorTypes]: EvaluatorDefinition<K>;\n"
    ts_definitions += "} = {\n"
    for evaluator_name, evaluator_info in evaluators_info.items():
        ts_definitions += f'  "{evaluator_name}": {{\n'
        ts_definitions += f'    name: `{evaluator_info["name"]}`,\n'
        ts_definitions += f'    description: `{evaluator_info["description"]}`,\n'
        ts_definitions += f'    category: "{evaluator_info["category"]}",\n'
        ts_definitions += f'    docsUrl: "{evaluator_info["docsUrl"]}",\n'
        ts_definitions += (
            f'    isGuardrail: {str(evaluator_info["isGuardrail"]).lower()},\n'
        )
        ts_definitions += f'    settings: {json.dumps(evaluator_info["settingsDescriptions"], indent=6).replace(": null", ": undefined")},\n'
        ts_definitions += (
            f'    result: {json.dumps(evaluator_info["result"], indent=6)}\n'
        )
        ts_definitions += "  },\n"
    ts_definitions += "};\n"

    return ts_definitions


def main():
    evaluators = load_evaluator_modules()
    evaluators_info = {}

    for _, evaluator_module in evaluators.items():
        for evaluator_cls in get_evaluator_classes(evaluator_module):
            definitions = get_evaluator_definitions(evaluator_cls)
            evaluator_info = extract_evaluator_info(definitions)
            evaluators_info[
                f"{definitions.module_name}/{definitions.evaluator_name}"
            ] = evaluator_info

    ts_content = generate_typescript_definitions(evaluators_info)

    with open("ts-integration/evaluators.generated.ts", "w") as ts_file:
        ts_file.write(ts_content)

    os.system("prettier ts-integration/evaluators.generated.ts --write &> /dev/null")

    print("TypeScript definitions generated successfully.")


if __name__ == "__main__":
    main()
