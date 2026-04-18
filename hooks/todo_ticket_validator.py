#!/usr/bin/env python3
"""
Claude Code hook to ensure TODO comments have ticket references.
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

TICKET_PATTERNS = [
    r'#\d+',
    r'[A-Z]+-\d+',
    r'GH-\d+',
    r'bug/\d+',
    r'issue/\d+',
    r'ticket/\d+',
    r'\bT\d{4,}',
    r'b/\d+',
    r'crbug\.com/\d+',
    r'go/\w+',
]


def strip_strings_and_comments(code):
    out = []
    i = 0
    n = len(code)
    lc = bc = sq = dq = bt = False
    while i < n:
        c = code[i]
        if lc:
            if c == '\n':
                lc = False; out.append(c)
            else:
                out.append(' ')
            i += 1; continue
        if bc:
            if c == '*' and i + 1 < n and code[i + 1] == '/':
                out.append('  '); i += 2; bc = False; continue
            out.append('\n' if c == '\n' else ' '); i += 1; continue
        if sq or dq or bt:
            q = "'" if sq else ('"' if dq else '`')
            if c == '\\' and i + 1 < n:
                out.append('  '); i += 2; continue
            if c == q:
                out.append(q); i += 1
                sq = dq = bt = False
                continue
            out.append('\n' if c == '\n' else ' '); i += 1; continue
        if c == '/' and i + 1 < n and code[i + 1] == '/':
            lc = True; out.append('  '); i += 2; continue
        if c == '/' and i + 1 < n and code[i + 1] == '*':
            bc = True; out.append('  '); i += 2; continue
        if c == "'":
            sq = True; out.append("'"); i += 1; continue
        if c == '"':
            dq = True; out.append('"'); i += 1; continue
        if c == '`':
            bt = True; out.append('`'); i += 1; continue
        out.append(c); i += 1
    return ''.join(out)


def is_code_file(fp):
    return Path(fp).suffix.lower() in CODE_EXTENSIONS


def has_ticket_reference(comment):
    for p in TICKET_PATTERNS:
        if re.search(p, comment, re.IGNORECASE):
            return True
    return False


def check_todos(content, fp):
    if not is_code_file(fp):
        return []
    issues = []
    ext = Path(fp).suffix.lower()
    c_style = ext in {'.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.java',
                      '.c', '.cpp', '.h', '.go', '.rs', '.php', '.swift',
                      '.kt', '.scala', '.cs'}
    comment_spans = find_comment_spans(content) if c_style else []
    todo_pattern = re.compile(
        r'(?P<pre>(?:^|\s)(?://|/\*|\*|#|--|<!--))\s*(?P<kw>TODO|FIXME|HACK|XXX)\b[:\s]*(?P<text>[^\n\r]*)',
        re.IGNORECASE,
    )
    if c_style:
        for start, end, start_line in comment_spans:
            segment = content[start:end]
            for m in re.finditer(
                r'(?P<kw>TODO|FIXME|HACK|XXX)\b[:\s]*(?P<text>[^\n\r]*)',
                segment, re.IGNORECASE,
            ):
                kw = m.group('kw').upper()
                text = m.group('text').strip()
                full = f"{kw} {text}"
                if has_ticket_reference(full):
                    continue
                if re.search(r'\([^)]+\)', text):
                    continue
                ln = start_line + segment[:m.start()].count('\n')
                issues.append(
                    f"line {ln}: {kw} without ticket reference - add issue number (e.g., {kw}: #123 description)"
                )
    else:
        spans = find_hash_comment_spans(content) if ext in {'.py', '.rb', '.sh', '.bash'} else []
        if spans:
            for start, end, start_line in spans:
                segment = content[start:end]
                for m in re.finditer(
                    r'(?P<kw>TODO|FIXME|HACK|XXX)\b[:\s]*(?P<text>[^\n\r]*)',
                    segment, re.IGNORECASE,
                ):
                    kw = m.group('kw').upper()
                    text = m.group('text').strip()
                    full = f"{kw} {text}"
                    if has_ticket_reference(full):
                        continue
                    if re.search(r'\([^)]+\)', text):
                        continue
                    ln = start_line + segment[:m.start()].count('\n')
                    issues.append(
                        f"line {ln}: {kw} without ticket reference - add issue number (e.g., {kw}: #123 description)"
                    )
        else:
            anchored = re.compile(
                r'^(?P<pre>\s*(?:#|--|<!--))\s*(?P<kw>TODO|FIXME|HACK|XXX)\b[:\s]*(?P<text>.*)$',
                re.IGNORECASE,
            )
            for ln, line in enumerate(content.split('\n'), 1):
                m = anchored.match(line)
                if not m:
                    continue
                kw = m.group('kw').upper()
                text = m.group('text').strip()
                full = f"{kw} {text}"
                if has_ticket_reference(full):
                    continue
                if re.search(r'\([^)]+\)', text):
                    continue
                issues.append(
                    f"line {ln}: {kw} without ticket reference - add issue number (e.g., {kw}: #123 description)"
                )
    return issues


def find_hash_comment_spans(code):
    spans = []
    i = 0
    n = len(code)
    line_num = 1
    sq = dq = False
    while i < n:
        c = code[i]
        if c == '\n':
            line_num += 1; i += 1; continue
        if sq or dq:
            q = "'" if sq else '"'
            if c == '\\' and i + 1 < n:
                if code[i + 1] == '\n':
                    line_num += 1
                i += 2; continue
            if c == q:
                sq = dq = False
            i += 1; continue
        if c == "'":
            sq = True; i += 1; continue
        if c == '"':
            dq = True; i += 1; continue
        if c == '#':
            j = code.find('\n', i)
            if j == -1:
                j = n
            spans.append((i, j, line_num))
            i = j
            continue
        i += 1
    return spans


def find_comment_spans(code):
    spans = []
    i = 0
    n = len(code)
    line_num = 1
    sq = dq = bt = False
    while i < n:
        c = code[i]
        if c == '\n':
            line_num += 1; i += 1; continue
        if sq or dq or bt:
            q = "'" if sq else ('"' if dq else '`')
            if c == '\\' and i + 1 < n:
                if code[i + 1] == '\n':
                    line_num += 1
                i += 2; continue
            if c == q:
                sq = dq = bt = False
            i += 1; continue
        if c == "'":
            sq = True; i += 1; continue
        if c == '"':
            dq = True; i += 1; continue
        if c == '`':
            bt = True; i += 1; continue
        if c == '/' and i + 1 < n and code[i + 1] == '/':
            j = code.find('\n', i)
            if j == -1:
                j = n
            spans.append((i, j, line_num))
            i = j
            continue
        if c == '/' and i + 1 < n and code[i + 1] == '*':
            j = code.find('*/', i + 2)
            if j == -1:
                j = n
            spans.append((i, j, line_num))
            line_num += code[i:j].count('\n')
            i = j + 2
            continue
        i += 1
    return spans


def gather(tool_input):
    edits = tool_input.get('edits')
    if isinstance(edits, list) and edits:
        return '\n'.join(e.get('new_string', '') or '' for e in edits if isinstance(e, dict))
    return tool_input.get('new_string', '') or tool_input.get('content', '') or ''


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    ti = data.get('tool_input', {})
    fp = ti.get('file_path', '')
    if not fp:
        sys.exit(0)
    content = gather(ti)
    if not content:
        sys.exit(0)
    issues = check_todos(content, fp)
    if issues:
        print("todo tracking issues:", file=sys.stderr)
        for issue in issues[:5]:
            print(f"  - {issue}", file=sys.stderr)
        if len(issues) > 5:
            print(f"  ... and {len(issues) - 5} more", file=sys.stderr)
        print("\ntodos should reference a ticket for tracking", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == '__main__':
    main()
