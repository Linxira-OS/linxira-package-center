# Linxira Package Center

Linxira Package Center is the user-facing application and optional-capability
manager for Linxira OS.

Current source version: `0.2.0`.

The Phase 1 implementation is an install-only PySide6 application. It defaults
to Catalog v3, presents reviewed applications in an expandable three-state
category tree, creates and shows a catalog-bound plan, confirms the unchanged
plan, and delegates the privileged transaction to `linxira-components`. It
never constructs package commands or invokes pacman.

Catalog v3 application categories come only from `categories` entries whose
`surface` is `applications`; their `children` arrays define the tree and
`primaryCategory` prevents duplicate projection. The default view contains only
`reviewed` + `available` + `default` channel Arch/pacman applications. Category
`selection` may be `multi`, `exclusive`, or `bounded` (with `maxSelected`).
Catalog v2 remains supported and continues to require `installer: true` and
`review.status: reviewed`.

The optional review-channel view is an explicit, view-only opt-in. AUR, WPS,
proprietary/mixed-license, and other third-party candidates are labelled with
their provider, source, review state, license, consent requirement, and catalog
reason. They are disabled and are not represented as supported installations.

## Ownership

- `linxira-package-center` owns selection UI, transaction presentation, progress,
  history, installed-state presentation, and the future Gaming Setup workflow.
- `linxira-catalog` owns selectable metadata and policy.
- `linxira-components` owns plan, confirmation, privileged apply, verification,
  and receipts.
- `linxira-config-hub` owns configuration and diagnostic CLI workflows, not
  application installation.

Package removal is intentionally unavailable until the shared backend has an
ownership ledger, dependency attribution, and drift detection. Installed items
are displayed as locked selected leaves and are never submitted as removals.

The filter provides reviewed/installable, installed, and view-only third-party
review-channel views. Installed state is optional and read from
`LINXIRA_INSTALLED_STATE_PATH`. The state document may
contain `installedApplications: [id, ...]` or an `applications` map whose values
have an installed state/status. If no state document is supplied, the catalog is
still fully usable and the Installed view is empty.

## Runtime

- Python 3.11+
- PySide6 6.7+
- `pkexec`
- `/usr/bin/linxira-components`
- `/usr/share/linxira/catalog/catalog-v3.json`

## Catalog v3 transaction contract

Catalog v3 planning uses an `org.linxira.component-selection.v1` document and
`linxira-components plan --selection`; it never uses `--application`. The
selection is bound to the exact catalog SHA-256 and release, and retains
category/application paths plus `optional` + `user` provenance.

The currently available `linxira-components` protocol requires every
`requestedBy` root to be a catalog bundle. Package Center therefore accepts a
v3 application category as a transaction root only when the catalog also
provides a bundle with the same ID, exactly the same direct application
children, and all children marked `optional`. This prevents a category click
from pulling required/recommended component side effects. If that contract is
absent, as in the current standalone Catalog v3, planning fails closed before
the backend is invoked. The catalog/backend repositories must add and validate
the category-root contract (and align the backend's object-form `artifact`
support) before those selections can install; Package Center does not forge a
bundle path or claim support.

## Development

```console
python -m pip install -r requirements.txt
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
python -m py_compile src/linxira-package-center
python -m compileall -q tests
```

To test with local data:

```console
LINXIRA_CATALOG_PATH=/path/to/catalog.json \
LINXIRA_COMPONENTS_CLI=/path/to/linxira-components \
LINXIRA_INSTALLED_STATE_PATH=/path/to/installed-state.json \
python src/linxira-package-center
```
