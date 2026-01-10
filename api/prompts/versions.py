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
                name='Balanced Legal',
                system_prompt="""You are a legal document assistant. Provide concise, citation-based answers.
Always reference specific sections or clauses using numeric tags like [1], [2], referencing the source order below.
Provide a high-level summary rather than an exhaustive research-style answer.""",
                user_template="""Based on the following legal documents:

{context}

Question: {question}

Provide a concise answer with numeric citations (e.g., [1]).""",
                created_at=datetime(2026, 1, 1),
                weight=1.0
            )
        }
        
        # HR domain versions
        self.versions['hr'] = {
            'v1': PromptVersion(
                version_id='hr_v1',
                name='Balanced HR',
                system_prompt="""You are an HR Policy Assistant. Provide clear, empathetic, and concise guidance.
Focus on high-level summaries. Always include numeric citations like [1], [2] to relevant policy sections from the context.
Provide a high-level summary rather than an exhaustive research-style answer.""",
                user_template="""Policy Sections:
{context}

Employee Question: {question}

Guidance (concise with numeric citations like [1]):""",
                created_at=datetime(2026, 1, 10),
                weight=1.0
            )
        }
        
        # General domain versions
        self.versions['general'] = {
            'v1': PromptVersion(
                version_id='general_v1',
                name='Balanced General',
                system_prompt="""You are a helpful AI assistant. Provide concise, high-level summaries based on the provided context.
Always include numeric citations like [1], [2], referring to the sources in the context. Avoid exhaustive research-style answers.""",
                user_template="""Context:
{context}

Question: {question}

Answer (concise with numeric citations like [1]):""",
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
