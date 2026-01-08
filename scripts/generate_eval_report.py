import json
from jinja2 import Template
from datetime import datetime

REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>RAG Evaluation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        .metric-good { color: green; }
        .metric-bad { color: red; }
    </style>
</head>
<body>
    <h1>RAG Evaluation Report</h1>
    <p>Generated: {{ timestamp }}</p>
    
    <h2>Summary Metrics</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Average Value</th>
        </tr>
        {% for metric, value in summary.items() %}
        <tr>
            <td>{{ metric }}</td>
            <td>{{ "%.4f"|format(value) }}</td>
        </tr>
        {% endfor %}
    </table>
    
    <h2>Detailed Results</h2>
    <table>
        <tr>
            <th>Question</th>
            <th>Relevance</th>
            <th>Coherence</th>
            <th>Cost ($)</th>
            <th>Latency (ms)</th>
        </tr>
        {% for result in results %}
        <tr>
            <td>{{ result.question[:100] }}...</td>
            <td>{{ "%.2f"|format(result.metrics.relevance) }}</td>
            <td>{{ "%.2f"|format(result.metrics.coherence) }}</td>
            <td>{{ "%.6f"|format(result.cost) }}</td>
            <td>{{ result.latency_ms }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

def generate_report(eval_results: dict, output_file: str):
    template = Template(REPORT_TEMPLATE)
    
    html = template.render(
        timestamp=datetime.now().isoformat(),
        summary=eval_results.get('summary', {}),
        results=eval_results.get('detailed_results', [])
    )
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"Report generated: {output_file}")

if __name__ == "__main__":
    # Example usage / Test
    sample_results = {
        'summary': {'relevance': 0.85, 'coherence': 0.92, 'cost': 0.0012, 'latency_ms': 450},
        'detailed_results': [
            {
                'question': 'Test Question 1',
                'metrics': {'relevance': 0.9, 'coherence': 1.0},
                'cost': 0.0005,
                'latency_ms': 400
            }
        ]
    }
    generate_report(sample_results, "test_report.html")
