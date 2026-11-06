# Android 11 native runtime diagnostic

This branch contains an internal test, not a new downloadable release. The main
branch and its existing APK are not changed by the test.

The SHA-bound 21 MB patch reconstructs the already signed internal APK from the
existing candidate 004. The reconstructed file must have SHA256
`499027020bc20b2b9a829ab3889b78544523ae241e0b599825e62710abf4b61f`.
No signing key is included. Standard Android package installation remains enabled.

The workflow requires KVM and an official Android 11 Google APIs image with its
ARM compatibility layer. It launches the actual Unity activity, blocks only the
game UID's external traffic, and records screenshots and actual device logs.
It publishes evidence to a separate `sgm-android11-evidence-*` branch. A workflow
success or a running game process does **not** establish that gameplay works.
The login, character creation, original map, movement, combat and save/load flow
still require review and verification before a release can be offered.
