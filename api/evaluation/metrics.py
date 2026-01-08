from typing import List, Dict, Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.translate.bleu_score import sentence_bleu

class EvaluationMetrics:
    def __init__(self):
        # Ensure NLTK data is available
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
    
    def relevance_score(
        self,
        answer: str,
        context: str,
        answer_embedding: List[float],
        context_embedding: List[float]
    ) -> float:
        """
        Measure how relevant the answer is to the context.
        Uses cosine similarity of embeddings.
        """
        if not answer_embedding or not context_embedding:
            return 0.0
            
        similarity = cosine_similarity(
            [answer_embedding],
            [context_embedding]
        )[0][0]
        return float(similarity)
    
    def coherence_score(self, answer: str) -> float:
        """
        Measure answer coherence (simple heuristic).
        Checks for complete sentences, proper punctuation.
        """
        if not answer:
            return 0.0
            
        try:
            sentences = nltk.sent_tokenize(answer)
        except Exception:
            # Fallback if tokenizer fails
            sentences = [s for s in answer.split('.') if s.strip()]
        
        if not sentences:
            return 0.0
        
        # Check if sentences end with proper punctuation
        proper_endings = sum(
            1 for s in sentences
            if s.strip() and s.strip()[-1] in '.!?'
        )
        
        coherence = proper_endings / len(sentences)
        return coherence
    
    def accuracy_score(
        self,
        answer: str,
        reference_answer: str
    ) -> float:
        """
        Measure accuracy against reference answer using BLEU score.
        """
        if not reference_answer:
            return 0.0
            
        reference_tokens = nltk.word_tokenize(reference_answer.lower())
        answer_tokens = nltk.word_tokenize(answer.lower())
        
        # Smoothing function to avoid 0.0 when n-gram overlaps are missing
        from nltk.translate.bleu_score import SmoothingFunction
        chencherry = SmoothingFunction()
        
        bleu = sentence_bleu(
            [reference_tokens], 
            answer_tokens,
            smoothing_function=chencherry.method1
        )
        return bleu
    
    def calculate_all(
        self,
        answer: str,
        context: str,
        answer_embedding: List[float],
        context_embedding: List[float],
        reference_answer: Optional[str] = None
    ) -> Dict[str, float]:
        """Calculate all quality metrics"""
        metrics = {
            'relevance': self.relevance_score(
                answer, context, answer_embedding, context_embedding
            ),
            'coherence': self.coherence_score(answer)
        }
        
        if reference_answer:
            metrics['accuracy'] = self.accuracy_score(answer, reference_answer)
        
        return metrics

evaluator = EvaluationMetrics()
