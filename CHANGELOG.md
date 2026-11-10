# Changelog

## v1.12.0 - 2026-11-10

- Add `healthai dashboard` / `./run dashboard` for private, standalone HTML reports from Apple Health XML, ZIP, or export directories.
- Introduce Monthly Report, Monthly Recap, and Observatory templates, plus Field Notes; switch layouts inside the same offline file.
- Show steps, sleep, resting heart rate, HRV, and workouts with monthly comparisons, 7/30/90-day trends, source coverage, accessible data tables, and print/PDF support.
- Reuse source reconciliation, normalize HRV and resting heart rate units, preserve missing-data gaps, and validate inputs and workout durations.
- Include fictional demos, a downloadable template gallery, explicit month/source filters, and output protection against overwriting existing reports.
- Add 23 dashboard regression tests; retain all existing export and analysis tests.

## v1.11.0 - 2026-11-02

- Add `healthai convert` / `./run convert` for offline XML or ZIP conversion to raw CSV/JSON without AI setup, preferences, telemetry, or third-party imports.
- Stream conversion with bounded record memory, progress, complete CSV headers, nested workout details, and local counts/checksums. Raw values and units remain unchanged.
- Publish output folders only after successful conversion; reject existing destinations and report malformed XML, changed inputs, unsupported elements, and write failures explicitly.
- Add synthetic export benchmarks and regression tests covering ZIP input, data preservation, offline operation, and failure cleanup.

## v1.4.2 - 2025-12-17

- Add `./run` auto-venv runner to simplify startup and avoid PEP 668 (Homebrew “externally managed”) issues.
- Update `Makefile` with `run`, `setup-venv`, `install`, and `clean-venv` convenience targets.
- Refresh README Quick Start to promote one-command usage and add note for `chmod +x run` / `bash ./run` on macOS/Linux.
- Bump internal version to `1.4.2`.

## v1.4.1

- Prior release with expanded AI integrations and data export utilities.
