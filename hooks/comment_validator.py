#!/usr/bin/env python3
"""
Claude Code hook to validate code comments.
"""

import json
import re
import sys
from pathlib import Path

BRITISH_SPELLINGS = {
    'color': 'colour', 'colors': 'colours',
    'behavior': 'behaviour', 'behaviors': 'behaviours',
    'favor': 'favour', 'favors': 'favours',
    'favorite': 'favourite', 'favorites': 'favourites',
    'honor': 'honour', 'honors': 'honours',
    'humor': 'humour', 'labor': 'labour', 'labors': 'labours',
    'neighbor': 'neighbour', 'neighbors': 'neighbours',
    'rumor': 'rumour', 'rumors': 'rumours',
    'vapor': 'vapour', 'vigor': 'vigour',
    'initialize': 'initialise', 'initializes': 'initialises',
    'initialized': 'initialised', 'initializing': 'initialising',
    'initialization': 'initialisation',
    'organize': 'organise', 'organizes': 'organises',
    'organized': 'organised', 'organizing': 'organising',
    'organization': 'organisation',
    'recognize': 'recognise', 'recognizes': 'recognises',
    'recognized': 'recognised', 'recognizing': 'recognising',
    'synchronize': 'synchronise', 'synchronizes': 'synchronises',
    'synchronized': 'synchronised', 'synchronizing': 'synchronising',
    'optimize': 'optimise', 'optimizes': 'optimises',
    'optimized': 'optimised', 'optimizing': 'optimising',
    'optimization': 'optimisation',
    'utilize': 'utilise', 'utilizes': 'utilises',
    'utilized': 'utilised', 'utilizing': 'utilising',
    'utilization': 'utilisation',
    'customize': 'customise', 'customizes': 'customises',
    'customized': 'customised', 'customizing': 'customising',
    'customization': 'customisation',
    'analyze': 'analyse', 'analyzes': 'analyses',
    'analyzed': 'analysed', 'analyzing': 'analysing',
    'center': 'centre', 'centers': 'centres',
    'centered': 'centred', 'centering': 'centring',
    'meter': 'metre', 'meters': 'metres',
    'liter': 'litre', 'liters': 'litres',
    'fiber': 'fibre', 'fibers': 'fibres',
    'theater': 'theatre', 'theaters': 'theatres',
    'catalog': 'catalogue', 'catalogs': 'catalogues',
    'dialog': 'dialogue', 'dialogs': 'dialogues',
    'program': 'programme', 'programs': 'programmes',
    'defense': 'defence', 'offense': 'offence',
    'license': 'licence', 'practice': 'practise',
    'gray': 'grey', 'grays': 'greys',
    'canceled': 'cancelled', 'canceling': 'cancelling',
    'traveled': 'travelled', 'traveling': 'travelling',
    'traveler': 'traveller', 'travelers': 'travellers',
    'modeling': 'modelling', 'modeled': 'modelled',
    'labeled': 'labelled', 'labeling': 'labelling',
}

LINE_EXT = {'.py': '#', '.rb': '#', '.sh': '#', '.bash': '#', '.zsh': '#',
            '.pl': '#', '.yaml': '#', '.yml': '#', '.toml': '#',
            '.r': '#', '.R': '#'}

C_EXT = {'.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs', '.java', '.c', '.cpp',
         '.h', '.hpp', '.cs', '.go', '.rs', '.swift', '.kt', '.scala',
         '.scss', '.less', '.svelte', '.php'}

UNNECESSARY_PATTERNS = [
    r'^todo:?\s*$', r'^fixme:?\s*$', r'^hack:?\s*$', r'^note:?\s*$',
    r'^(increment|decrement)\s+(the\s+)?(counter|variable|value|i|j|k|x|y|z|n|count)',
    r'^(add|subtract)\s+(one|1)\s+(to|from)',
    r'^(set|assign)\s+\w+\s+to',
    r'^(return|returns)\s+(the\s+)?(result|value)',
    r'^(loop|iterate)\s+(through|over)',
    r'^(check|checking)\s+if',
    r'^(get|getting)\s+(the\s+)?\w+',
    r'^(set|setting)\s+(the\s+)?\w+',
    r'^(create|creating)\s+(a\s+)?(new\s+)?\w+',
    r'^(define|defining)\s+(a\s+)?\w+',
    r'^(call|calling)\s+(the\s+)?\w+',
    r'^(import|importing)\s+\w+',
    r'^(declare|declaring)\s+\w+',
    r'^end\s+(of\s+)?(function|method|class|loop|if|block)',
    r'^close\s+(the\s+)?(file|connection|stream)',
    r'^open\s+(the\s+)?(file|connection|stream)',
    r'^this\s+(function|method|class)\s+(does|will|is)',
    r'^constructor$', r'^destructor$', r'^getter$', r'^setter$',
    r'^default\s+(value|case)$',
]

PASCAL_RE = re.compile(r'[A-Z][a-z]+(?:[A-Z][a-z]+)+')


def strip_strings_and_comments(code):
    out = []
    i = 0
    n = len(code)
    lc = bc = sq = dq = bt = False
    while i < n:
        c = code[i]
        if lc:
            if c == '\n':
                lc = False
                out.append(c)
            else:
                out.append(' ')
            i += 1
            continue
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


def extract_comments(content, ext):
    comments = []
    if ext in LINE_EXT:
        m = LINE_EXT[ext]
        for ln, line in enumerate(content.split('\n'), 1):
            s = line.lstrip()
            if s.startswith(m):
                t = s[len(m):].lstrip()
                if t:
                    comments.append((ln, t))
        return comments
    if ext in C_EXT:
        i = 0
        n = len(content)
        line_num = 1
        sq = dq = bt = False
        while i < n:
            c = content[i]
            if c == '\n':
                line_num += 1; i += 1; continue
            if sq or dq or bt:
                q = "'" if sq else ('"' if dq else '`')
                if c == '\\' and i + 1 < n:
                    if content[i + 1] == '\n':
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
            if c == '/' and i + 1 < n and content[i + 1] == '/':
                j = content.find('\n', i)
                if j == -1:
                    j = n
                text = content[i + 2:j].strip()
                if text:
                    comments.append((line_num, text))
                i = j
                continue
            if c == '/' and i + 1 < n and content[i + 1] == '*':
                start = line_num
                j = content.find('*/', i + 2)
                if j == -1:
                    j = n
                inner = content[i + 2:j]
                line_num += inner.count('\n')
                text = re.sub(r'\s*\*+\s*', ' ', inner).strip()
                if text:
                    comments.append((start, text))
                i = j + 2
                continue
            if c == '#' and ext == '.php':
                j = content.find('\n', i)
                if j == -1:
                    j = n
                text = content[i + 1:j].strip()
                if text:
                    comments.append((line_num, text))
                i = j
                continue
            i += 1
        return comments
    if ext == '.css':
        for m in re.finditer(r'/\*(.*?)\*/', content, re.DOTALL):
            t = re.sub(r'\s*\*+\s*', ' ', m.group(1)).strip()
            if t:
                comments.append((content.count('\n', 0, m.start()) + 1, t))
        return comments
    if ext == '.lua':
        for ln, line in enumerate(lines, 1):
            s = line.lstrip()
            if s.startswith('--'):
                t = s[2:].lstrip()
                if t:
                    comments.append((ln, t))
        return comments
    if ext == '.sql':
        for ln, line in enumerate(lines, 1):
            s = line.lstrip()
            if s.startswith('--'):
                t = s[2:].lstrip()
                if t:
                    comments.append((ln, t))
        for m in re.finditer(r'/\*(.*?)\*/', content, re.DOTALL):
            t = m.group(1).strip()
            if t:
                comments.append((content.count('\n', 0, m.start()) + 1, t))
        return comments
    if ext in {'.html', '.xml', '.vue'}:
        for m in re.finditer(r'<!--(.*?)-->', content, re.DOTALL):
            t = m.group(1).strip()
            if t:
                comments.append((content.count('\n', 0, m.start()) + 1, t))
        return comments
    return comments


def is_licence_header(comment, line_num, has_star):
    if line_num > 20:
        return False
    if 'MIT' in comment or 'copyright' in comment.lower():
        return True
    return has_star


def check_lowercase(comment):
    if re.search(r'https?://', comment):
        return []
    pascal = [(m.start(), m.end()) for m in PASCAL_RE.finditer(comment)]

    def in_pascal(pos):
        return any(s <= pos < e for s, e in pascal)

    code_ref = r'`[^`]+`|[a-z]+[A-Z][a-zA-Z]*|[A-Z]{2,}'
    cleaned = re.sub(code_ref, lambda m: ' ' * (m.end() - m.start()), comment)
    sentences = re.split(r'(?<=[.!?])\s+', cleaned)
    for sentence in sentences:
        if not sentence.strip():
            continue
        words = sentence.split()
        first = True
        for word in words:
            stripped = word.strip(".,;:!?()[]{}\"'")
            if not stripped:
                continue
            if first:
                first = False
                continue
            if stripped.isupper() and len(stripped) <= 5:
                continue
            pos = cleaned.find(word)
            if pos != -1 and in_pascal(pos):
                continue
            if stripped[0].isupper():
                return [f"uppercase found: '{stripped}' should be lowercase"]
    return []


def check_british(comment):
    out = []
    low = comment.lower()
    for am, br in BRITISH_SPELLINGS.items():
        if re.search(rf'\b{am}\b', low):
            out.append(f"use british spelling: '{am}' -> '{br}'")
    return out


def check_unnecessary(comment):
    low = comment.lower().strip()
    if len(low.split()) > 5:
        return []
    for pat in UNNECESSARY_PATTERNS:
        if re.search(pat, low):
            return [f"potentially unnecessary comment: '{comment}' - comments should explain why, not what"]
    return []


def validate(file_path, content):
    ext = Path(file_path).suffix.lower()
    if not ext:
        return []
    comments = extract_comments(content, ext)
    issues = []
    lines = content.split('\n')
    for ln, comment in comments:
        raw = lines[ln - 1] if 1 <= ln <= len(lines) else ''
        has_star = bool(re.match(r'\s*\*', raw))
        if is_licence_header(comment, ln, has_star):
            continue
        for issue in check_lowercase(comment) + check_british(comment) + check_unnecessary(comment):
            issues.append(f"line {ln}: {issue}")
    return issues


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
        print("comment style issues detected:", file=sys.stderr)
        for issue in issues[:5]:
            print(f"  - {issue}", file=sys.stderr)
        if len(issues) > 5:
            print(f"  ... and {len(issues) - 5} more issues", file=sys.stderr)
        print("\nreminder: comments should be lowercase, use british spelling, and only added when necessary", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == '__main__':
    main()
