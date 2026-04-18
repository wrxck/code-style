#!/usr/bin/env python3
"""
Claude Code hook for icon library and emoji usage.
"""

import json
import re
import sys
from pathlib import Path

TS_EXTENSIONS = {'.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs'}

ICON_LIBRARIES = [
    (r'from\s+[\'"]react-icons', 'react-icons'),
    (r'from\s+[\'"]@heroicons/', '@heroicons'),
    (r'from\s+[\'"]@fortawesome/', '@fortawesome (Font Awesome)'),
    (r'from\s+[\'"]lucide-react', 'lucide-react'),
    (r'from\s+[\'"]@phosphor-icons/', '@phosphor-icons'),
    (r'from\s+[\'"]@tabler/icons', '@tabler/icons'),
    (r'from\s+[\'"]@mui/icons-material', '@mui/icons-material'),
    (r'from\s+[\'"]@ant-design/icons', '@ant-design/icons'),
    (r'from\s+[\'"]bootstrap-icons', 'bootstrap-icons'),
    (r'from\s+[\'"]@iconify/', '@iconify'),
    (r'from\s+[\'"]feather-icons', 'feather-icons'),
    (r'from\s+[\'"]ionicons', 'ionicons'),
    (r'from\s+[\'"]@radix-ui/react-icons', '@radix-ui/react-icons'),
    (r'from\s+[\'"]react-feather', 'react-feather'),
]

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F6FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA70-\U0001FAFF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002700-\U000027BF"
    "\U0001F000-\U0001F02F"
    "]+",
    flags=re.UNICODE,
)

EMOJI_SHORTCODES = [
    chr(58) + chr(92) + chr(41),
    chr(58) + chr(92) + chr(40),
    chr(58) + chr(68),
    chr(59) + chr(45) + chr(63) + chr(92) + chr(41),
    chr(60) + chr(51),
    chr(58) + 'heart' + chr(58),
    chr(58) + 'smile' + chr(58),
    chr(58) + 'thumbsup' + chr(58),
    chr(58) + 'fire' + chr(58),
    chr(58) + 'rocket' + chr(58),
    chr(58) + 'star' + chr(58),
    chr(58) + 'check' + chr(58),
    chr(58) + 'x' + chr(58),
    chr(58) + 'warning' + chr(58),
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


def is_ts(fp):
    return Path(fp).suffix.lower() in TS_EXTENSIONS


def check_icon_libs(content, fp):
    if not is_ts(fp):
        return []
    out = []
    for ln, line in enumerate(content.split('\n'), 1):
        for pat, name in ICON_LIBRARIES:
            if re.search(pat, line):
                out.append(f"line {ln}: prefer Huge Icons instead of {name} - use 'hugeicons-react' package")
    return out


def check_emojis(content):
    out = []
    stripped = strip_strings_and_comments(content)
    for ln, line in enumerate(stripped.split('\n'), 1):
        matches = EMOJI_PATTERN.findall(line)
        if matches:
            found = ''.join(matches)
            out.append(f"line {ln}: emoji detected '{found}' - do not use emojis in code")
    raw_lines = content.split('\n')
    for ln, line in enumerate(raw_lines, 1):
        is_comment = line.strip().startswith(('//', '#', '/*', '*'))
        if is_comment:
            continue
        for m in re.finditer(r'["\']([^"\']*)["\']', line):
            s = m.group(1)
            if EMOJI_PATTERN.search(s):
                out.append(f"line {ln}: emoji detected in string - do not use emojis in code")
                break
            for sc in EMOJI_SHORTCODES:
                if re.search(sc, s):
                    out.append(f"line {ln}: emoji shortcode detected in string - do not use emojis in code")
                    break
    return out


def validate(fp, content):
    return check_icon_libs(content, fp) + check_emojis(content)


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
    issues = validate(fp, content)
    if issues:
        print("icon/emoji issues detected:", file=sys.stderr)
        for issue in issues[:5]:
            print(f"  - {issue}", file=sys.stderr)
        if len(issues) > 5:
            print(f"  ... and {len(issues) - 5} more issues", file=sys.stderr)
        print("\nreminder: use Huge Icons (hugeicons-react) for icons, never use emojis in code", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == '__main__':
    main()
