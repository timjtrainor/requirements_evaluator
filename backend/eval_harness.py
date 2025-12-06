"""Evaluation harness for the AI Requirements Quality Evaluator.

Loads an evaluation dataset, calls Bedrock for each sample, compares AI output
to expected labels, and computes accuracy metrics.
"""

import json
import os
import sys
from textwrap import dedent
from typing import Any, Dict, List, Optional

import boto3

from config import get_config, validate_response_schema

# Get configuration singleton
config = get_config()

# Initialize Bedrock client using configuration
bedrock_client = boto3.client(
    "bedrock-runtime",
    region_name=config.bedrock_region,
    config=boto3.session.Config(
        connect_timeout=config.bedrock_timeout,
        read_timeout=config.bedrock_timeout,
    )
)


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


def call_bedrock(requirement_text: str) -> Optional[Dict[str, Any]]:
    """Call Amazon Bedrock to evaluate the requirement."""
    prompt = build_evaluation_prompt(requirement_text)

    model_id = config.bedrock_model_id

    if model_id.startswith("openai."):
        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": config.model_temperature,
            "max_tokens": config.model_max_tokens,
        }
    else:
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": config.model_max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt,
                        }
                    ],
                }
            ],
            "temperature": config.model_temperature
        }

    response = bedrock_client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(request_body)
    )

    response_body = json.loads(response["body"].read())

    if model_id.startswith("openai."):
        first_choice = response_body.get("choices", [{}])[0]
        message = first_choice.get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            content = "".join(block.get("text", "") for block in content if isinstance(block, dict))
    else:
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


def evaluate_sample(sample: Dict[str, Any]) -> Dict[str, Any]:
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


def compute_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
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


def print_results(metrics: Dict[str, Any]) -> None:
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


def load_edge_cases() -> List[Dict[str, Any]]:
    """
    Load additional edge case test samples for comprehensive validation.

    Returns:
        List of edge case samples with expected results
    """
    return [
        {
            "requirement": "The system shall be fast.",
            "expected": {
                "ambiguity_detected": True,
                "testable": False,
                "completeness_score": 2,
                "completeness_threshold": 3
            }
        },
        {
            "requirement": "The system shall respond within 2 seconds under normal load conditions with up to 100 concurrent users.",
            "expected": {
                "ambiguity_detected": False,
                "testable": True,
                "completeness_score": 8,
                "completeness_threshold": 2
            }
        },
        {
            "requirement": "",
            "expected": {
                "ambiguity_detected": None,
                "testable": None,
                "completeness_score": 0,
                "completeness_threshold": 0
            }
        },
        {
            "requirement": "x" * 6000,  # Too long
            "expected": {
                "ambiguity_detected": None,
                "testable": None,
                "completeness_score": 0,
                "completeness_threshold": 0
            }
        },
        {
            "requirement": "The system shall use encryption for all data transmissions and storage, complying with industry standards such as AES-256 for symmetric encryption and RSA-2048 for key exchange, with regular key rotation every 90 days.",
            "expected": {
                "ambiguity_detected": False,
                "testable": True,
                "completeness_score": 9,
                "completeness_threshold": 2
            }
        }
    ]


def validate_model_consistency(results: List[Dict[str, Any]], threshold: float = 0.8) -> Dict[str, Any]:
    """
    Validate model consistency across multiple runs.

    Args:
        results: List of evaluation results
        threshold: Minimum consistency threshold (0.0-1.0)

    Returns:
        Dictionary with consistency metrics
    """
    if len(results) < 2:
        return {"consistency_score": 1.0, "message": "Need at least 2 results for consistency check"}

    # Group results by requirement
    requirement_groups = {}
    for result in results:
        req = result.get("requirement", "")
        if req not in requirement_groups:
            requirement_groups[req] = []
        requirement_groups[req].append(result)

    consistency_scores = []
    for req, group_results in requirement_groups.items():
        if len(group_results) < 2:
            continue

        # Compare key metrics across runs
        scores = [r.get("ai_output", {}).get("completeness_score", 0) for r in group_results]
        ambiguities = [r.get("ai_output", {}).get("ambiguity_detected") for r in group_results]
        testabilities = [r.get("ai_output", {}).get("testable") for r in group_results]

        # Calculate consistency
        score_std = sum((s - sum(scores)/len(scores))**2 for s in scores) ** 0.5 if scores else 0
        ambiguity_consistent = len(set(ambiguities)) == 1 if ambiguities else True
        testability_consistent = len(set(testabilities)) == 1 if testabilities else True

        # Overall consistency score (0-1, higher is better)
        consistency = 1.0
        if scores:
            consistency *= max(0, 1 - score_std / 5)  # Penalize high variance
        if not ambiguity_consistent:
            consistency *= 0.8
        if not testability_consistent:
            consistency *= 0.8

        consistency_scores.append(consistency)

    avg_consistency = sum(consistency_scores) / len(consistency_scores) if consistency_scores else 1.0

    return {
        "consistency_score": avg_consistency,
        "passed": avg_consistency >= threshold,
        "message": f"Model consistency: {avg_consistency:.2%} ({'PASS' if avg_consistency >= threshold else 'FAIL'})"
    }


def run_ci_cd_validation() -> bool:
    """
    Run comprehensive validation suitable for CI/CD pipelines.

    Returns:
        True if all validations pass, False otherwise
    """
    print("Running CI/CD validation...")

    # Load main dataset
    dataset_path = os.environ.get("EVAL_DATASET", "eval_dataset.json")
    if not os.path.exists(dataset_path):
        print(f"❌ Dataset file not found: {dataset_path}")
        return False

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    samples = dataset.get("samples", [])
    print(f"Loaded {len(samples)} samples from {dataset_path}")

    # Add edge cases
    samples.extend(load_edge_cases())
    print(f"Total samples including edge cases: {len(samples)}")

    # Evaluate samples
    results = []
    for i, sample in enumerate(samples, 1):
        print(f"Evaluating sample {i}/{len(samples)}", end="\r")
        result = evaluate_sample(sample)
        results.append(result)

    print()  # New line after progress

    # Compute metrics
    metrics = compute_metrics(results)

    # Check thresholds
    thresholds = {
        "ambiguity_accuracy": 0.75,
        "testability_accuracy": 0.75,
        "completeness_accuracy": 0.70
    }

    passed = True
    print("\nCI/CD Validation Results:")
    print("=" * 50)

    for metric, threshold in thresholds.items():
        if metric in metrics.get("ambiguity", {}):
            value = metrics["ambiguity"].get(metric, 0)
        elif metric in metrics.get("testability", {}):
            value = metrics["testability"].get(metric, 0)
        elif metric in metrics.get("completeness", {}):
            value = metrics["completeness"].get(metric, 0)
        else:
            continue

        status = "✅ PASS" if value >= threshold else "❌ FAIL"
        print(f"{metric}: {value:.2%} (threshold: {threshold:.2%}) - {status}")
        if value < threshold:
            passed = False

    # Consistency check
    consistency = validate_model_consistency(results)
    print(f"Model consistency: {consistency['consistency_score']:.2%} - {'✅ PASS' if consistency['passed'] else '❌ FAIL'}")
    if not consistency['passed']:
        passed = False

    # Error rate check
    error_rate = metrics.get("errors", 0) / metrics.get("total_samples", 1)
    max_error_rate = 0.1  # 10% max errors
    error_status = "✅ PASS" if error_rate <= max_error_rate else "❌ FAIL"
    print(f"Error rate: {error_rate:.2%} (max: {max_error_rate:.2%}) - {error_status}")
    if error_rate > max_error_rate:
        passed = False

    print("=" * 50)
    print(f"Overall result: {'✅ ALL TESTS PASSED' if passed else '❌ SOME TESTS FAILED'}")

    # Save detailed results for CI/CD artifacts
    output_path = os.environ.get("EVAL_OUTPUT", "ci_cd_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "results": results,
            "metrics": metrics,
            "consistency": consistency,
            "passed": passed,
            "timestamp": __import__("time").time()
        }, f, indent=2)
    print(f"Detailed results saved to: {output_path}")

    return passed


def main() -> None:
    """Main entry point for the evaluation harness."""
    # Check if running in CI/CD mode
    if os.environ.get("CI_CD_MODE", "").lower() in ("true", "1", "yes"):
        success = run_ci_cd_validation()
        sys.exit(0 if success else 1)

    # Standard evaluation mode
    # Load dataset
    dataset_path = os.environ.get("EVAL_DATASET", "eval_dataset.json")

    if not os.path.exists(dataset_path):
        print(f"Error: Dataset file not found: {dataset_path}")
        sys.exit(1)

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    samples = dataset.get("samples", [])
    print(f"Loaded {len(samples)} samples from {dataset_path}")

    # Add edge cases for comprehensive testing
    if os.environ.get("INCLUDE_EDGE_CASES", "true").lower() in ("true", "1", "yes"):
        samples.extend(load_edge_cases())
        print(f"Total samples including edge cases: {len(samples)}")

    # Evaluate each sample
    results = []
    for i, sample in enumerate(samples, 1):
        print(f"\n[{i}/{len(samples)}]", end="")
        result = evaluate_sample(sample)
        results.append(result)

    # Compute and print metrics
    metrics = compute_metrics(results)
    print_results(metrics)

    # Validate consistency
    consistency = validate_model_consistency(results)
    print(f"\n{consistency['message']}")

    # Optionally save detailed results
    output_path = os.environ.get("EVAL_OUTPUT")
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "results": results,
                "metrics": metrics,
                "consistency": consistency
            }, f, indent=2)
        print(f"\nDetailed results saved to: {output_path}")

if __name__ == "__main__":
    main()
