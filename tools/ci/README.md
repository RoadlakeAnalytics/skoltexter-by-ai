CI helper scripts
==================

This directory contains helper scripts to regenerate the project's lockfile
and build a per-Python-version wheelhouse used by the offline, hardened CI
jobs. The scripts are intentionally lightweight and do not use Docker — run
them on a developer machine or CI runner that matches your target platform.

Files
-----
- `regenerate_lockfile.sh` - Regenerate a pip-compile `requirements.lock` for a given Python. Usage:

  ```sh
  bash tools/ci/regenerate_lockfile.sh --python python3.12 --req requirements.txt --out lockfiles/requirements.lock-3.12
  ```

- `build_wheelhouse.sh` - Build wheels from a lockfile into a wheelhouse directory.

  ```sh
  bash tools/ci/build_wheelhouse.sh --python python3.12 --lock lockfiles/requirements.lock-3.12 --wheel-dir wheelhouse/3.12
  ```

Cross-platform downloads
------------------------
When running on macOS or Windows it can be useful to instruct `pip` to
download Linux manylinux wheels rather than the platform-specific wheels for
your machine. `build_wheelhouse.sh` supports optional flags that are
forwarded to `pip download` to request wheels for a different platform:

  - `--download-platform <platform>` e.g. `manylinux_2_28_x86_64`
  - `--download-python-version <version>` e.g. `3.12`
  - `--download-implementation <impl>` e.g. `cp`
  - `--download-abi <abi>` e.g. `cp312`
  - `--download-only-binary` to restrict downloads to binary wheels only

Example (fetch manylinux wheels for CPython 3.12):

  ```sh
  bash tools/ci/build_wheelhouse.sh --python python3.12 --lock lockfiles/requirements.lock-3.12 \
    --wheel-dir wheelhouse/3.12 --download-platform manylinux_2_28_x86_64 \
    --download-python-version 3.12 --download-implementation cp --download-abi cp312 --download-only-binary
  ```

Note: cross-platform downloads rely on PyPI hosting compatible manylinux
wheels for the requested platform. If a package only ships an sdist for that
platform `pip download --only-binary` will not fetch it and the subsequent
`pip wheel` step may attempt to build a wheel locally (which may not be
portable). For guaranteed portability, generate the wheelhouse on an
appropriate Linux runner (the CI `generate-locks` job already does this).

Notes & recommendations
-----------------------
- These scripts assume network access to download packages when building the
  wheelhouse. Run them on a machine that has the appropriate build toolchain
  (compilers and libraries) if any packages need to be compiled.
- For pure Python wheels this should work on most systems. If you require
  manylinux-compatible wheels for distribution, use a manylinux builder or CI
  infrastructure that produces manylinux wheels.
- After building the wheelhouse, upload the `wheelhouse/3.12` artifact using
  your CI provider so the hardened CI jobs can download it and perform
  offline installations.

Security / pip-audit
--------------------
- If `pip-audit` reports a vulnerable `pip` version in the lockfile, regenerate
  the lockfile (see `regenerate_lockfile.sh`) which will pick up newer
  `pip` versions if available. Then rebuild the wheelhouse.

Example workflow
----------------
1. Regenerate the lockfile locally:

   ```sh
   bash tools/ci/regenerate_lockfile.sh --python python3.12 --req requirements.txt --out lockfiles/requirements.lock-3.12
   git add lockfiles/requirements.lock-3.12 && git commit -m "Regenerate lockfile for 3.12"
   ```

2. Build wheelhouse and verify strictly:

   ```sh
   bash tools/ci/build_wheelhouse.sh --python python3.12 --lock lockfiles/requirements.lock-3.12 --wheel-dir wheelhouse/3.12
   ```

3. Upload the `wheelhouse/3.12` artifact in your CI (the workflows in this
   repository expect that artifact name).

If you want assistance automating any of these steps (for example, a small
helper to package the wheelhouse as a CI artifact), open an issue or request
it in the PR and we will add it.
