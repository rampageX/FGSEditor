# FGSEditor v4.0.1

First release of the rampageX fork, based on PingWer/FGSEditor v4.0.0.

- Remember successful video, grain-table and template directories across restarts.
- Restore independent main, dynamic timeline and event editor window positions and sizes; recover off-screen windows.
- Save & Apply uses the current unsaved grain data and preserves the original video association.
- Apply static or dynamic grain tables in the background with cancellation, preserving event gaps and open-ended timestamps.
- Write a new MKV without re-encoding video pixels; retain original audio, subtitles, attachments, chapters and metadata where supported.
- Fix Apply after closing an event editor and protect existing output files.

## Windows package

Extract the ZIP and run FGSEditor.exe. grav1synth v0.2.2 is included. Configure external ffmpeg.exe and ffprobe.exe paths in Settings; these executables are not bundled.

Windows unit checks, real AV1 grain replacement/integrity checks and packaged EXE startup are required before publication. Directory/window behavior and saving an applied video were also tested by the maintainer. Mixed-DPI/multi-monitor edge cases remain hardware-dependent. Grain-texture preview is not implemented in this release.

Original author and copyright notices are retained in NOTICE.md and the application credits.
