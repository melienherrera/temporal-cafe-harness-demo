"""Temporal client connection — local dev server by default, Cloud-ready via env vars.

Env vars:
  TEMPORAL_ADDRESS    default "localhost:7233"      (Cloud: "<ns>.<acct>.tmprl.cloud:7233")
  TEMPORAL_NAMESPACE  default "default"             (Cloud: "<ns>.<acct>")
  TEMPORAL_API_KEY    if set, connects to Temporal Cloud over TLS with this API key
"""
import os

from temporalio.client import Client


async def get_client() -> Client:
    address = os.environ.get("TEMPORAL_ADDRESS", "localhost:7233")
    namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")
    api_key = os.environ.get("TEMPORAL_API_KEY")

    if api_key:
        # Temporal Cloud with an API key (TLS required).
        return await Client.connect(
            address, namespace=namespace, api_key=api_key, tls=True
        )

    # Local dev server (temporal server start-dev).
    return await Client.connect(address, namespace=namespace)
