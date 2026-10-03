# Security policy

## Supported version

The latest released version receives security fixes.

## Reporting

Report suspected vulnerabilities privately to the repository owner before public disclosure. Do not include real creator data in a report.

## Deployment note

The app has no authentication layer and stores personal data (creator contacts and fees) in a local SQLite file. It is built to run on `127.0.0.1` for one user. A shared or networked deployment needs access control, TLS, backups, logging and retention policy, dependency updates and isolation appropriate to the data.

## Hardening in the code

- CSV and XLSX exports neutralise spreadsheet formula injection (cells starting with `=`, `+`, `-`, `@`).
- `defusedxml` protects XLSX parsing; a public demo (`SIGNAL_PUBLIC=1`) limits uploads to 20 MB, 100 MB expanded (XLSX), 50,000 rows and 100 columns, while the app run locally has no built-in data limits; `.xlsm` is refused.
- The HTML report escapes all user-entered text.
- SQL uses parameter binding; no user text is interpolated into queries.
- The Docker image runs as a non-root user.
