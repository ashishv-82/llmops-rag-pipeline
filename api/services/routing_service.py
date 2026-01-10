"""Intelligent LLM Routing Service for cost optimization.

Routes queries to appropriate model tier (lite/pro) based on complexity and domain.
Reduces costs by using cheaper models for simple queries.
"""
import re
from typing import Literal
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

ModelTier = Literal['lite', 'pro']

class RoutingService:
    """Routes queries to lite or pro models based on complexity and domain requirements."""
    
    def __init__(self):
        # Complexity thresholds
        self.word_count_threshold = 50
        self.sentence_count_threshold = 3
        
        # Domain-specific routing rules
        # Legal: defaults to 'pro' for accuracy
        # HR/Engineering/General: defaults to 'lite' for cost savings
        self.domain_routing = {
            'legal': {
                'default': 'pro',  # Legal queries need high accuracy
                'simple_threshold': 20  # Very short legal queries can use lite
            },
            'hr': {
                'default': 'lite',  # HR queries are typically simpler
                'complex_threshold': 100  # Long HR queries need pro
            },
            'engineering': {
                'default': 'lite',
                'complex_threshold': 75
            },
            'history': {
                'default': 'lite',
                'complex_threshold': 50
            },
            'general': {
                'default': 'lite',
                'complex_threshold': 50
            }
        }
    
    def analyze_complexity(self, query: str, domain: str = 'general') -> dict:
        """
        Determine which model to use based on query complexity and domain.
        Returns dict with model_tier and model_id.
        """
        # Get domain config
        config = self.domain_routing.get(domain, self.domain_routing['general'])
        
        # Word count
        words = word_tokenize(query.lower())
        word_count = len(words)
        
        # Sentence count
        sentences = sent_tokenize(query)
        sentence_count = len(sentences)
        
        # Check for complex patterns that indicate need for pro model
        has_technical_terms = self._has_technical_terms(query)
        has_multiple_questions = query.count('?') > 1
        has_conditional = bool(re.search(r'\b(if|when|unless|provided|assuming)\b', query.lower()))
        
        tier = 'lite'
        reason = "Default complexity"

        # Domain-specific logic
        if domain == 'legal':
            # Legal: default to pro unless very simple
            if word_count < config['simple_threshold'] and not has_conditional:
                tier = 'lite'
                reason = "Simple legal query"
            else:
                tier = 'pro'
                reason = "Complex legal query"
        
        elif domain == 'hr':
            # HR: default to lite unless complex
            if word_count > config['complex_threshold'] or has_multiple_questions:
                tier = 'pro'
                reason = "Complex HR query"
            else:
                tier = 'lite'
                reason = "Simple HR query"
        
        else:
            # General/Engineering: complexity-based scoring
            complexity_score = (
                (word_count > config['complex_threshold']) * 2 +
                (sentence_count > self.sentence_count_threshold) * 1 +
                has_technical_terms * 1 +
                has_multiple_questions * 1 +
                has_conditional * 1
            )
            
            if complexity_score >= 3:
                tier = 'pro'
                reason = f"High complexity score: {complexity_score}"
            else:
                tier = 'lite'
                reason = f"Low complexity score: {complexity_score}"
        
        # Map tier to Model ID
        model_id = (
            "anthropic.claude-3-sonnet-20240229-v1:0" if tier == "pro" 
            else "global.amazon.nova-2-lite-v1:0"
        )

        return {
            "model_tier": tier,
            "model_id": model_id,
            "reason": reason
        }
    
    def _has_technical_terms(self, query: str) -> bool:
        """Check for technical terminology"""
        technical_indicators = [
            'algorithm', 'implementation', 'architecture', 'deployment',
            'configuration', 'infrastructure', 'optimization', 'integration',
            'compliance', 'regulation', 'statute', 'provision'
        ]
        query_lower = query.lower()
        return any(term in query_lower for term in technical_indicators)

    def get_available_domains(self) -> list[str]:
        """Return list of supported domains"""
        domains = list(self.domain_routing.keys())
        domains.insert(0, "all") # Add global search option
        return domains

routing_service = RoutingService()