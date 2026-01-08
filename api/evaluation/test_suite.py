from typing import List, Dict, Any
import json
import numpy as np
from api.services.rag_service import RAGService
from api.evaluation.metrics import evaluator
from api.services.embedding_service import embedding_service

rag_service = RAGService()

class EvaluationTestSuite:
    def __init__(self, test_cases_file: str):
        self.test_cases_file = test_cases_file
        with open(test_cases_file, 'r') as f:
            self.test_cases = json.load(f)
    
    def run_evaluation(self, domain: str = None) -> Dict[str, Any]:
        """Run evaluation on test cases"""
        results = []
        
        for test_case in self.test_cases:
            if domain and test_case.get('domain') != domain:
                continue
            
            question = test_case['question']
            expected_answer = test_case.get('expected_answer')
            test_domain = test_case.get('domain', 'general')
            
            try:
                # Get RAG response
                response = rag_service.query(question, domain=test_domain)
                
                # Generate embeddings for evaluation
                answer_embedding = embedding_service.generate_embedding(response['answer'])
                
                # Handling sources which might be a list of dictionaries or strings
                context_str = ""
                if isinstance(response.get('sources'), list):
                    # Extract text content from sources if they are dicts, or join if strings
                    context_parts = []
                    for s in response['sources']:
                        if isinstance(s, dict):
                            context_parts.append(str(s.get('text', s)))
                        else:
                            context_parts.append(str(s))
                    context_str = "\n".join(context_parts)
                else:
                    context_str = str(response.get('sources', ''))

                context_embedding = embedding_service.generate_embedding(context_str)
                
                # Calculate metrics
                metrics = evaluator.calculate_all(
                    answer=response['answer'],
                    context=context_str,
                    answer_embedding=answer_embedding,
                    context_embedding=context_embedding,
                    reference_answer=expected_answer
                )
                
                results.append({
                    'question': question,
                    'answer': response['answer'],
                    'metrics': metrics,
                    'cost': response.get('cost', 0),
                    'latency_ms': response.get('execution_time_ms', 0),
                    'model_used': response.get('model_tier', 'unknown')
                })
            except Exception as e:
                print(f"Error evaluating case '{question}': {e}")
                continue
        
        return self._generate_report(results)
    
    def _generate_report(self, results: List[Dict]) -> Dict:
        """Generate evaluation report"""
        if not results:
            return {}
        
        avg_metrics = {
            'relevance': np.mean([r['metrics']['relevance'] for r in results]),
            'coherence': np.mean([r['metrics']['coherence'] for r in results]),
            'cost': np.mean([r['cost'] for r in results]),
            'latency_ms': np.mean([r['latency_ms'] for r in results])
        }
        
        # Check if accuracy is available in the first result
        if 'accuracy' in results[0]['metrics']:
            avg_metrics['accuracy'] = np.mean([
                r['metrics']['accuracy'] for r in results
                if 'accuracy' in r['metrics']
            ])
        
        return {
            'summary': avg_metrics,
            'total_tests': len(results),
            'detailed_results': results
        }
