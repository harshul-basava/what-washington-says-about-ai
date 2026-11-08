"""Shared federal X query and checkpoint identity for collection and coverage."""
import hashlib
import json

KEYWORDS = '(AI OR "artificial intelligence" OR AGI OR superintelligence OR "super intelligence" OR OpenAI OR Anthropic OR "AI chips" OR "export controls" OR "FRONTIER Act" OR "Kill Switch Act" OR "Stop Stealing Our Chips" OR "independent verification")'


def fingerprint(account):
    # A changed query or sourced account definition requires a fresh search.
    return hashlib.sha256((json.dumps(account, sort_keys=True) + KEYWORDS).encode()).hexdigest()
