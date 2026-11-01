# Security review — portfolio version

## Improvements implemented

- Removed the hard-coded `admin/admin`, `manager/1234`, and `reception/1234` accounts.
- Added first-launch administrator creation, minimum length for newly created passwords, and salted PBKDF2-HMAC-SHA256 password storage.
- On startup, passwords from an existing trusted local database are migrated from plaintext; **existing weak passwords may remain weak after hashing** and must be changed. Legacy plaintext DBs and backups must never be published.
- Login and password reset/change use password verification/hashing rather than SQL plaintext comparisons.
- Reservation creation and updates use an immediate transaction and re-check room availability inside it. Duplicate selected room IDs, invalid dates and over-capacity bookings are rejected.
- Financial inputs reject negative/non-finite amounts and are quantized with `Decimal` at the data-access boundary.
- Prevented deletion of guest/room reservation history and removal/demotion of the last administrator.
- SQLite backup/restore use SQLite's backup API for consistent snapshots.
- Source package excludes `.db`, WAL sidecars, backups, business data, executable and build artifacts; `.gitignore` reinforces this exclusion.

## Outstanding work before real-world deployment

1. **Backend authorization**: role controls are mostly UI-based; enforce authorization at the database/service boundary with a session/role context and test every privileged operation.
2. **Money storage**: migrate all `REAL` columns to integer cents, with tested conversions and a defined currency/rounding policy. Decimal input rounding alone does not make existing SQLite REAL fully exact.
3. **Operational lifecycle**: add tests for every check-in/out transition, invoice calculation, service handling and multi-room status change.
4. **Backup and data protection**: encrypt sensitive backups, control file permissions, add retention and safe restore procedures, and validate GDPR/compliance requirements where applicable.
5. **GUI testing and accessibility**: full desktop flows need GUI/system testing on Windows or another supported desktop.
6. **Secrets/password policy**: add robust login rate limiting, stronger password policy and recovery flows for a network-connected or multi-user production environment.
7. **Software rights**: clarify permissions for any code written for a third-party hotel before making a public repository.

This is **not a professional security audit**. Do not use with real customer, identity or payment records without further work.
