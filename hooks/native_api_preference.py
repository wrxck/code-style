#!/usr/bin/env python3
"""
Claude Code hook to evaluate library choices.
NOT a blocker - provides context to make informed decisions.
Reminds to evaluate if a library is the best choice, not just the default.
"""

import json
import re
import sys
from pathlib import Path

TS_EXTENSIONS = {'.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs'}

# library considerations - not blockers, just things to think about
LIBRARY_NOTES = [
    # http clients
    (r'from\s+[\'"]axios[\'"]', 'axios',
     'axios vs fetch: axios has interceptors, automatic transforms, better error handling. '
     'fetch is native but needs more boilerplate. choose based on needs.'),

    # date libraries
    (r'from\s+[\'"]moment[\'"]', 'moment.js',
     'moment is deprecated and heavy. date-fns (tree-shakeable), dayjs (tiny), '
     'or native Temporal API (modern) are better options.'),
    (r'from\s+[\'"]dayjs[\'"]', 'dayjs',
     'dayjs: tiny (2kb), moment-compatible API. good choice for most projects.'),
    (r'from\s+[\'"]date-fns[\'"]', 'date-fns',
     'date-fns: tree-shakeable, functional. good for projects using few date operations.'),

    # utility libraries
    (r'from\s+[\'"]lodash[\'"]$', 'lodash (full)',
     'importing full lodash adds ~70kb. prefer lodash-es or individual imports like lodash/debounce. '
     'many methods have native equivalents.'),
    (r'from\s+[\'"]lodash/', 'lodash (modular)',
     'good - using modular lodash import. verify native alternative doesn\'t exist.'),
    (r'from\s+[\'"]lodash-es[\'"]', 'lodash-es',
     'lodash-es is tree-shakeable. good choice if you need multiple lodash utilities.'),

    # state management - just notes, not recommendations
    (r'from\s+[\'"]redux[\'"]', 'redux',
     'redux: powerful but verbose. zustand/jotai are simpler for most cases. '
     'redux toolkit reduces boilerplate if redux is needed.'),

    # form libraries
    (r'from\s+[\'"]formik[\'"]', 'formik',
     'formik: larger bundle, less maintained. react-hook-form is lighter and more active.'),

    # animation
    (r'from\s+[\'"]framer-motion[\'"]', 'framer-motion',
     'framer-motion: powerful but heavy (~30kb). motion (same author, lighter) '
     'or CSS animations may suffice.'),

    # uuid
    (r'from\s+[\'"]uuid[\'"]', 'uuid',
     'crypto.randomUUID() is native in modern browsers/node. uuid package needed for '
     'older environments or specific uuid versions (v1, v5).'),

    # classnames
    (r'from\s+[\'"]classnames[\'"]', 'classnames',
     'clsx is a smaller drop-in replacement. template literals work for simple cases.'),
    (r'from\s+[\'"]clsx[\'"]', 'clsx',
     'clsx: tiny classname utility. good choice.'),
]


def is_ts_file(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in TS_EXTENSIONS


def check_library_usage(content: str, file_path: str) -> list[str]:
    """check for library imports and provide context, not blocking"""
    if not is_ts_file(file_path):
        return []

    notes = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, 1):
        for pattern, lib_name, note in LIBRARY_NOTES:
            if re.search(pattern, line):
                notes.append(f"{lib_name}: {note}")
                break

    return notes


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    if not file_path:
        sys.exit(0)

    content = tool_input.get('new_string', '') or tool_input.get('content', '')
    if not content:
        sys.exit(0)

    notes = check_library_usage(content, file_path)

    if notes:
        # output as context, not as error - exit 0 means success
        print("library notes (not blocking):")
        for note in notes[:3]:
            print(f"  • {note}")
        # exit 0 - this is informational, not a blocker
        sys.exit(0)

    sys.exit(0)


if __name__ == '__main__':
    main()
