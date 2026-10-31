# Changelog

## Fork test build — 2026-10-31

- Remember successful video/table directories separately and restore three main window geometries.
- Preserve extracted video's association with dynamic and static editing.
- Replace blocking static-only Save & Apply with cancellable background metadata replacement.
- Allow Apply after the dynamic event editor has been closed and destroyed by Qt.
- Apply current unsaved data, including the open dynamic event editor; preserve event boundaries.
- Preserve open-ended u64 timestamps when loading events instead of clamping them to widget limits.
- Protect existing files and publish a new MKV only after all commands succeed.
- Remux original non-target streams, metadata and chapters using FFmpeg stream copy.
- Extract grain into a temporary directory instead of overwriting a source-side text file.
- Add Windows unit and real AV1 integration checks before packaging; bundle tool dependencies.
- Actual grain-texture preview remains a second-stage task.
