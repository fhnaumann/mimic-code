# MIMIC Code Repository [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.6818823.svg)](https://doi.org/10.5281/zenodo.6818823)

## Local relational oracle setup (fork-specific)

How to build the local MIMIC-IV demo oracle with derived concepts, on this
machine (macOS, DuckDB CLI, demo data at
`/Users/nau025/warehouses/mimic-iv-psql-demo`).

**DuckDB, not Postgres.** The Postgres build was torn down deliberately; do not
reintroduce it. DuckDB is serverless and stores everything in a single file, so
there is no service to start, no roles, no `constraint`/`index` step, and the
oracle can be copied, hashed, and version-pinned as one artifact -- which suits
the per-attempt hashing this port requires.

The concepts driver takes no data path. It reads tables already in the database
file and writes derived tables into the `mimiciv_derived` schema. Loading the
CSVs is the real work; concepts is the last step.

```sh
cd /Users/nau025/Documents/mimic-code/mimic-iv/buildmimic/duckdb

# 1. create the db file and load the gzipped demo CSVs
./import_duckdb.sh /Users/nau025/warehouses/mimic-iv-duckdb-demo \
  /Users/nau025/warehouses/mimic4-demo.db

# 2. derived concepts -- the cd is REQUIRED, see below
cd /Users/nau025/Documents/mimic-code/mimic-iv/concepts_duckdb
duckdb /Users/nau025/warehouses/mimic4-demo.db -c ".read duckdb.sql"
```

That is the whole build. Two steps instead of six.

### How the build actually works

`import_duckdb.sh` does not have its own schema definition. It **reuses the
Postgres `create.sql`**, piped through three `sed` regexes before being fed to
`duckdb`:

1. `TIMESTAMP(n)` -> `TIMESTAMP` (DuckDB rejects the precision argument)
2. drops `NOT NULL` on `mimiciv_hosp.microbiologyevents.spec_type_desc`
3. drops `NOT NULL` on `mimiciv_hosp.prescriptions.drug`

Regexes 2 and 3 exist because DuckDB's CSV reader treats zero-length strings as
NULL, so rows Postgres accepts would violate `NOT NULL` here. **Consequence worth
knowing for equivalence work:** the DuckDB oracle's schema is marginally laxer
than the Postgres one, and those two columns can hold NULLs that the Postgres
build forbids.

Loading then walks the data directory with `find -name '*.csv???'`, derives the
table name from the path (`./icu/d_items.csv.gz` -> `mimiciv_icu.d_items`), and
`COPY`s each file in. Only `hosp` and `icu` directories are processed; anything
else (e.g. a sibling `mimic-iv-ed` download, or the top-level
`demo_subject_id.csv`) is skipped by design.

### Notes, in rough order of how easy they are to get wrong

- **Step 2 must be run from inside `concepts_duckdb`.** `duckdb.sql` is a list of
  relative `.read demographics/age.sql` directives, so paths resolve against the
  process working directory. Same trap as the old Postgres build.
- **`create.sql`'s schema block is what creates `mimiciv_derived`.** The concepts
  driver assumes the schema already exists; it does not create it. So step 1 must
  precede step 2 -- you cannot run concepts against a hand-made db file.
- **The import script's glob only matches compressed files.** `-name '*.csv???'`
  requires exactly three characters after `.csv`, which matches `.csv.gz` but
  **not** plain `.csv`, despite the upstream README saying uncompressed files are
  supported. Irrelevant here (the demo ships `.csv.gz`) but it fails silently by
  loading nothing rather than erroring, so keep the files compressed.
- **Re-running the import prompts rather than clobbering.** If the output file
  exists and is non-empty the script asks `(y/d/n)`: `y` continues into the
  existing file (which double-loads rows -- avoid), `d` deletes and rebuilds, `n`
  aborts. For a clean rebuild choose `d`. In an unattended context, delete the
  file first so nothing blocks on stdin.
- **No constraints or indexes step.** DuckDB is columnar and needs no index
  equivalent of `postgres-concept-index.sql`. Note this also means the oracle has
  **no primary or foreign keys** -- those lived in the Postgres-only
  `constraint.sql`, which the import does not use.
- **`mimiciv_ed` is referenced by concepts but never created**, since the demo has
  no ED data.

### Protecting the oracle from the agent loop

DuckDB has no roles, so the `mimic_ro` approach from the Postgres build has no
equivalent. Access control is filesystem-level and mode-level instead. **Agents
must open the oracle read-only:**

```sh
duckdb -readonly /Users/nau025/warehouses/mimic4-demo.db
```

```sql
-- or, from another database
ATTACH '/Users/nau025/warehouses/mimic4-demo.db' AS oracle (READ_ONLY);
```

```python
import duckdb
con = duckdb.connect("/Users/nau025/warehouses/mimic4-demo.db", read_only=True)
```

Read-only mode is a per-connection flag, so an agent that constructs its own
connection can simply omit it. Back it with filesystem permissions, which an
agent running as this user cannot trivially undo from SQL:

```sh
chmod 444 /Users/nau025/warehouses/mimic4-demo.db
```

Keep a pristine copy plus its hash as the reference artifact, so a corrupted
oracle is detectable rather than silently producing passing comparisons:

```sh
cp mimic4-demo.db mimic4-demo.reference.db
shasum -a 256 mimic4-demo.reference.db > mimic4-demo.reference.db.sha256
```

Because the whole oracle is one file, restoring is a copy and verifying is one
`shasum` -- materially better for reproducible attempts than the Postgres setup.
Note that read-only mode is also required for *concurrent* readers: DuckDB allows
many read-only connections to a file but only one read-write connection, so a
parallel loop will otherwise fail to acquire the lock.

### Facts about the demo data that survive the switch

These were established on the Postgres build and are properties of the dataset,
not the engine, so they still hold:

- 22 `hosp` tables and 9 `icu` tables, matching the 22 and 9 `.csv.gz` files.
- All 28 row counts matched `buildmimic/postgres/validate_demo.sql` exactly
  (`admissions` 275, `patients` 100, `chartevents` 668862, `icustays` 140, ...).
  That script is plain SQL over `information_schema` and is the reference for
  expected counts even though it lives in the Postgres folder.
- 65 derived concept tables built, of which exactly one is empty: `neuroblock`.
  No neuromuscular blocker administrations exist among the 100 demo patients.
  This is a correct result, not a build failure, but it means `neuroblock` cannot
  act as a local relational oracle -- a FHIR implementation returning 0 rows would
  match it trivially. Force that concept to human review or HPC-only validation.

```sh
# quick sanity check
duckdb -readonly /Users/nau025/warehouses/mimic4-demo.db -c \
  "SELECT table_schema, count(*) FROM information_schema.tables
   WHERE table_schema LIKE 'mimiciv%' GROUP BY 1 ORDER BY 1;"
```

### Pinned concept baseline

Port baseline commit: **`3a914fc`**. Pin to this rather than rolling the fork
back to a 2.2-era commit. The concepts drifted ~6.6k lines across 71 files
between `v2.4.0` (2023-02, the 2.2 era) and here, and much of the recent work is
specifically determinism repair -- `5a45342` bg determinism, `15ae2cf` o2 flow
non-determinism, `d3f593d` deterministic `string_agg`, `2afa73c` rhythm
concatenation instead of arbitrary `MAX()`, `ad1d23b` storetime tie-breaker
removal, `c07b7a9` suspicion-of-infection tie handling, `317068a` rounding
mismatches. Equivalence testing against a non-deterministic oracle is not
meaningful, so these fixes are load-bearing for this port. HEAD also adds
`3327e48` (missing concepts in the build) and `a399a08` (concept indexes -- a
Postgres-only benefit, irrelevant under DuckDB).

Do not roll the fork back for version alignment. The build scripts are already
2.2-era: `create.sql`'s last substantive commit is `db74e5d` (2023-01-06)
*"update create and load psql scripts for v2.2"*, followed only by a cosmetic
`admissions.language` column-width bump (`b52db56`), and `validate_demo.sql` was
last calibrated 2023-01-07 against the 2.2 demo. This holds for DuckDB too, since
the import reuses that same `create.sql`.

Concept SQL is version-agnostic across 2.2/3.1 for the columns it reads, which is
demonstrated rather than assumed: all 65 concepts executed against 2.2 demo data
with zero errors, and a renamed or missing column would fail at execution
regardless of row counts. MIMIC-on-FHIR 2.1 is generated from raw 2.2 tables, not
from derived concepts, so concept vintage is not part of that lineage.

**`concepts_duckdb/` is generated, not authored.** Like the Postgres variant it is
transpiled from the BigQuery sources via sqlglot; its own README says to make
corrections in `mimic-iv/concepts/` instead. When deciding what a concept
*means*, `mimic-iv/concepts/` is canonical; if the two disagree, treat it as a
transpilation bug rather than editing the generated file.

## MIMIC-on-FHIR concept port (fork-specific)

This fork is being used to port the MIMIC-IV derived concepts to MIMIC-on-FHIR
2.1, which was generated from MIMIC-IV 2.2. The intended unattended invocation
for one derived table is:

```text
/goal Port the ready MIMIC-IV concept <concept> from MIMIC-IV 2.2 to mimic-on-FHIR 2.1 in generated DAG order. Require demo equivalence before full-data validation. Process exactly this one concept and stop after it passes, a representability decision requires human review, or a configured budget is reached. --max-turns 500 --max-minutes 1440
```

The generated dependency DAG must be available in both machine-readable and
human-readable forms. A goal may only select a concept whose dependencies have
already passed, and it must not automatically continue to the next concept.
Execution is strictly sequential by default, including local probes and HPC
validation. Parallel execution is allowed only when the goal explicitly requests
it.

Validation uses the public 100-patient MIMIC-IV 2.2 demo as the local relational
oracle and the MIMIC-on-FHIR demo as the local candidate dataset after an identifier
check confirms that both contain the same source cohort.
Full MIMIC-IV 2.2 and MIMIC-on-FHIR 2.1 remain on HPC for final validation of each
concept. Dataset versions, source SQL, dependencies, terminology resources, and
execution artifacts must be hashed and recorded for every attempt.

FHIR ConceptMaps hosted on `https://velonto.dw.csiro.au/fhir/`, with pinned local
FHIR copies when needed for reproducibility or offline HPC execution, are the
authoritative terminology mappings. The CSV mappings under
`mimic-iv/concepts/concept_map/` are not used by this port. Translation accepts
every ConceptMap relationship except an explicit `unmatched` result. Production
views use an approved ConceptMap canonical and verify its scope and version before
execution; bare `$translate` is suitable for discovery but is not a reproducible
mapping contract by itself.

Agent model assignments follow task complexity:

- Complex reasoning, implementation, mismatch diagnosis, orchestration, and
  independent equivalence or representability judgment use Sol with `xhigh`.
- Bounded analysis, FHIR probing, terminology resolution, and engineering repair
  use Luna with `xhigh` or `max`.
- Mechanical DAG checks, job launch, polling, artifact transfer, and formatting
  use Luna with `low`.

### Local setup

Install the project and the comparison dependencies, then validate the static DAG
and the read-only MIMIC-IV 2.2 demo database:

```bash
uv sync --extra test --extra equivalence
uv run mimic_utils concept_dag --check
uv run mimic_utils preflight --no-color
uv run mimic_utils status --no-color
```

The DuckDB migration is complete and live-verified. Every loop code path
resolves its oracle from `MIMIC_DUCKDB_PATH` (default
`/Users/nau025/warehouses/mimic4-demo.db`) and opens it with
`duckdb.connect(path, read_only=True)`. No `psycopg2` import and no
`MIMIC_DB_URI` remains anywhere in the port loop.

Verified on 2026-08-05:

```text
uv run pytest                        725 passed
mimic_utils concept_dag --check      pass (65 concepts, 91 edges, 4 levels)
mimic_utils preflight --no-color     PASS (4 gates; 65/65 concept tables)
```

`preflight` proves demo identity by SHA256 plus the exact row counts from
`buildmimic/postgres/validate_demo.sql` -- that script is plain SQL over
`information_schema`, so it is engine-independent and remains the reference
under DuckDB. It reports `neuroblock` as an expected-empty demo concept rather
than a build failure.

Two PostgreSQL things remain **by design**, both upstream and unrelated to the
port loop: the `mimic-iv/buildmimic/postgres/` and `mimic-iv/concepts_postgres/`
build trees, and `src/mimic_utils/compare_concepts.py`, which takes both `--pg`
and `--duckdb` because it is upstream's cross-engine transpilation check. That
tool is not part of the concept-port execution path; the port loop uses
`compare-port-results`.

The generated human-readable selection order is at
[`mimic-iv/concept_dag/concept_dag.md`](mimic-iv/concept_dag/concept_dag.md).
Run `uv run mimic_utils status` to combine that DAG with current conversion
state and see which concepts are ready.

Source oracle and comparison artifacts are write-once:

```bash
uv run mimic_utils export-oracle age \
  --output mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0001/original.demo.json
uv run mimic_utils compare-port-results ORIGINAL.json CANDIDATE.json \
  --output comparison.demo.json
```

OpenCode configuration, agents, and skills are project-local under
`opencode.json` and `.opencode/`. Restart OpenCode after changing these files;
configuration is loaded only at startup.

The MIMIC Code Repository is intended to be a central hub for sharing, refining, and reusing code used for analysis of the [MIMIC critical care database](https://mimic.mit.edu). To find out more about MIMIC, please see: https://mimic.mit.edu. Source code for the website is in the [mimic-website GitHub repository](https://github.com/MIT-LCP/mimic-website/).

You can read more about the code repository in the following open access paper: [The MIMIC Code Repository: enabling reproducibility in critical care research](https://doi.org/10.1093/jamia/ocx084).

## Cloud access to datasets

The various MIMIC databases are available on Google Cloud Platform (GCP) and Amazon Web Services (AWS). To access the data on the cloud, simply add the relevant cloud identifier to your PhysioNet profile. Then request access to the dataset for the particular cloud platform via the PhysioNet project page. Further instructions are available on [the MIMIC website](https://mimic.mit.edu/docs/gettingstarted/cloud/).

## Navigating this repository

This repository contains code for the following databases on PhysioNet:

- [MIMIC-III](https://physionet.org/content/mimiciii/) - critical care data for patients admitted to ICUs at the BIDMC between 2001 - 2012
- [MIMIC-IV](https://physionet.org/content/mimiciv/) - hospital and critical care data for patients admitted to the ED or ICU between 2008 - 2019
- [MIMIC-IV-Note](https://physionet.org/content/mimic-iv-note) - deidentified free-text clinical notes
- [MIMIC-IV-ED](https://physionet.org/content/mimic-iv-ed/) - emergency department data for individuals attending the ED between 2011 - 2019
- MIMIC-IV Waveforms (TBD) - this dataset has yet to be published.
- [MIMIC-CXR](https://physionet.org/content/mimic-cxr/) - chest x-ray imaging and deidentified free-text radiology reports for patients admitted to the ED from 2012 - 2016

The repository contains one top-level folder containing community developed code for each datasets:

- [mimic-iii](/mimic-iii) - build scripts for MIMIC-III, derived concepts which are available on the `physionet-data.mimiciii_derived` dataset on BigQuery, and tutorials.
- [mimic-iv](/mimic-iv) - build scripts for MIMIC-IV, derived concepts which are available on release-specific datasets such as `physionet-data.mimiciv_3_1_derived` on BigQuery, and tutorials.
- [mimic-iv-note](/mimic-iv-note) - build scripts
- [mimic-iv-cxr](/mimic-iv-cxr) - code for loading and analyzing both dicom (mimic-iv-cxr/dcm) and text (mimic-iv-cxr/txt) data. In order to clearly indicate that MIMIC-CXR can be linked with MIMIC-IV, we have named this folder mimic-iv-cxr, and any references to MIMIC-CXR / MIMIC-IV-CXR are interchangeable.
- [mimic-iv-ed](/mimic-iv-ed) - build scripts for MIMIC-IV-ED.
- mimic-iv-waveforms - TBD

Each subfolder has a README with further detail regarding its content.

### Launch MIMIC-III in AWS

MIMIC-III is available on AWS (and MIMIC-IV will be available in the future). Use the below Launch Stack button to deploy access to the MIMIC-III dataset into your AWS account.  This will give you real-time access to the MIMIC-III data in your AWS account without having to download a copy of the MIMIC-III dataset.  It will also deploy a Jupyter Notebook with access to the content of this GitHub repository in your AWS account.    Prior to launching this, please login to the [MIMIC PhysioNet website](https://mimic.mit.edu/), [input your AWS account number](https://physionet.org/settings/cloud/), and [request access to the MIMIC-III Clinical Database on AWS](https://physionet.org/projects/mimiciii/1.4/request_access/2).  

To start this deployment, click the Launch Stack button.  On the first screen, the template link has already been specified, so just click next.  On the second screen, provide a Stack name (letters and numbers) and click next, on the third screen, just click next.  On the forth screen, at the bottom, there is a box that says **I acknowledge that AWS CloudFormation might create IAM resources.**.  Check that box, and then click **Create**.  Once the Stack has complete deploying, look at the **Outputs** tab of the AWS CloudFormation console for links to your Jupyter Notebooks instance.

[![cloudformation-launch-stack](/mimic-iii/buildmimic/aws-athena/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=MIMIC&templateURL=https://aws-bigdata-blog.s3.amazonaws.com/artifacts/biomedical-informatics-studies/mimic-iii-athena.yaml)

## mimic_utils package

This package contains utilities for working with the MIMIC datasets; primarily transpiling SQL code.

### Installation

```bash
pip install -e ".[test]"
```

### Development

The repository includes a locked dependency file (`requirements-lock.txt`) generated by `pip-compile` for reproducible builds on Python 3.9. To use it:

```bash
pip install -r requirements-lock.txt
pip install -e . --no-deps
```

To update the lock file after changing dependencies in `pyproject.toml`:

```bash
pip-compile pyproject.toml --output-file requirements-lock.txt --all-extras --strip-extras --upgrade
```

### Running tests

```bash
pytest tests/
```

## Other useful tools

* [Bloatectomy](https://github.com/MIT-LCP/bloatectomy) ([paper](https://github.com/MIT-LCP/bloatectomy/blob/master/paper/bloatectomy_paper.md)) - A python based package for removing duplicate text in clinical notes
* [Medication categories](https://github.com/mghassem/medicationCategories) - Python script for extracting medications from free-text notes
* [MIMIC Extract](https://github.com/MLforHealth/MIMIC_Extract) ([paper](https://doi.org/10.1145/3368555.3384469)) - A python based package for transforming MIMIC-III data into a machine learning friendly format
* [FIDDLE](https://github.com/MLD3/FIDDLE) ([paper](https://doi.org/10.1093/jamia/ocaa139)) - A python based package for a FlexIble Data-Driven pipeLinE (FIDDLE), transforming structured EHR data into a machine learning friendly format

## Acknowledgement

If you use code or concepts available in this repository, we would be grateful if you would:

- cite the dataset(s) you use as described in the PhysioNet project page: [MIMIC-III](https://physionet.org/content/mimiciii/), [MIMIC-IV](https://physionet.org/content/mimiciv/), [MIMIC-IV-ED](https://physionet.org/content/mimic-iv-ed/) , and/or [MIMIC-CXR](https://physionet.org/content/mimic-cxr/)
- cite the Zenodo repository directly as it contains a static copy of the code. Be sure to select the release of MIMIC Code you used from the menu on the right side of the page on Zenodo: https://zenodo.org/record/6818823
- cite the MIMIC code repository paper: [The MIMIC Code Repository: enabling reproducibility in critical care research](https://doi.org/10.1093/jamia/ocx084)

```bibtex
@article{johnson2018mimic,
  title={The MIMIC Code Repository: enabling reproducibility in critical care research},
  author={Johnson, Alistair E W and Stone, David J and Celi, Leo A and Pollard, Tom J},
  journal={Journal of the American Medical Informatics Association},
  volume={25},
  number={1},
  pages={32--39},
  year={2018},
  publisher={Oxford University Press}
}
```

## Contributing

Our team has worked hard to create and share the MIMIC datasets. We encourage you to share the code that you use for data processing and analysis. Sharing code helps to make studies reproducible and promotes collaborative research. To contribute, please:

* Fork the repository using the following link: https://github.com/MIT-LCP/mimic-code/fork. For a background on GitHub forks, see: https://help.github.com/articles/fork-a-repo/
* Commit your changes to the forked repository.
* Submit a pull request to the [MIMIC code repository](https://github.com/MIT-LCP/mimic-code), using the method described at: https://help.github.com/articles/using-pull-requests/

We encourage users to share concepts they have extracted by writing code which generates a table. These derived tables can then be used by researchers around the world to speed up data extraction. See the [mimic-iv/concepts](mimic-iv/concepts/) folder for examples.

### License

By committing your code to the [MIMIC Code Repository](https://github.com/mit-lcp/mimic-code) you agree to release the code under the [MIT License attached to the repository](https://github.com/mit-lcp/mimic-code/blob/main/LICENSE).

### Coding style

Please refer to the [style guide](https://github.com/MIT-LCP/mimic-code/blob/main/styleguide.md) for guidelines on formatting your code for the repository.
