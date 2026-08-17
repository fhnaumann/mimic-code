"""Tests for the Pathling config loader.

Only the loader is tested.  It is the piece with real branching, it needs no
network, and its worst failure is silent: a `client_secret` that renders empty
turns auth *off*, and the run then dies at the server with a bare 401 that says
nothing about the cause.  The upload loop itself is a `for` loop over `PUT`, and
a live server on localhost exercises it more honestly than a mock would.
"""

import pytest

pytest.importorskip("yaml")
pytest.importorskip("jinja2")
pytest.importorskip("dotenv")

from mimic_utils.pathling_config import (  # noqa: E402
    ConfigError,
    Secret,
    _coerce_verify_tls,
    load_pathling_env,
)


AUTH_OFF = """
active_environment: local
environments:
  local:
    base_url: http://localhost:8080/fhir/
  prod:
    base_url: https://example.invalid/fhir/
    token_url: https://token.invalid/token
    client_id: someone
    scopes:
      - openid system/*.*
    client_secret: "{{ SECRET_VAR | default('') }}"
"""


def _write(tmp_path, text):
    path = tmp_path / "pathling_config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """The loader reads the real environment, so isolate every test from it."""
    for var in ("ACTIVE_PATHLING_ENV", "SECRET_VAR", "CSIRO_CA_BUNDLE"):
        monkeypatch.delenv(var, raising=False)


class TestEnvironmentSelection:
    def test_file_default_is_used(self, tmp_path):
        env = load_pathling_env(path=_write(tmp_path, AUTH_OFF))
        assert env.name == "local"

    def test_env_var_overrides_the_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SECRET_VAR", "s3cret")
        monkeypatch.setenv("ACTIVE_PATHLING_ENV", "prod")
        env = load_pathling_env(path=_write(tmp_path, AUTH_OFF))
        assert env.name == "prod"

    def test_argument_beats_the_env_var(self, tmp_path, monkeypatch):
        """`--env` is the last word, so a stale exported var cannot misdirect a run."""
        monkeypatch.setenv("ACTIVE_PATHLING_ENV", "prod")
        env = load_pathling_env(path=_write(tmp_path, AUTH_OFF), env_name="local")
        assert env.name == "local"

    def test_unknown_environment_names_the_alternatives(self, tmp_path):
        with pytest.raises(ConfigError, match="known: \\['local', 'prod'\\]"):
            load_pathling_env(path=_write(tmp_path, AUTH_OFF), env_name="staging")

    def test_missing_file_is_reported_as_config(self, tmp_path):
        with pytest.raises(ConfigError, match="not found"):
            load_pathling_env(path=tmp_path / "absent.yaml")


class TestAuthSwitch:
    def test_no_token_url_means_auth_off(self, tmp_path):
        env = load_pathling_env(path=_write(tmp_path, AUTH_OFF))
        assert env.auth_enabled is False
        assert "auth OFF" in env.describe()

    def test_token_url_with_a_secret_means_auth_on(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SECRET_VAR", "s3cret")
        env = load_pathling_env(path=_write(tmp_path, AUTH_OFF), env_name="prod")
        assert env.auth_enabled is True
        assert env.client_secret.get() == "s3cret"

    def test_auth_on_with_an_unset_secret_fails_loudly(self, tmp_path):
        """The failure this whole module exists to prevent.

        Without it the secret renders blank, no Authorization header is sent, and
        the server answers 401 without saying why.
        """
        with pytest.raises(ConfigError, match="missing: client_secret"):
            load_pathling_env(path=_write(tmp_path, AUTH_OFF), env_name="prod")

    def test_an_inactive_environment_may_stay_incomplete(self, tmp_path):
        """`prod` is missing its secret, but selecting `local` must still work."""
        env = load_pathling_env(path=_write(tmp_path, AUTH_OFF), env_name="local")
        assert env.name == "local"

    def test_auth_on_missing_client_id_and_scopes(self, tmp_path):
        text = """
active_environment: prod
environments:
  prod:
    base_url: https://example.invalid/fhir/
    token_url: https://token.invalid/token
    client_secret: "shhh"
"""
        with pytest.raises(ConfigError) as excinfo:
            load_pathling_env(path=_write(tmp_path, text))
        assert "client_id" in str(excinfo.value)
        assert "scopes" in str(excinfo.value)


class TestStrictRendering:
    def test_an_undefined_variable_without_a_default_fails_at_render(self, tmp_path):
        """StrictUndefined: a typo'd variable is an error, not a silent blank."""
        text = """
active_environment: local
environments:
  local:
    base_url: http://localhost:8080/fhir/
    token_url: "{{ NO_SUCH_VAR }}"
"""
        with pytest.raises(ConfigError, match="cannot render"):
            load_pathling_env(path=_write(tmp_path, text))

    def test_base_url_gains_a_trailing_slash(self, tmp_path):
        """httpx only joins a relative path onto a base_url that ends in '/'."""
        text = """
active_environment: local
environments:
  local:
    base_url: http://localhost:8080/fhir
"""
        env = load_pathling_env(path=_write(tmp_path, text))
        assert env.base_url == "http://localhost:8080/fhir/"

    def test_missing_base_url_is_refused(self, tmp_path):
        text = """
active_environment: local
environments:
  local:
    token_url: https://token.invalid/token
"""
        with pytest.raises(ConfigError, match="no 'base_url'"):
            load_pathling_env(path=_write(tmp_path, text))


class TestVerifyTls:
    def test_blank_falls_back_to_the_system_trust_store(self):
        """An unset CSIRO_CA_BUNDLE must not read as 'disable verification'."""
        assert _coerce_verify_tls("") is True

    def test_a_path_is_kept_as_a_bundle(self):
        assert _coerce_verify_tls("/etc/ssl/csiro.pem") == "/etc/ssl/csiro.pem"

    @pytest.mark.parametrize("value,expected", [
        ("true", True), ("false", False), ("yes", True), ("no", False),
        (True, True), (False, False),
    ])
    def test_booleans_round_trip(self, value, expected):
        assert _coerce_verify_tls(value) is expected

    def test_an_unset_bundle_var_renders_to_verification_on(self, tmp_path):
        text = """
active_environment: local
environments:
  local:
    base_url: http://localhost:8080/fhir/
    verify_tls: "{{ CSIRO_CA_BUNDLE | default('') }}"
"""
        env = load_pathling_env(path=_write(tmp_path, text))
        assert env.verify_tls is True


class TestSecret:
    def test_the_value_is_retrievable(self):
        assert Secret("hunter2").get() == "hunter2"

    def test_it_does_not_leak_in_repr_or_str(self):
        secret = Secret("hunter2")
        assert "hunter2" not in repr(secret)
        assert "hunter2" not in str(secret)
        assert "hunter2" not in f"{secret}"

    def test_emptiness_is_falsey(self):
        assert not Secret("")
        assert Secret("x")
