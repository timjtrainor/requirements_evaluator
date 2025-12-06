"""Evaluation harness for the AI Requirements Quality Evaluator.

Loads an evaluation dataset, calls Bedrock for each sample, compares AI output
to expected labels, and computes accuracy metrics.
"""

import json
import os
import sys
from textwrap import dedent
from typing import Any

import boto3

from config import Config, validate_response_schema

# Initialize Bedrock client using configuration
bedrock_client = boto3.client("bedrock-runtime", region_name=Config.get_bedrock_region())


def build_evaluation_prompt(requirement_text: str) -> str:
    """Build the prompt for Bedrock to evaluate the requirement."""
    return dedent(
        f"""
        You are an expert software requirements analyst. Analyze the following
        software requirement and provide a structured evaluation.

        Requirement to evaluate:
        "{requirement_text}"

        Evaluate the requirement and respond with ONLY valid JSON in this exact format:
        {{
            "ambiguity_detected": true/false,
            "ambiguity_details": "explanation of any ambiguous terms or phrases, or 'None' if clear",
            "testable": true/false,
            "testability_details": "explanation of whether the requirement can be objectively tested",
            "completeness_score": 1-10,
            "completeness_details": "explanation of what information may be missing",
            "issues": ["list", "of", "specific", "issues"],
            "suggestions": ["list", "of", "improvement", "suggestions"]
        }}

        Respond with ONLY the JSON object, no additional text.
        """
    ).strip()


def call_bedrock(requirement_text: str) -> dict:
    """Call Amazon Bedrock to evaluate the requirement."""
    prompt = build_evaluation_prompt(requirement_text)

    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2
    }

    response = bedrock_client.invoke_model(
        modelId=Config.get_model_id(),
        contentType="application/json",
        accept="application/json",
        body=json.dumps(request_body)
    )

    response_body = json.loads(response["body"].read())
    content = response_body.get("content", [{}])[0].get("text", "")

    try:
        evaluation = json.loads(content)
        
        # Validate the response schema
        is_valid, error_msg = validate_response_schema(evaluation)
        if not is_valid:
            print(f"Warning: Schema validation failed: {error_msg}")
        
        return evaluation
    except json.JSONDecodeError:
        return None


def evaluate_sample(sample: dict) -> dict:
    """
    Evaluate a single sample and compare to expected results.

    Args:
        sample: Dictionary with 'requirement', 'expected' keys

    Returns:
        Dictionary with evaluation results and comparison
    """
    requirement = sample.get("requirement", "")
    expected = sample.get("expected", {})

    print(f"\nEvaluating: {requirement[:60]}...")

    try:
        ai_output = call_bedrock(requirement)

        if ai_output is None:
            return {
                "requirement": requirement,
                "status": "error",
                "error": "Failed to parse AI response"
            }

        # Compare results
        results = {
            "requirement": requirement,
            "status": "success",
            "ai_output": ai_output,
            "expected": expected,
            "comparisons": {},
        }

        # Compare ambiguity
        if "ambiguity_detected" in expected:
            ai_ambiguity = ai_output.get("ambiguity_detected")
            expected_ambiguity = expected["ambiguity_detected"]
            results["comparisons"]["ambiguity"] = {
                "ai": ai_ambiguity,
                "expected": expected_ambiguity,
                "match": ai_ambiguity == expected_ambiguity,
            }

        # Compare testability
        if "testable" in expected:
            ai_testable = ai_output.get("testable")
            expected_testable = expected["testable"]
            results["comparisons"]["testability"] = {
                "ai": ai_testable,
                "expected": expected_testable,
                "match": ai_testable == expected_testable,
            }

        # Compare completeness (within threshold)
        if "completeness_score" in expected:
            ai_score = ai_output.get("completeness_score", 0)
            expected_score = expected["completeness_score"]
            threshold = expected.get("completeness_threshold", 2)
            within_threshold = abs(ai_score - expected_score) <= threshold
            results["comparisons"]["completeness"] = {
                "ai": ai_score,
                "expected": expected_score,
                "threshold": threshold,
                "within_threshold": within_threshold,
            }

        return results

    except Exception as e:  # noqa: BLE001
        return {
            "requirement": requirement,
            "status": "error",
            "error": str(e),
        }


def compute_metrics(results: list[dict]) -> dict:
    """
    Compute accuracy metrics from evaluation results.

    Args:
        results: List of evaluation result dictionaries

    Returns:
        Dictionary with computed metrics
    """
    metrics = {
        "total_samples": len(results),
        "successful_evaluations": 0,
        "errors": 0,
        "ambiguity": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
        "testability": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
        "completeness": {"within_threshold": 0, "outside_threshold": 0},
    }

    for result in results:
        if result.get("status") == "error":
            metrics["errors"] += 1
            continue

        metrics["successful_evaluations"] += 1
        comparisons = result.get("comparisons", {})

        # Ambiguity metrics
        if "ambiguity" in comparisons:
            amb = comparisons["ambiguity"]
            ai_val = amb.get("ai")
            exp_val = amb.get("expected")

            if ai_val is True and exp_val is True:
                metrics["ambiguity"]["tp"] += 1
            elif ai_val is False and exp_val is False:
                metrics["ambiguity"]["tn"] += 1
            elif ai_val is True and exp_val is False:
                metrics["ambiguity"]["fp"] += 1
            elif ai_val is False and exp_val is True:
                metrics["ambiguity"]["fn"] += 1

        # Testability metrics
        if "testability" in comparisons:
            test = comparisons["testability"]
            ai_val = test.get("ai")
            exp_val = test.get("expected")

            if ai_val is True and exp_val is True:
                metrics["testability"]["tp"] += 1
            elif ai_val is False and exp_val is False:
                metrics["testability"]["tn"] += 1
            elif ai_val is True and exp_val is False:
                metrics["testability"]["fp"] += 1
            elif ai_val is False and exp_val is True:
                metrics["testability"]["fn"] += 1

        # Completeness metrics
        if "completeness" in comparisons:
            comp = comparisons["completeness"]
            if comp.get("within_threshold"):
                metrics["completeness"]["within_threshold"] += 1
            else:
                metrics["completeness"]["outside_threshold"] += 1

    # Calculate accuracy rates
    for category in ["ambiguity", "testability"]:
        cat_metrics = metrics[category]
        total = cat_metrics["tp"] + cat_metrics["tn"] + cat_metrics["fp"] + cat_metrics["fn"]
        if total > 0:
            cat_metrics["accuracy"] = (cat_metrics["tp"] + cat_metrics["tn"]) / total
            cat_metrics["precision"] = (
                cat_metrics["tp"] / (cat_metrics["tp"] + cat_metrics["fp"])
                if (cat_metrics["tp"] + cat_metrics["fp"]) > 0
                else 0
            )
            cat_metrics["recall"] = (
                cat_metrics["tp"] / (cat_metrics["tp"] + cat_metrics["fn"])
                if (cat_metrics["tp"] + cat_metrics["fn"]) > 0
                else 0
            )

    # Completeness accuracy
    comp_total = metrics["completeness"]["within_threshold"] + metrics["completeness"]["outside_threshold"]
    if comp_total > 0:
        metrics["completeness"]["accuracy"] = (
            metrics["completeness"]["within_threshold"] / comp_total
        )

    return metrics


def print_results(metrics: dict) -> None:
    """Print formatted evaluation results."""
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)

    print(f"\nTotal samples: {metrics['total_samples']}")
    print(f"Successful evaluations: {metrics['successful_evaluations']}")
    print(f"Errors: {metrics['errors']}")

    print("\n--- Ambiguity Detection ---")
    amb = metrics["ambiguity"]
    print(f"  True Positives:  {amb['tp']}")
    print(f"  True Negatives:  {amb['tn']}")
    print(f"  False Positives: {amb['fp']}")
    print(f"  False Negatives: {amb['fn']}")
    if "accuracy" in amb:
        print(f"  Accuracy:  {amb['accuracy']:.2%}")
        print(f"  Precision: {amb['precision']:.2%}")
        print(f"  Recall:    {amb['recall']:.2%}")

    print("\n--- Testability Detection ---")
    test = metrics["testability"]
    print(f"  True Positives:  {test['tp']}")
    print(f"  True Negatives:  {test['tn']}")
    print(f"  False Positives: {test['fp']}")
    print(f"  False Negatives: {test['fn']}")
    if "accuracy" in test:
        print(f"  Accuracy:  {test['accuracy']:.2%}")
        print(f"  Precision: {test['precision']:.2%}")
        print(f"  Recall:    {test['recall']:.2%}")

    print("\n--- Completeness Score ---")
    comp = metrics["completeness"]
    print(f"  Within threshold:  {comp['within_threshold']}")
    print(f"  Outside threshold: {comp['outside_threshold']}")
    if "accuracy" in comp:
        print(f"  Accuracy: {comp['accuracy']:.2%}")

    print("\n" + "=" * 60)


def main() -> None:
    """Main entry point for the evaluation harness."""
    # Load dataset
    dataset_path = os.environ.get("EVAL_DATASET", "eval_dataset.json")

    if not os.path.exists(dataset_path):
        print(f"Error: Dataset file not found: {dataset_path}")
        sys.exit(1)

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    samples = dataset.get("samples", [])
    print(f"Loaded {len(samples)} samples from {dataset_path}")

    # Evaluate each sample
    results = []
    for i, sample in enumerate(samples, 1):
        print(f"\n[{i}/{len(samples)}]", end="")
        result = evaluate_sample(sample)
        results.append(result)

    # Compute and print metrics
    metrics = compute_metrics(results)
    print_results(metrics)

    # Optionally save detailed results
    output_path = os.environ.get("EVAL_OUTPUT")
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"results": results, "metrics": metrics}, f, indent=2)
        print(f"\nDetailed results saved to: {output_path}")

if __name__ == "__main__":
    main()

