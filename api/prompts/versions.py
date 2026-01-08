from dataclasses import dataclass
from typing import Dict, List, Tuple
from datetime import datetime
import random

@dataclass
class PromptVersion:
    version_id: str
    name: str
    system_prompt: str
    user_template: str
    created_at: datetime
    active: bool = True
    weight: float = 1.0  # For A/B testing

class PromptVersionManager:
    """Manages prompt versions and A/B testing selection."""
    
    def __init__(self):
        self.versions: Dict[str, Dict[str, PromptVersion]] = {}
        self._load_versions()
    
    def _load_versions(self):
        """Load prompt versions from initial configuration."""
        # Legal domain versions
        self.versions['legal'] = {
            'v1': PromptVersion(
                version_id='legal_v1',
                name='Standard Legal',
                system_prompt="""You are a legal document assistant. Provide precise, citation-based answers.
Always reference specific sections or clauses. Use formal legal terminology.""",
                user_template="""Based on the following legal documents:

{context}

Question: {question}

Provide a detailed answer with specific citations.""",
                created_at=datetime(2026, 1, 1),
                weight=0.5
            ),
            'v2': PromptVersion(
                version_id='legal_v2',
                name='Concise Legal',
                system_prompt="""You are a legal document assistant. Provide concise, accurate answers with citations.
Focus on the most relevant information.""",
                user_template="""Legal Documents:

{context}

Question: {question}

Provide a concise answer with key citations only.""",
                created_at=datetime(2026, 1, 5),
                weight=0.5
            )
        }
        
        # General domain versions
        self.versions['general'] = {
            'v1': PromptVersion(
                version_id='general_v1',
                name='Standard General',
                system_prompt="""You are a helpful AI assistant. Answer questions based on the provided context.
If the answer is not in the context, say so.""",
                user_template="""Context:
{context}

Question: {question}

Answer:""",
                created_at=datetime(2026, 1, 1),
                weight=1.0
            )
        }
    
    def get_prompt(
        self,
        domain: str,
        context: str,
        question: str,
        version_id: str = None
    ) -> Tuple[str, str, str]:
        """
        Get prompt for domain. If version_id not specified, use A/B testing.
        Returns (system_prompt, user_prompt, version_id)
        """
        # Default to general if domain not found
        domain_versions = self.versions.get(domain, self.versions.get('general', {}))
        
        if not domain_versions:
            # Fallback if even general is missing (unlikely)
            return "", f"Context: {context}\n\nQuestion: {question}", "fallback"
        
        # Get specific version or select via weighted random
        if version_id and version_id in domain_versions:
            version = domain_versions[version_id]
        else:
            version = self._weighted_random_selection(domain_versions)
        
        system_prompt = version.system_prompt
        user_prompt = version.user_template.format(
            context=context,
            question=question
        )
        
        return system_prompt, user_prompt, version.version_id
    
    def _weighted_random_selection(
        self,
        versions: Dict[str, PromptVersion]
    ) -> PromptVersion:
        """Select version using weighted random sampling for A/B testing."""
        active_versions = [v for v in versions.values() if v.active]
        if not active_versions:
            raise ValueError("No active prompt versions available")
            
        weights = [v.weight for v in active_versions]
        
        # random.choices returns a list, we take the first item
        return random.choices(active_versions, weights=weights, k=1)[0]
    
    def add_version(self, domain: str, version: PromptVersion):
        """Add new prompt version."""
        if domain not in self.versions:
            self.versions[domain] = {}
        
        self.versions[domain][version.version_id] = version
    
    def deactivate_version(self, domain: str, version_id: str):
        """Deactivate a prompt version."""
        if domain in self.versions and version_id in self.versions[domain]:
            self.versions[domain][version_id].active = False

# Global instance
prompt_manager = PromptVersionManager()
