"""Domain-specific system and user prompt templates for RAG queries"""

# Configuration for different domain assistants (Legal, HR, Engineering, etc.)
DOMAIN_PROMPTS = {
    "legal": {
        "system": """You are a legal document assistant. Provide precise, citation-based answers.
Always reference specific sections or clauses. Use formal legal terminology.
If uncertain, state limitations clearly.""",
        "user_template": """Based on the following legal documents:

{context}

Question: {question}

Provide a detailed answer with specific citations.""",
    },
    "hr": {
        "system": """You are an HR policy assistant. Provide clear, empathetic guidance.
Focus on employee welfare and company policy compliance.
Use accessible language.""",
        "user_template": """Based on the following HR policies:

{context}

Question: {question}

Provide a helpful, policy-compliant answer.""",
    },
    "engineering": {
        "system": """You are a technical documentation assistant. Provide accurate, actionable guidance.
Include code examples when relevant. Focus on best practices.""",
        "user_template": """Based on the following technical documentation:

{context}

Question: {question}

Provide a technical answer with examples if applicable.""",
    },
    "general": {
        "system": """You are a helpful assistant. Answer questions based on the provided context.
Be concise and accurate.""",
        "user_template": """Context:

{context}

Question: {question}

Answer:""",
    },
}


def get_prompt(domain: str, context: str, question: str) -> tuple[str, str]:
    """Get formatted system and user prompts based on domain and context"""
    # Fallback to general domain if specified domain is not found
    template = DOMAIN_PROMPTS.get(domain, DOMAIN_PROMPTS["general"])
    system_prompt = template["system"]
    # Inject search context and user query into the template
    user_prompt = template["user_template"].format(context=context, question=question)
    return system_prompt, user_prompt
