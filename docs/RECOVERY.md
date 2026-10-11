# Source recovery and compatibility

On 11 October 2026, the user authorized committing the reviewed Inventory source to private `Denberg28/inventory`. Its default main branch had no commits. Workspace maintenance had removed the original checkout. Both saved archives had file records but could not be made accessible to the execution workspace; the download link also failed for the user. No source was uploaded from those inaccessible records.

The user then explicitly chose **Rebuild and commit**. Candidate 0.1.0a3 is an independently implemented reconstruction of the documented requirements. It is not the original source and does not inherit its test results or signing identity. No prior EXE or signing key was recovered.

| Version | Source identity | Actual compatibility status |
| --- | --- | --- |
| 0.1.0a1 | Historical local ce26dcd757030998f2f96fc104d9bbf69ea51b9d | Source/fixture currently unavailable |
| 0.1.0a2 | Historical local 168987169df65c1d840d463a0a5fd1ae75acdb68 | Source/fixture currently unavailable; earlier 59 tests not rerun against reconstructed source |
| 0.1.0a3 | c65ef374badbf9309f6d81bcb4548273a9e8afaa | Known-good rebuilt baseline: 51 tests, Linux and Windows private CI passed; schema 2 |
| 0.1.0a4 | Current reviewed repository commit | Same schema 2/file/package identity; v0.1.0a3 synthetic upgrade and reverse restore verified; schema-1 migration BLOCKED |

The application name stays DroneLabInventory; rebuilt data is `inventory-v2.sqlite3`. Older `inventory.sqlite3` files remain untouched. Opening/restoring an unsupported schema fails before changes. Do not rename an older database to the new filename. A CSV from an older report is not a complete migration: custody/history would be lost. Preserve it and obtain verified migration tooling after the actual schema-1 database can be tested.

## Installation / upgrade / rollback

Download/extract the full source into a new program folder; install Python 3.12/Tk, launch Start-Inventory.cmd. For another schema-2 candidate, first make and verify a backup; close Inventory, then replace only the program folder. User data stays outside that folder.

Restore saves a dated `before-restore-*.sqlite3` recovery copy. To undo a restore, use Data → Restore backup on that copy. Keep both backups until the result is checked. If startup refuses corrupted data, close Inventory, retain its DB/WAL/SHM files together, and copy a verified schema-2 backup into a separate test location before recovery. Do not delete WAL files while the database is open.

To roll back 0.1.0a4 to 0.1.0a3, make and verify a current backup, close Inventory and restore the complete v0.1.0a3 program folder from the baseline commit or retained Windows artifact. Data and stock-count events remain readable by v0.1.0a3; counts appear as Receive/Issue/Edit with the explicit count note. No schema conversion is needed. To undo a count, record a new physical count with a reason; never delete its event.

Rollback to the inaccessible schema-1 reconstruction means retaining its current data/backups and stopping its use. A runnable original candidate cannot be promised until recovered. Use any independently retained original application only with its matching original database/backup. Never feed schema-2 data to schema-1 software.
