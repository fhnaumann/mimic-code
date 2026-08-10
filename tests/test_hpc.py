"""Tests for the HPC stage/submit/poll/fetch driver.

Every cluster interaction goes through one injectable ``runner`` callable, so
these tests substitute it and assert on the exact commands issued. That is the
point of the seam: the sequencing rules that matter here — never sbatch after a
failed smoke test, never call a job successful just because it left the queue,
never overwrite a write-once artifact — are decisions, not I/O, and they should
be testable without a cluster.

The Slurm template is the real one from ``mimic-iv/concepts_fhir/``: rendering
it is exactly where a placeholder typo would otherwise reach the queue.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mimic_utils import hpc
from mimic_utils.hpc import (
    CommandResult,
    HPCError,
    launch,
    poll_once,
    poll_until_done,
    remote_attempt_dir,
    render_submit_script,
    stage_attempt,
    submit,
)

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


class FakeRunner:
    """Records commands and replays scripted responses."""

    def __init__(self, responses=None, default=(0, "", "")):
        self.commands: list[list[str]] = []
        self.responses = responses or {}
        self.default = default

    def __call__(self, cmd, *, timeout=None):
        self.commands.append(list(cmd))
        joined = " ".join(cmd)
        for needle, response in self.responses.items():
            if needle in joined:
                return CommandResult(*response)
        return CommandResult(*self.default)

    def issued(self, needle: str) -> list[list[str]]:
        return [c for c in self.commands if needle in " ".join(c)]


@pytest.fixture
def attempt(tmp_path):
    """A minimal attempt directory inside a fake repo root."""
    path = tmp_path / "mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0001"
    path.mkdir(parents=True)
    (path / "concept.sql").write_text("SELECT 1", encoding="utf-8")
    (path / "ViewDefinition.patient.json").write_text(
        json.dumps({"resourceType": "ViewDefinition", "name": "patient"}),
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# path mapping + template rendering
# ---------------------------------------------------------------------------


class TestRemotePathMapping:
    def test_mirrors_the_relative_path(self, tmp_path, attempt):
        remote = remote_attempt_dir(attempt, root=tmp_path)
        assert remote == (
            f"{hpc.REMOTE_REPO}/mimic-iv/concepts_fhir/concepts/"
            "demographics/age/attempt_0001"
        )

    def test_rejects_a_path_outside_the_repo(self, tmp_path):
        outside = tmp_path.parent / "elsewhere"
        with pytest.raises(HPCError, match="outside the repo"):
            remote_attempt_dir(outside, root=tmp_path)


class TestRenderSubmitScript:
    def test_substitutes_every_placeholder(self):
        script = render_submit_script("age", "/scratch3/nau025/mimic-code/x/attempt_0001")
        assert "{{" not in script
        assert "--job-name=port-age" in script
        assert hpc.ACCOUNT in script
        assert "/scratch3/nau025/mimic-code/x/attempt_0001" in script

    def test_points_the_runner_at_the_full_oracle_and_warehouse(self):
        script = render_submit_script("age", "/remote/attempt_0001")
        assert f"MIMIC_FULL_ORACLE={hpc.REMOTE_ORACLE}" in script
        assert f"MIMIC_FHIR_WAREHOUSE={hpc.REMOTE_WAREHOUSE}" in script

    def test_never_syncs_on_a_node_without_internet(self):
        assert "uv run --no-sync" in render_submit_script("age", "/remote/a")

    def test_raises_on_an_unsubstituted_placeholder(self, tmp_path):
        template = tmp_path / "t.slurm"
        template.write_text("#!/bin/bash\n{{CONCEPT}} {{MYSTERY}}\n", encoding="utf-8")
        with pytest.raises(HPCError, match="unsubstituted placeholders"):
            render_submit_script("age", "/remote/a", template_path=template)


# ---------------------------------------------------------------------------
# staging
# ---------------------------------------------------------------------------


class TestStageAttempt:
    def test_writes_the_submit_script_into_the_attempt(self, tmp_path, attempt):
        stage_attempt("age", attempt, runner=FakeRunner(), root=tmp_path)
        rendered = (attempt / "submit.slurm").read_text(encoding="utf-8")
        assert "--job-name=port-age" in rendered

    def test_transfers_source_manifest_and_attempt(self, tmp_path, attempt):
        (tmp_path / "src/mimic_utils").mkdir(parents=True)
        manifest = tmp_path / hpc.MANIFEST_RELPATH
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text("{}", encoding="utf-8")

        runner = FakeRunner()
        stage_attempt("age", attempt, runner=runner, root=tmp_path)

        rsyncs = " | ".join(" ".join(c) for c in runner.issued("rsync"))
        assert "src/mimic_utils" in rsyncs
        assert "oracle_manifest.full.json" in rsyncs
        assert "attempt_0001" in rsyncs

    def test_never_uploads_a_local_result_artifact(self, tmp_path, attempt):
        """A remote comparison.full.json must only ever come from a remote run."""
        runner = FakeRunner()
        stage_attempt("age", attempt, runner=runner, root=tmp_path)
        # The attempt-directory transfer specifically: since staging became
        # per-attempt, the code and manifest rsyncs also mention attempt_0001,
        # and only this one has the attempt dir itself as source and target.
        attempt_rsync = [
            c for c in runner.issued("rsync")
            if any(a.endswith("attempt_0001/") for a in c)
        ]
        assert attempt_rsync
        flags = " ".join(attempt_rsync[0])
        for excluded in ("comparison.full.json", "run_meta.full.json", "candidate.full.parquet"):
            assert f"--exclude {excluded}" in flags

    def test_raises_when_the_remote_mkdir_fails(self, tmp_path, attempt):
        runner = FakeRunner(responses={"mkdir": (1, "", "permission denied")})
        with pytest.raises(HPCError, match="remote mkdir failed"):
            stage_attempt("age", attempt, runner=runner, root=tmp_path)

    def test_raises_when_an_rsync_fails(self, tmp_path, attempt):
        runner = FakeRunner(responses={"rsync": (23, "", "partial transfer")})
        with pytest.raises(HPCError, match="rsync"):
            stage_attempt("age", attempt, runner=runner, root=tmp_path)


# ---------------------------------------------------------------------------
# submission
# ---------------------------------------------------------------------------


class TestSubmit:
    def test_parses_the_job_id(self):
        runner = FakeRunner(responses={"sbatch": (0, "Submitted batch job 8675309\n", "")})
        assert submit("/remote/a", runner=runner) == "8675309"

    def test_raises_when_the_id_cannot_be_parsed(self):
        runner = FakeRunner(responses={"sbatch": (0, "queued, probably\n", "")})
        with pytest.raises(HPCError, match="could not parse a job id"):
            submit("/remote/a", runner=runner)

    def test_raises_when_sbatch_fails(self):
        runner = FakeRunner(responses={"sbatch": (1, "", "Invalid account")})
        with pytest.raises(HPCError, match="sbatch failed"):
            submit("/remote/a", runner=runner)


class TestLaunch:
    def _runner(self, **overrides):
        responses = {"sbatch": (0, "Submitted batch job 4242\n", "")}
        responses.update(overrides)
        return FakeRunner(responses=responses)

    def test_submits_and_records_the_job(self, tmp_path, attempt):
        runner = self._runner()
        result = launch("age", attempt_dir=attempt, runner=runner, root=tmp_path)

        assert result.submitted
        assert result.job_id == "4242"
        record = json.loads((attempt / "hpc_job.json").read_text(encoding="utf-8"))
        assert record["job_id"] == "4242"
        assert record["concept"] == "age"
        assert record["remote_attempt"].endswith("attempt_0001")

    def test_a_failed_smoke_test_stops_before_sbatch(self, tmp_path, attempt):
        """A broken job still burns a queue slot, so it must never be submitted."""
        runner = self._runner(**{"bash -lc": (1, "", "ModuleNotFoundError: pathling")})
        result = launch("age", attempt_dir=attempt, runner=runner, root=tmp_path)

        assert not result.submitted
        assert runner.issued("sbatch") == []
        assert not (attempt / "hpc_job.json").exists()
        assert "smoke test failed" in result.errors[0]

    def test_smoke_test_does_not_start_a_jvm_on_the_login_node(self, tmp_path, attempt):
        runner = self._runner()
        launch("age", attempt_dir=attempt, runner=runner, root=tmp_path)
        smoke = " ".join(runner.issued("bash -lc")[0])
        assert "PathlingContext" not in smoke
        assert "import duckdb, pathling, pyspark" in smoke

    def test_refuses_a_second_run_in_the_same_attempt(self, tmp_path, attempt):
        (attempt / "hpc_job.json").write_text("{}", encoding="utf-8")
        with pytest.raises(HPCError, match="write-once"):
            launch("age", attempt_dir=attempt, runner=self._runner(), root=tmp_path)


# ---------------------------------------------------------------------------
# polling + fetching
# ---------------------------------------------------------------------------


class TestPollOnce:
    def test_reports_a_queued_job(self):
        runner = FakeRunner(responses={"squeue": (0, "4242\n9999\n", "")})
        status = poll_once("4242", "/remote/a", runner=runner)
        assert status.in_queue
        assert not status.finished

    def test_a_job_out_of_the_queue_is_finished(self):
        runner = FakeRunner(responses={"squeue": (0, "9999\n", "")})
        assert poll_once("4242", "/remote/a", runner=runner).finished

    def test_a_fatal_marker_ends_the_wait_early(self):
        runner = FakeRunner(
            responses={
                "squeue": (0, "4242\n", ""),
                "grep": (0, "java.lang.OutOfMemoryError: Java heap space\n", ""),
            }
        )
        status = poll_once("4242", "/remote/a", runner=runner)
        # Still in the queue, but there is nothing left to wait for.
        assert status.in_queue and status.finished
        assert status.fatal_markers == ["java.lang.OutOfMemoryError"]


class TestPollUntilDone:
    def _record(self, attempt, job_id="4242"):
        (attempt / "hpc_job.json").write_text(
            json.dumps({"job_id": job_id, "remote_attempt": "/remote/a"}),
            encoding="utf-8",
        )

    def test_returns_the_verdict_once_the_comparison_lands(self, attempt, monkeypatch):
        self._record(attempt)
        comparison = {"verdict": "match", "diagnostics": []}

        def fake_fetch(local, remote, *, runner):
            (local / "comparison.full.json").write_text(json.dumps(comparison))
            return [str(local / "comparison.full.json")]

        monkeypatch.setattr(hpc, "fetch_results", fake_fetch)
        runner = FakeRunner(responses={"squeue": (0, "", "")})
        result = poll_until_done("age", attempt_dir=attempt, runner=runner, sleeper=lambda _: None)

        assert result.outcome == "complete"
        assert result.verdict == "match"

    def test_leaving_the_queue_without_a_verdict_is_a_crash(self, attempt):
        """Queue exit alone is not success — an OOM also leaves the queue."""
        self._record(attempt)
        runner = FakeRunner(responses={"squeue": (0, "", "")})
        result = poll_until_done("age", attempt_dir=attempt, runner=runner, sleeper=lambda _: None)

        assert result.outcome == "crash"
        assert result.verdict is None
        assert any("without producing" in d for d in result.diagnostics)

    def test_keeps_waiting_while_the_job_is_queued(self, attempt):
        self._record(attempt)
        runner = FakeRunner(responses={"squeue": (0, "4242\n", "")})
        slept: list[float] = []
        result = poll_until_done(
            "age", attempt_dir=attempt, runner=runner,
            interval=300, max_polls=3, sleeper=slept.append,
        )
        assert result.outcome == "timeout"
        assert result.polls == 3
        assert slept == [300, 300, 300]

    def test_requires_a_launch_record(self, attempt):
        with pytest.raises(HPCError, match="launch the job first"):
            poll_until_done("age", attempt_dir=attempt, runner=FakeRunner())


class TestFetchResults:
    def test_never_overwrites_a_local_artifact(self, attempt):
        runner = FakeRunner()
        hpc.fetch_results(attempt, "/remote/a", runner=runner)
        for cmd in runner.issued("rsync"):
            assert "--ignore-existing" in cmd

    def test_leaves_the_large_parquet_on_scratch(self, attempt):
        runner = FakeRunner()
        hpc.fetch_results(attempt, "/remote/a", runner=runner)
        fetched = " ".join(" ".join(c) for c in runner.issued("rsync"))
        assert "candidate.full.parquet" not in fetched
        assert "comparison.full.json" in fetched
        assert "run_meta.full.json" in fetched
