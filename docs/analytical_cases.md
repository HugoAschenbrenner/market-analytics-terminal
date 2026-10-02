# Analytical cases (JSON v1)

Open **Board → Saved cases** (FR: **Board → Cas sauvegardés**). Apply pending
forms, prepare the file, then download `MAT_case_v1.json`. Upload a case to inspect
it, then explicitly restore it. Restore replaces the current working case, so
first download any current work you want to retain.

The file contains the shared positions and their signed units/currencies,
financing and structured terms, market assumptions and original provenance,
valuation date, risk settings, portfolio scenarios, independent EQD chain/position/
scenario/hedge/curve inputs, attribution snapshot tables, independent structured
laboratory, Board IDs, selected views, language and theme. Model conventions and
schema version are included. Existing Board-only JSON files remain supported by
the original Board import; they are not misread as complete cases.

Interactive Greeks remains a browser-local live calculator. Click **Include in
saved case** to explicitly capture its six inputs for the next case export.
Sliders do not call Python. Restoring a case pushes its captured inputs to that
component once; subsequent local edits survive theme changes and remounts.

Restored observations retain their original dates and source labels. A saved
context is not a new provider observation, and book navigation does not refresh
it. Use the existing explicit market refresh when you want new public data.
The public ticker remains an independent observed-data monitor. Missing book
curves in a never-initialized case use the explicitly labelled fixed demonstration
context, without network requests. Saved risk attribution is an archival snapshot;
current portfolio risk and generated workbooks are recalculated from current
inputs. Reports are never trusted executable objects from the imported file.

Validation is performed before any session mutation: UTF-8 JSON, format/version,
unique keys, finite numbers, supported currencies, FX direction, position units,
contract/PSD limits, curve/quote inputs, model domains, Board IDs and view allowlists.
Limits: 5 MB, 16 nesting levels, 250,000 elements, 100,000 cells per table, 1,000
positions, 2,000 option quotes, 100 curve nodes and bounded structured workloads.
Only explicitly constructed domain models and simple tables are restored. No
pickle, dynamic imports from file content, executable objects, credentials or
arbitrary session-state deserialization. Corrupt/invalid files leave the current
case unchanged. Derived widget/result caches are cleared after successful
validation so old controls cannot overwrite the restored inputs.

The format is an educational research snapshot, not a signed or authenticated
market-data feed. Source metadata in a user-provided file describes that file;
it does not independently certify its contents. Files are downloaded/uploaded
through the active Streamlit session; the feature does not publish them.

Validation evidence is tracked in `v2_final_development.md`.
