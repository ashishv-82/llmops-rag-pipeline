import json
import os
from api.evaluation.test_suite import EvaluationTestSuite

# Mock test cases
test_cases = [
    {
        "question": "What is the standard procedure for onboarding?",
        "expected_answer": "The standard onboarding procedure includes document verification, IT setup, and HR orientation.",
        "domain": "hr"
    }
]

# Write mock test cases to file
with open('tests/mock_test_cases.json', 'w') as f:
    json.dump(test_cases, f)

print("Created mock test cases.")

# Run evaluation suite
# We mock the RAG service and embedding service calls internally if possible?
# But here we want to test integration. Since we don't have Minikube running with Redis yet,
# the RAG service might fail.
# So we need to handle that or ensure RAGService mocks dependencies if they are missing.
# For now, let's just try running it and see if imports and logic structure hold up.
# The RAG service will likely try to connect to Redis/LLM.
# If connection fails, it might throw exception, which our test suite catches.

# Set PYTHONPATH to include root
import sys
sys.path.append(os.getcwd())

suite = EvaluationTestSuite('tests/mock_test_cases.json')
print("Initialized test suite.")

report = suite.run_evaluation(domain="hr")
print("Report generated:")
print(json.dumps(report, indent=2))

# Generate HTML
from scripts.generate_eval_report import generate_report
generate_report(report, "tests/mock_report.html")
print("HTML report generated at tests/mock_report.html")
