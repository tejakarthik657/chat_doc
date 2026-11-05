"""
smart package — SMART Backend Services OAuth 2.0 Client Assertion & Token Manager.
"""
from app.integrations.smart.jwt_assertion import generate_client_assertion
from app.integrations.smart.token_manager import token_manager
from app.integrations.smart.smart_auth import smart_authenticator

__all__ = [
    "generate_client_assertion",
    "token_manager",
    "smart_authenticator",
]
