from __future__ import annotations

from urllib.parse import urlsplit

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_SAFE_FETCH_SITES = {"same-origin", "same-site", "none"}


class PayloadTooLarge(Exception):
    pass


def _header_values(scope: Scope, name: bytes) -> list[str]:
    return [
        value.decode("latin-1").strip()
        for key, value in scope.get("headers", [])
        if key.lower() == name
    ]


def _local_host(value: str) -> str | None:
    """Extract a canonical host without accepting user-info or malformed ports."""
    value = value.strip()
    if not value or any(character in value for character in "/\\@"):
        return None
    if value.startswith("["):
        closing = value.find("]")
        if closing < 0:
            return None
        host = value[1:closing]
        remainder = value[closing + 1 :]
        if remainder and (not remainder.startswith(":") or not remainder[1:].isdigit()):
            return None
        if remainder and not 0 < int(remainder[1:]) <= 65535:
            return None
        return host.casefold().rstrip(".")
    if value.count(":") > 1:
        return None
    host, separator, port = value.partition(":")
    if separator and (not port or not port.isdigit()):
        return None
    if separator and not 0 < int(port) <= 65535:
        return None
    return host.casefold().rstrip(".") or None


def _origin_is_allowed(
    origin: str,
    scope: Scope,
    allowed_hosts: frozenset[str],
    allowed_origins: frozenset[str],
) -> bool:
    if origin in allowed_origins:
        return True
    try:
        parsed = urlsplit(origin)
        hostname = (parsed.hostname or "").casefold().rstrip(".")
        if (
            parsed.scheme not in {"http", "https"}
            or not hostname
            or hostname not in allowed_hosts
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            return False
        origin_port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return False

    host_values = _header_values(scope, b"host")
    if len(host_values) != 1 or _local_host(host_values[0]) != hostname:
        return False
    raw_host = host_values[0]
    try:
        request_port = (
            int(raw_host.rsplit(":", 1)[1])
            if ":" in raw_host and not raw_host.endswith("]")
            else (443 if scope.get("scheme") == "https" else 80)
        )
    except ValueError:
        return False
    return parsed.scheme == scope.get("scheme", "http") and origin_port == request_port


class LocalRequestSecurityMiddleware:
    """Protect the local server before FastAPI parses a request body."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        allowed_hosts: tuple[str, ...],
        allowed_origins: tuple[str, ...],
        max_body_bytes: int,
    ) -> None:
        self.app = app
        self.allowed_hosts = frozenset(host.casefold().rstrip(".") for host in allowed_hosts)
        self.allowed_origins = frozenset(origin.rstrip("/") for origin in allowed_origins)
        self.max_body_bytes = max_body_bytes

    async def _reject(self, scope: Scope, receive: Receive, send: Send, status: int, detail: str) -> None:
        await JSONResponse({"detail": detail}, status_code=status)(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        host_values = _header_values(scope, b"host")
        host = _local_host(host_values[0]) if len(host_values) == 1 else None
        if host not in self.allowed_hosts:
            await self._reject(
                scope, receive, send, 400,
                "Host não permitido. A aplicação aceita apenas acesso local.",
            )
            return

        method = str(scope.get("method", "GET")).upper()
        path = str(scope.get("path", ""))
        if path.startswith("/api/") and method in _MUTATING_METHODS:
            origins = _header_values(scope, b"origin")
            fetch_sites = _header_values(scope, b"sec-fetch-site")
            normalized_origin = origins[0].rstrip("/") if len(origins) == 1 else ""
            if len(origins) > 1 or (
                origins
                and not _origin_is_allowed(
                    origins[0].rstrip("/"),
                    scope,
                    self.allowed_hosts,
                    self.allowed_origins,
                )
            ):
                await self._reject(
                    scope, receive, send, 403,
                    "Origem não permitida para esta operação.",
                )
                return
            fetch_site = fetch_sites[0].casefold() if len(fetch_sites) == 1 else ""
            trusted_dev_cross_site = (
                fetch_site == "cross-site"
                and normalized_origin in self.allowed_origins
            )
            if len(fetch_sites) > 1 or (
                fetch_sites
                and fetch_site not in _SAFE_FETCH_SITES
                and not trusted_dev_cross_site
            ):
                await self._reject(
                    scope, receive, send, 403,
                    "Contexto de navegação não permitido para esta operação.",
                )
                return
            if fetch_sites and fetch_sites[0].casefold() != "none" and not origins:
                await self._reject(
                    scope, receive, send, 403,
                    "A origem da operação não foi informada pelo navegador.",
                )
                return

        content_lengths = _header_values(scope, b"content-length")
        if len(content_lengths) > 1:
            await self._reject(scope, receive, send, 400, "Content-Length inválido.")
            return
        if content_lengths:
            try:
                content_length = int(content_lengths[0])
            except ValueError:
                content_length = -1
            if content_length < 0:
                await self._reject(scope, receive, send, 400, "Content-Length inválido.")
                return
            if content_length > self.max_body_bytes:
                await self._reject(
                    scope, receive, send, 413,
                    "O corpo da requisição excede o limite permitido.",
                )
                return

        consumed = 0

        async def limited_receive() -> Message:
            nonlocal consumed
            message = await receive()
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > self.max_body_bytes:
                    raise PayloadTooLarge
            return message

        response_started = False

        async def tracked_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except PayloadTooLarge:
            if response_started:
                raise
            await self._reject(
                scope, receive, send, 413,
                "O corpo da requisição excede o limite permitido.",
            )
