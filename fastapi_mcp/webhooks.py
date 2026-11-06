"""FastAPI-MCP Webhooks: Inbound Webhook Gateway with cryptographic verification.

Provides HMAC signature verification (SHA256, SHA1, SHA512), automatic route
registration, and webhook delivery lifecycle management for FastAPI and MCP.
"""

import hashlib
import hmac
import inspect
import json
import os
import re
from typing import Any, Callable, Dict, List, Optional, Union

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, Field


def verify_hmac_signature(
    payload: Union[bytes, str],
    secret: str,
    signature: str,
    algorithm: str = "sha256",
) -> bool:
    """Verify cryptographic HMAC signature of inbound webhook payload.

    Supports standard prefixes (e.g., 'sha256=', 'sha1=', 'v1='), constant-time
    comparison to prevent timing attacks, and multi-format signatures.
    """
    if not secret or not signature:
        return False

    raw_bytes = payload.encode("utf-8") if isinstance(payload, str) else payload

    # Normalize algorithm name
    algo_name = algorithm.lower().replace("-", "")
    if not hasattr(hashlib, algo_name):
        return False

    digest_mod = getattr(hashlib, algo_name)

    # Strip prefixes like 'sha256=', 'sha1=', 'sha512='
    cleaned_sig = signature.strip()
    prefix_match = re.match(r"^(?:sha\d+|v\d+)=([a-fA-F0-9]+)$", cleaned_sig)
    if prefix_match:
        cleaned_sig = prefix_match.group(1)

    # Stripe format: t=12345,v1=abcdef...
    if "t=" in signature and "v1=" in signature:
        parts = dict(re.findall(r"([a-z0-9]+)=([a-zA-Z0-9]+)", signature))
        if "v1" in parts:
            cleaned_sig = parts["v1"]
            if "t" in parts:
                timestamp = parts["t"]
                timestamped_payload = f"{timestamp}.".encode("utf-8") + raw_bytes
                computed_ts = hmac.new(
                    secret.encode("utf-8"), timestamped_payload, digest_mod
                ).hexdigest()
                if hmac.compare_digest(computed_ts.lower(), cleaned_sig.lower()):
                    return True

    # Standard direct HMAC computation
    try:
        computed = hmac.new(secret.encode("utf-8"), raw_bytes, digest_mod).hexdigest()
        return hmac.compare_digest(computed.lower(), cleaned_sig.lower())
    except (ValueError, TypeError):
        return False


class WebhookMetadata(BaseModel):
    """Metadata representation of a registered inbound webhook endpoint."""

    path: str = Field(..., description="HTTP URL path for the webhook")
    name: str = Field(..., description="Identifier name of the webhook")
    header: str = Field(..., description="HTTP header containing cryptographic signature")
    algorithm: str = Field(default="sha256", description="Digest algorithm")
    secret_env: Optional[str] = Field(default=None, description="Environment variable for secret")
    has_secret: bool = Field(default=False, description="Whether secret is configured")
    event_topic: Optional[str] = Field(default=None, description="Target event topic")
    description: str = Field(default="", description="Webhook description")


class WebhookDefinition:
    """Internal registry definition of a webhook endpoint and its handler."""

    def __init__(
        self,
        path: str,
        name: str,
        handler: Optional[Callable[..., Any]] = None,
        secret: Optional[str] = None,
        secret_env: Optional[str] = None,
        header: str = "X-Hub-Signature-256",
        algorithm: str = "sha256",
        event_topic: Optional[str] = None,
        description: str = "",
    ) -> None:
        self.path = path
        self.name = name
        self.handler = handler
        self.secret = secret
        self.secret_env = secret_env
        self.header = header
        self.algorithm = algorithm
        self.event_topic = event_topic
        self.description = description

    def get_secret(self) -> Optional[str]:
        """Resolve webhook secret from explicit value or environment variable."""
        if self.secret:
            return self.secret
        if self.secret_env:
            return os.getenv(self.secret_env)
        return None

    def to_metadata(self) -> WebhookMetadata:
        """Convert definition to exportable metadata model."""
        return WebhookMetadata(
            path=self.path,
            name=self.name,
            header=self.header,
            algorithm=self.algorithm,
            secret_env=self.secret_env,
            has_secret=self.get_secret() is not None,
            event_topic=self.event_topic,
            description=self.description,
        )


class WebhookManager:
    """Manages inbound webhook endpoints, signature verification, and dispatch."""

    def __init__(self) -> None:
        self._webhooks: Dict[str, WebhookDefinition] = {}
        self._delivery_history: List[Dict[str, Any]] = []

    def register(
        self,
        path: str,
        handler: Optional[Callable[..., Any]] = None,
        *,
        name: Optional[str] = None,
        secret: Optional[str] = None,
        secret_env: Optional[str] = None,
        header: str = "X-Hub-Signature-256",
        algorithm: str = "sha256",
        event_topic: Optional[str] = None,
        description: str = "",
    ) -> WebhookDefinition:
        """Register an inbound webhook definition."""
        wh_name = name or (handler.__name__ if handler else path.strip("/").replace("/", "_"))
        defn = WebhookDefinition(
            path=path,
            name=wh_name,
            handler=handler,
            secret=secret,
            secret_env=secret_env,
            header=header,
            algorithm=algorithm,
            event_topic=event_topic,
            description=description or (handler.__doc__ or "").strip(),
        )
        self._webhooks[path] = defn
        return defn

    def get_webhook(self, path: str) -> Optional[WebhookDefinition]:
        """Retrieve a webhook definition by URL path."""
        return self._webhooks.get(path)

    def list_webhooks(self) -> List[Dict[str, Any]]:
        """List all registered webhook definitions as dictionaries."""
        return [defn.to_metadata().model_dump() for defn in self._webhooks.values()]

    def create_route_handler(self, webhook_def: WebhookDefinition) -> Callable:
        """Create a FastAPI route handler for an inbound webhook endpoint."""

        async def webhook_endpoint(request: Request) -> Any:
            secret = webhook_def.get_secret()
            body_bytes = await request.body()

            if secret is not None:
                # Case-insensitive header lookup
                sig_header = None
                for header_key, header_val in request.headers.items():
                    if header_key.lower() == webhook_def.header.lower():
                        sig_header = header_val
                        break

                if not sig_header:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Missing required webhook signature header: {webhook_def.header}",
                    )

                if not verify_hmac_signature(
                    body_bytes, secret, sig_header, webhook_def.algorithm
                ):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid webhook signature",
                    )

            # Parse payload
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
                except (json.JSONDecodeError, UnicodeDecodeError):
                    payload = body_bytes
            else:
                payload = body_bytes

            result = None
            if webhook_def.handler:
                if inspect.iscoroutinefunction(webhook_def.handler):
                    result = await webhook_def.handler(payload)
                else:
                    result = webhook_def.handler(payload)

            response_data = {
                "status": "accepted",
                "webhook": webhook_def.name,
                "result": result,
            }

            self._delivery_history.append(
                {
                    "path": webhook_def.path,
                    "name": webhook_def.name,
                    "status": "accepted",
                }
            )
            if len(self._delivery_history) > 100:
                self._delivery_history.pop(0)

            return response_data

        return webhook_endpoint

    async def simulate_delivery(
        self,
        path: str,
        payload: Union[Dict[str, Any], str, bytes],
        secret: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Simulate delivery to a registered webhook handler without HTTP transport."""
        defn = self.get_webhook(path)
        if not defn:
            raise KeyError(f"Webhook not found for path: {path}")

        raw_bytes = (
            json.dumps(payload).encode("utf-8")
            if isinstance(payload, dict)
            else (payload.encode("utf-8") if isinstance(payload, str) else payload)
        )

        effective_secret = secret or defn.get_secret()
        if effective_secret is not None:
            algo = getattr(hashlib, defn.algorithm.lower().replace("-", ""))
            computed_sig = hmac.new(effective_secret.encode("utf-8"), raw_bytes, algo).hexdigest()
            headers = {defn.header: computed_sig, "content-type": "application/json"}
        else:
            headers = {"content-type": "application/json"}

        if custom_headers:
            headers.update(custom_headers)

        parsed_payload = payload if isinstance(payload, dict) else raw_bytes

        result = None
        if defn.handler:
            if inspect.iscoroutinefunction(defn.handler):
                result = await defn.handler(parsed_payload)
            else:
                result = defn.handler(parsed_payload)

        return {"status": "accepted", "webhook": defn.name, "result": result}
