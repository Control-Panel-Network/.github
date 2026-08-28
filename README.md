# Control Panel Network organization defaults

This repository holds **organization-wide community health files** and reusable
workflow templates for [Control-Panel-Network](https://github.com/Control-Panel-Network).

GitHub uses these defaults for public repositories in the organization that do
not define their own copies:

- `CODE_OF_CONDUCT.md`
- `CONTRIBUTING.md`
- `SECURITY.md`

## Security baseline for new repositories

Organization settings enable for **new** repositories (where the plan allows):

- Dependency graph
- Dependabot alerts
- Dependabot security updates
- Secret scanning
- Secret scanning push protection
- Required web commit sign-off

Per-repository Advanced Setup should still add:

- `.github/dependabot.yml` for version updates
- CodeQL (or org Code Security default configuration) for code scanning
- Private vulnerability reporting enabled in repository Settings → Code security

## Workflow templates

See `workflow-templates/` for starter workflows that repository maintainers can
add from the GitHub Actions “New workflow” UI.
