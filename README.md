# code-style

[![CI](https://github.com/wrxck/code-style/actions/workflows/ci.yml/badge.svg)](https://github.com/wrxck/code-style/actions/workflows/ci.yml)

Code style enforcement for Claude Code sessions.

## What it checks

- **Comments**: lowercase only, British English spelling, no unnecessary comments
- **Imports**: proper grouping and ordering (node built-ins, external, internal aliases, relative)
- **File length**: warns when files exceed recommended line counts per file type
- **Icons/Emojis**: prefer Huge Icons library, no emoji characters in code
- **TODOs**: must reference a ticket/issue number for tracking
- **Library choices**: informational notes on library alternatives (non-blocking)

## Installation

```
claude plugin marketplace add wrxck/claude-plugins
claude plugin install code-style@wrxck-claude-plugins
```
