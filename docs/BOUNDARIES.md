# Product Boundaries

Package Center may read catalog and installed-state data, collect a user
selection, display an immutable plan, request authorization for an already
confirmed transaction, and display backend progress and receipts.

Package Center must not:

- accept package names or shell commands from UI input;
- invoke pacman, AUR helpers, Flatpak, npm, or other installers directly;
- own catalog metadata or duplicate backend validation;
- install drivers, kernels, or system updates as hidden application side effects;
- remove packages before ownership and drift contracts are implemented;
- mutate sources, SSH, network, firewall, or service configuration.

Gaming Setup belongs here as a specialized selection workflow. Driver findings
route to Hardware/Driver Manager and remain a separate transaction boundary.
