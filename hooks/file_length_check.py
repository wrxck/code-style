#!/usr/bin/env python3
"""
Claude Code hook to check file length.
Warns when files exceed recommended length thresholds.
"""

import json
import sys
from pathlib import Path

# maximum recommended lines by file type
MAX_LINES = {
    '.ts': 300,
    '.tsx': 250,  # react components should be smaller
    '.js': 300,
    '.jsx': 250,
    '.py': 400,
    '.go': 400,
    '.rs': 400,
    '.java': 400,
    '.cs': 400,
    '.rb': 300,
    '.vue': 300,
    '.svelte': 250,
}

# default for unlisted types
DEFAULT_MAX = 500


def get_max_lines(file_path: str) -> int:
    """get maximum recommended lines for file type"""
    ext = Path(file_path).suffix.lower()
    return MAX_LINES.get(ext, DEFAULT_MAX)


def check_file_length(file_path: str, content: str) -> list[str]:
    """check if file exceeds recommended length"""
    issues = []

    lines = content.split('\n')
    line_count = len(lines)
    max_lines = get_max_lines(file_path)

    if line_count > max_lines:
        overage = line_count - max_lines
        percentage = (line_count / max_lines - 1) * 100

        if percentage > 50:
            severity = "significantly"
        elif percentage > 25:
            severity = "moderately"
        else:
            severity = "slightly"

        issues.append(
            f"file has {line_count} lines ({severity} over {max_lines} recommended) - "
            f"consider splitting into smaller modules"
        )

        # suggest what to look for
        suggestions = []
        if Path(file_path).suffix.lower() in {'.tsx', '.jsx'}:
            suggestions.append("extract components into separate files")
            suggestions.append("move hooks to custom hook files")
            suggestions.append("extract utility functions")
        else:
            suggestions.append("extract related functions into separate modules")
            suggestions.append("consider single responsibility principle")
            suggestions.append("look for code that could be shared utilities")

        for suggestion in suggestions[:2]:
            issues.append(f"  suggestion: {suggestion}")

    return issues


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

    issues = check_file_length(file_path, content)

    if issues:
        print("file length warning:", file=sys.stderr)
        for issue in issues:
            print(f"  • {issue}", file=sys.stderr)
        # this is a warning, not a blocker
        sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
