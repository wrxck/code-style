#!/usr/bin/env python3
"""
Claude Code hook to ensure TODO comments have ticket references.
TODOs should reference a ticket/issue for tracking.
"""

import json
import re
import sys
from pathlib import Path

CODE_EXTENSIONS = {
    '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs',
    '.py', '.rb', '.go', '.rs', '.java', '.cs', '.cpp', '.c', '.h',
    '.php', '.swift', '.kt', '.scala', '.sh', '.bash',
}

# patterns that indicate a ticket reference
TICKET_PATTERNS = [
    r'#\d+',           # github issues: #123
    r'[A-Z]+-\d+',     # jira style: ABC-123, PROJ-456
    r'GH-\d+',         # github: GH-123
    r'bug/\d+',        # bug/123
    r'issue/\d+',      # issue/123
    r'ticket/\d+',     # ticket/123
    r'\bT\d{4,}',      # phabricator: T1234
    r'b/\d+',          # google bug tracker style
    r'crbug\.com/\d+', # chromium bugs
    r'go/\w+',         # google go links
]


def is_code_file(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in CODE_EXTENSIONS


def has_ticket_reference(comment: str) -> bool:
    """check if comment contains a ticket reference"""
    for pattern in TICKET_PATTERNS:
        if re.search(pattern, comment, re.IGNORECASE):
            return True
    return False


def check_todos(content: str, file_path: str) -> list[str]:
    """check for TODOs without ticket references"""
    if not is_code_file(file_path):
        return []

    issues = []
    lines = content.split('\n')

    # patterns to match TODO/FIXME/HACK/XXX comments
    todo_pattern = re.compile(
        r'(?://|#|/\*|\*|--|<!--)\s*(TODO|FIXME|HACK|XXX)\b[:\s]*(.*)$',
        re.IGNORECASE
    )

    for line_num, line in enumerate(lines, 1):
        match = todo_pattern.search(line)
        if match:
            todo_type = match.group(1).upper()
            todo_text = match.group(2).strip()

            # check if there's a ticket reference
            full_comment = f"{todo_type} {todo_text}"
            if not has_ticket_reference(full_comment):
                # allow TODOs with specific owner
                if not re.search(r'\([^)]+\)', todo_text):  # (username) pattern
                    issues.append(
                        f"line {line_num}: {todo_type} without ticket reference - "
                        f"add issue number (e.g., {todo_type}: #123 description)"
                    )

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

    issues = check_todos(content, file_path)

    if issues:
        print("todo tracking issues:", file=sys.stderr)
        for issue in issues[:5]:
            print(f"  • {issue}", file=sys.stderr)
        if len(issues) > 5:
            print(f"  ... and {len(issues) - 5} more", file=sys.stderr)
        print("\ntodos should reference a ticket for tracking", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
