# Changelog

All notable changes to this project are documented here. Versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

- Version number from the release tag (`git describe --tags`) instead of the commit id, shown in a footer on every
  page together with license and project link; `scripts/update.sh` builds with this version.

## [1.0.0] – 2026-11-15

First public release of Interview-Leitfaden: a self-hosted web app (German UI) that guides interviewers question by
question through an interview and helps evaluate the results.

### Features

- **Projects and groups:** interviews and target groups belong to a project; projects can be copied including their
  groups and question catalogs.
- **Question catalogs:** import from CSV (encoding detection), XLSX or JSON with preview and error list; editor with
  drag & drop, versioning and required questions.
- **Interview mode:** one question at a time with keyboard shortcuts, notes with autosave, overall note, status per
  question; the catalog is snapshotted so later edits never change past interviews.
- **Audio and transcription:** attach recordings (e.g. OBS .mkv with separate tracks) and transcribe them with a
  speech model on your own OpenAI-compatible server (e.g. vLLM), in a background job.
- **AI evaluation:** summary and assessment of a single interview (including the transcript) via your own LLM server;
  project-wide analysis with a short summary; system prompts adjustable globally and per project.
- **Exports:** single interviews as PDF, Markdown or CSV; all interviews of a project as one Markdown or JSON file;
  AI evaluation and analysis as Markdown or PDF.
- **Multi-user for the intranet:** accounts with roles *Admin* and *Interviewer*, projects assigned to interviewers,
  interviewers edit only their own interviews; scrypt password hashes, signed session cookies, login throttling.
- **Operations:** Docker Compose setup, daily database backup, backup ZIP download, restore with undo,
  `scripts/update.sh` for updates with backup and version check, notice in the browser when a new version is installed.
- **Documentation (German):** step-by-step installation guide and user manual (also as PDF).

### Known limitations

- Intended for a single computer or an intranet, **not** for direct exposure to the internet.
- Audio files are not part of the backup ZIP; back up `data/audio/` separately.
- Running transcriptions and LLM requests cannot be cancelled on the server side.
- Very large projects are truncated for the project analysis instead of being processed in several passes.

[1.0.0]: https://github.com/rainer-sharp/Interview-Leitfaden/releases/tag/v1.0.0
