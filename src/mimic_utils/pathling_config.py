"""Pathling-server config and auth for ``register-derived-concepts``.

A deliberately small mirror of ``pathling_config.py`` in the thesis pipeline
repo: the same committed-yaml shape, the same ``active_environment`` +
``ACTIVE_PATHLING_ENV`` override, the same rule that ``token_url`` is the auth
switch, and the same discipline that *only* secrets are interpolated from the
environment.  Knowing one file means knowing this one.

What it does **not** mirror is the token manager.  There, a LangGraph fan-out
needs a thread-safe, proactively refreshing token.  Here a developer runs one
command by hand a few times a month, so the token is fetched once at startup
and never refreshed: if a long ``--all`` run against prod outlives it, the
request fails with a 401 and you run the command again.  Every write is an
idempotent ``PUT``, so re-running costs nothing, which is what makes the simple
thing the correct thing rather than merely the cheap one.

Secrets cross the process boundary here and nowhere else.  :func:`build_client`
receives resolved values; nothing downstream reads ``os.environ``.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)

# src/mimic_utils/pathling_config.py -> src -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CONFIG_PATH = _REPO_ROOT / "mimic-iv" / "concepts_fhir" / "pathling_config.yaml"

#: A ``PUT``/``GET`` that has not answered in this long is broken, not busy.
WRITE_TIMEOUT = 30.0

#: A smoke query has to *execute* the view.  On prod against full MIMIC-IV even
#: ``_limit=1`` can take minutes, so this is generous on purpose.  Kept as a
#: constant rather than a flag: a developer tool should not ask you to tune it.
QUERY_TIMEOUT = 300.0


class ConfigError(Exception):
    """The config cannot be loaded, or is incomplete for the active environment."""


class Secret:
    """A string that does not appear in logs, reprs or tracebacks.

    The one property of pydantic's ``SecretStr`` this module actually used, at
    a fraction of the dependency.
    """

    __slots__ = ("_value",)

    def __init__(self, value: str = "") -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def __bool__(self) -> bool:
        return bool(self._value)

    def __repr__(self) -> str:
        return "Secret('***')" if self._value else "Secret('')"

    __str__ = __repr__


@dataclass(frozen=True)
class PathlingEnv:
    """One resolved environment: everything needed to talk to one server."""

    name: str
    base_url: str
    token_url: str = ""
    client_id: str = ""
    client_secret: Secret = Secret()
    scopes: tuple[str, ...] = ()
    #: ``True`` verifies against the system trust store, ``False`` accepts a
    #: self-signed certificate, a ``str`` is a CA bundle path.
    verify_tls: Union[bool, str] = True

    @property
    def auth_enabled(self) -> bool:
        """``token_url`` is the canonical auth switch -- see the module docstring."""
        return bool(self.token_url)

    def describe(self) -> str:
        """A one-line target summary safe to print (carries no secret)."""
        auth = "auth on" if self.auth_enabled else "auth OFF"
        return f"{self.base_url} (env {self.name}, {auth})"


def _coerce_verify_tls(value: object) -> Union[bool, str]:
    """Resolve the ``verify_tls`` tri-state.

    An unset ``CSIRO_CA_BUNDLE`` renders as an empty string, which means "no
    bundle configured" and falls back to the system trust store -- *not* to
    disabled verification.  Getting that backwards would silently turn TLS
    checking off, so it is spelled out rather than left to truthiness.
    """
    if isinstance(value, bool):
        return value
    text = str(value or "").strip()
    if not text:
        return True
    lowered = text.lower()
    if lowered in ("true", "yes", "1"):
        return True
    if lowered in ("false", "no", "0"):
        return False
    return text


def _load_dotenv() -> None:
    """Populate ``os.environ`` from ``.env`` without overriding a real env var.

    Without this, a ``.env`` only works under ``direnv`` or a manual ``source``,
    and the failure mode is the nastiest one available: ``client_secret``
    renders empty, auth silently turns *off*, and the run dies at the server
    with a bare 401 that says nothing about the cause.
    """
    from dotenv import load_dotenv

    load_dotenv(_REPO_ROOT / ".env")
    load_dotenv()  # also honour a .env beside the invocation


def load_pathling_env(
    *,
    path: Optional[Union[str, Path]] = None,
    env_name: Optional[str] = None,
) -> PathlingEnv:
    """Load, render and validate the config, returning the active environment.

    Precedence for which environment wins: the ``env_name`` argument (the
    ``--env`` flag), then ``ACTIVE_PATHLING_ENV``, then the file's
    ``active_environment``.  Only the selected environment is validated, so the
    others may stay blank or partial -- you needn't hold every environment's
    secrets to use one of them.
    """
    import yaml
    from jinja2 import Environment, StrictUndefined
    from jinja2 import TemplateError

    _load_dotenv()

    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    if not config_path.is_file():
        raise ConfigError(f"Pathling config not found: {config_path}")

    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Cannot read {config_path}: {exc}") from exc

    # StrictUndefined makes a *required* env var fail loud at render time;
    # `{{ VAR | default('') }}` is what keeps inactive environments blank.
    try:
        rendered = Environment(undefined=StrictUndefined).from_string(raw).render(**os.environ)
    except TemplateError as exc:
        raise ConfigError(
            f"{config_path}: cannot render (a referenced environment variable is "
            f"unset and has no default): {exc}"
        ) from exc

    try:
        data = yaml.safe_load(rendered) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"{config_path}: invalid YAML: {exc}") from exc

    environments = data.get("environments")
    if not isinstance(environments, dict) or not environments:
        raise ConfigError(f"{config_path}: no 'environments' mapping")

    selected = env_name or os.getenv("ACTIVE_PATHLING_ENV") or data.get("active_environment")
    if not selected:
        raise ConfigError(
            f"{config_path}: no environment selected (set 'active_environment', "
            f"ACTIVE_PATHLING_ENV, or pass --env)"
        )
    if selected not in environments:
        raise ConfigError(
            f"environment {selected!r} is not defined in {config_path}; "
            f"known: {sorted(environments)}"
        )

    block = environments[selected] or {}
    if not isinstance(block, dict):
        raise ConfigError(f"{config_path}: environment {selected!r} is not a mapping")

    base_url = str(block.get("base_url") or "").strip()
    if not base_url:
        raise ConfigError(f"environment {selected!r} has no 'base_url'")

    scopes_raw = block.get("scopes") or []
    if isinstance(scopes_raw, str):
        scopes_raw = [scopes_raw]

    env = PathlingEnv(
        name=selected,
        # httpx joins a relative path onto base_url only when it ends in '/'.
        base_url=base_url if base_url.endswith("/") else base_url + "/",
        token_url=str(block.get("token_url") or "").strip(),
        client_id=str(block.get("client_id") or "").strip(),
        client_secret=Secret(str(block.get("client_secret") or "")),
        scopes=tuple(str(s) for s in scopes_raw),
        verify_tls=_coerce_verify_tls(block.get("verify_tls", True)),
    )

    if env.auth_enabled:
        missing = [
            name
            for name, present in (
                ("client_id", bool(env.client_id)),
                ("client_secret", bool(env.client_secret)),
                ("scopes", bool(env.scopes)),
            )
            if not present
        ]
        if missing:
            raise ConfigError(
                f"environment {selected!r} has auth enabled (token_url is set) but is "
                f"missing: {', '.join(missing)}. A blank client_secret usually means the "
                f"env var behind it is not exported and is not in .env."
            )
    else:
        logger.warning(
            "Pathling auth is OFF for environment %r (no token_url); requests will "
            "carry no Authorization header.",
            selected,
        )
    return env


def fetch_token(env: PathlingEnv) -> str:
    """Fetch one OAuth2 client-credentials bearer token.

    Called once per run.  There is no refresh and no retry: failing here aborts
    before anything has been written, and the fix is to run the command again.
    """
    import httpx

    with httpx.Client(verify=env.verify_tls, timeout=WRITE_TIMEOUT) as http:
        try:
            resp = http.post(
                env.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": env.client_id,
                    "client_secret": env.client_secret.get(),
                    "scope": " ".join(env.scopes),
                },
            )
        except httpx.HTTPError as exc:
            raise ConfigError(f"token endpoint unreachable ({env.token_url}): {exc}") from exc

    if resp.status_code != 200:
        raise ConfigError(
            f"token endpoint rejected credentials: HTTP {resp.status_code}: {resp.text[:300]}"
        )
    try:
        payload = resp.json()
    except ValueError as exc:
        raise ConfigError(f"token endpoint returned non-JSON: {exc}") from exc
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise ConfigError("token endpoint payload has no 'access_token'")
    return token


def build_client(env: PathlingEnv):
    """Build the one HTTP client the upload uses, with auth already resolved.

    Returns an ``httpx.Client`` whose ``base_url`` is the FHIR endpoint, so
    callers issue relative paths like ``Library/age``.
    """
    import httpx

    headers = {"Accept": "application/fhir+json"}
    if env.auth_enabled:
        headers["Authorization"] = f"Bearer {fetch_token(env)}"
    # If a prod connection ever hangs where curl succeeds, the known fix is an
    # explicit IPv4 transport: httpx.HTTPTransport(local_address="0.0.0.0").
    return httpx.Client(
        base_url=env.base_url,
        headers=headers,
        verify=env.verify_tls,
        timeout=WRITE_TIMEOUT,
    )


__all__ = [
    "ConfigError",
    "DEFAULT_CONFIG_PATH",
    "PathlingEnv",
    "QUERY_TIMEOUT",
    "Secret",
    "WRITE_TIMEOUT",
    "build_client",
    "fetch_token",
    "load_pathling_env",
]
