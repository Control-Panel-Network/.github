# Security Policy

## Supported versions

Security fixes are applied on the default branch of each Control Panel Network
repository and released when practical. Prefer the latest release or default
branch when testing.

| Version | Supported |
|---|---|
| Latest release / default branch | Yes |
| Older releases | Best effort |

## Reporting a vulnerability

**Do not** open a public GitHub issue or public pull request for security-sensitive findings.

Prefer one of these private channels:

1. **GitHub Private Vulnerability Reporting** on the affected repository (Security → Advisories → Report a vulnerability), when enabled.
2. Contact an organization maintainer via GitHub:
   - [@master3395](https://github.com/master3395)
   - [@KraoESPfan1n](https://github.com/KraoESPfan1n)

Please include:

- Affected repository, version, commit, or package
- Steps to reproduce
- Impact (what an attacker could do)

You can expect an initial response within **7 days** when possible. Fixes may take longer depending on severity and available maintainer time.

## Scope notes

Organization projects may install system packages, open temporary installer ports, manage mail or DNS credentials, and store encrypted secrets on disk. Treat temporary bootstrap links, OAuth client secrets, and host credentials as sensitive.

## Operator guidance

- Never publish temporary installer or bootstrap URLs that include access tokens
- Prefer dedicated test machines while projects are experimental
- Enable MFA on GitHub accounts with write access
- Keep default branches protected with required checks when collaborators are added

## Incident response (lightweight checklist)

1. **Triage:** confirm severity and affected versions; keep discussion private until a fix is ready.
2. **Mitigate:** revoke or rotate leaked tokens; shut down exposed services; pin or bump vulnerable dependencies if needed.
3. **Fix:** develop on a private fork or private advisory branch when available.
4. **Release:** publish a fixed version or tag; note the issue in release notes without unnecessary exploit detail.
5. **Disclose:** publish or update the advisory after users have a reasonable path to upgrade.
