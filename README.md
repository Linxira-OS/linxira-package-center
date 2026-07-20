# Linxira Package Center

Linxira Package Center is the user-facing application and optional-capability
manager for Linxira OS.

Current source version: `0.1.0`.

The current Phase 1 implementation is an install-only kdialog client for catalog
v2. It lists individually reviewed applications, creates a catalog-bound plan,
confirms the unchanged plan, and delegates the privileged transaction to
`linxira-components`. It never constructs package commands or invokes pacman.

## Ownership

- `linxira-package-center` owns selection UI, transaction presentation, progress,
  history, installed-state presentation, and the future Gaming Setup workflow.
- `linxira-catalog` owns selectable metadata and policy.
- `linxira-components` owns plan, confirmation, privileged apply, verification,
  and receipts.
- `linxira-config-hub` owns configuration and diagnostic CLI workflows, not
  application installation.

Package removal is intentionally unavailable until the shared backend has an
ownership ledger, dependency attribution, and drift detection. Catalog v3 and a
native tree UI will replace the current catalog v2 checklist after the P1
installability gate.

## Runtime

- Bash
- `jq`
- `kdialog`
- `pkexec`
- `/usr/bin/linxira-components`
- `/usr/share/linxira/catalog/catalog-v2.json`

## Development

```console
python -m unittest discover -s tests -v
bash -n src/linxira-package-center
```
