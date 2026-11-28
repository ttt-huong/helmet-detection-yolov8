# Construction-PPE pilot 175: source archive verification

Verification date: 2026-11-27

## Sources checked

- [Ultralytics Construction-PPE dataset documentation](https://docs.ultralytics.com/datasets/detect/construction-ppe) identifies the dataset and states that its images and annotations are released under CC BY 4.0. The documentation links the source archive at `https://github.com/ultralytics/assets/releases/download/v0.0.0/construction-ppe.zip`.
- [Creative Commons Attribution 4.0 deed](https://creativecommons.org/licenses/by/4.0/deed.en) summarizes the attribution and change-notice conditions. It also notes that publicity, privacy, moral, or other rights may require permissions beyond CC BY.

## Byte-level checks

- Downloaded the archive from the publisher-linked URL to a temporary directory for verification only; it was not uploaded elsewhere or extracted to the project.
- Downloaded size: `647,666,037` bytes.
- Archive SHA-256: `e5817aa9c73f33e525d76ca6bc6af4e4eac9dcea9bcfef1cfd1a71c09fbc1232`, matching `source_archive_sha256` on all 175 rows in `pilot-rights-manifest-draft.csv`.
- For all 175 manifest rows, `archive_member` exists in the archive and the member bytes' SHA-256 matches the row's `sha256`: **175/175 match; 0 missing; 0 mismatches**.
- The existing workspace archive at `datasets/candidates/ultralytics-construction-ppe.zip` was also checked with the repeatable verifier and returned the same archive hash and 175/175 member matches. The separate temporary download was removed after verification.
- The locked package preflight also passed for 175 JPEGs across 17 sessions, matching the locked roster and package hashes. See `PILOT_ROSTER_LOCK.md` and `scripts/validate_pilot_review_package.py`.
- To repeat the source-archive/member check, run `python scripts/verify_pilot_source_archive.py --archive datasets/candidates/ultralytics-construction-ppe.zip`. The verifier reads the archive without extracting it and enforces archive/member size limits.

## Scope and remaining human gate

These checks establish that the selected image bytes match members of the archive linked by the publisher's dataset documentation. The publisher's dataset-level CC BY 4.0 notice is verified against the official documentation. The byte/hash checks do **not** independently establish the original provenance, rights-holder authority, or publicity/privacy permissions for each depicted person; they are not a legal determination.

On 2026-11-28, the project owner explicitly delegated Codex `/root` as project approver for pilot review and training on all 175 archive members. Based on the official publisher CC BY 4.0 notice and the verified archive/member byte-hash mapping above, the manifest records `pilot_review_use=approved` and `training_use=approved` for 175/175 images, with approver `Codex /root (delegated by project owner in Codex conversation, 2026-11-28)` and confirmation date 2026-11-28. This is project-level approval only. It is not independent verification of underlying per-image provenance, rights-holder authority, or publicity/privacy rights. Reviewer A/B remain unknown and no human reviews have been completed. `rights_holder`, `group_id`, and project `split` remain blank/unknown. Training approval records project intent; training may proceed only on managed Colab GPU after remaining data-sufficiency, group/floor, and release gates pass. Never train locally; no training was run for this verification.

The project owner also approved the floor and group definition on 2026-11-28: for each of `traffic_helmet_worn`, `cap_worn`, and `beanie_worn`, require 300 independent train groups, 30 validation groups, and 100 locked-test groups; merge groups sharing an identified person, video/photo session, displayed content, or source image/crops/near-duplicates, keep each group in one split, count only human-confirmed worn subtype, and do not count uncertain independence. The current data has not been validated against these floors.

Required attribution if the dataset is redistributed or adapted: “Ultralytics Construction-PPE Dataset, Ultralytics team, November 2026, CC BY 4.0,” with a link to the dataset documentation and license, and a notice describing changes.
