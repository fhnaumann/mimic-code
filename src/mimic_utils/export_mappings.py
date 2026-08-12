"""Export finalized FHIR concept SQL in the canonical concept layout."""

from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from pathlib import Path, PurePosixPath
from typing import Optional, Union

from mimic_utils.conversion_state import ConversionController, StateError


DEFAULT_EXPORT_DIR = "mimic-iv/concepts_fhir/artifacts"


def export_mappings(
    *, artifact_root: Optional[Union[str, Path]] = None
) -> tuple[Path, int]:
    """Rebuild the canonical-layout SQL export from finalized attempts."""
    ctrl = ConversionController(artifact_root=artifact_root)
    output_dir = ctrl.artifact_root / DEFAULT_EXPORT_DIR
    exports: list[tuple[Path, Path]] = []
    destinations: set[Path] = set()

    for row in ctrl.status_report().concepts:
        if row["status"] not in ctrl.SATISFYING_STATUSES:
            continue

        concept = row["concept"]
        attempt_dir = ctrl.attempt_dir(concept)
        source = attempt_dir / "concept.sql" if attempt_dir else None
        if source is None or not source.is_file():
            expected = source or f"attempt {row['attempt']}"
            raise StateError(
                f"Finalized concept '{concept}' has no concept.sql at {expected}"
            )

        dag_path = PurePosixPath(ctrl.dag_raw["nodes"][concept]["path"])
        if dag_path.is_absolute() or ".." in dag_path.parts:
            raise StateError(
                f"Concept '{concept}' has unsafe DAG path {str(dag_path)!r}"
            )
        destination = Path(*dag_path.parts)
        if destination in destinations:
            raise StateError(f"Duplicate mapping export path: {destination}")
        destinations.add(destination)
        exports.append((source, destination))

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if output_dir.exists() and not output_dir.is_dir():
        raise StateError(f"Mapping export path is not a directory: {output_dir}")

    staging_dir = Path(
        tempfile.mkdtemp(prefix=".artifacts-staging-", dir=output_dir.parent)
    )
    backup_dir: Optional[Path] = None
    try:
        for source, destination in exports:
            staged = staging_dir / destination
            staged.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, staged)

        if output_dir.exists():
            backup_dir = output_dir.with_name(
                f".{output_dir.name}.backup-{uuid.uuid4().hex}"
            )
            os.replace(output_dir, backup_dir)

        try:
            os.replace(staging_dir, output_dir)
        except Exception:
            if backup_dir is not None:
                os.replace(backup_dir, output_dir)
                backup_dir = None
            raise

        if backup_dir is not None:
            shutil.rmtree(backup_dir)
            backup_dir = None
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)

    return output_dir, len(exports)
