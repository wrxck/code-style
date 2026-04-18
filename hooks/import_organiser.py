#!/usr/bin/env python3
"""
Claude Code hook to enforce import organisation.
"""

import json
import re
import sys
from pathlib import Path

TS_EXTENSIONS = {'.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs'}

NODE_BUILTINS = {
    'assert', 'buffer', 'child_process', 'cluster', 'console', 'constants',
    'crypto', 'dgram', 'dns', 'domain', 'events', 'fs', 'http', 'https',
    'module', 'net', 'os', 'path', 'process', 'punycode', 'querystring',
    'readline', 'repl', 'stream', 'string_decoder', 'timers', 'tls',
    'tty', 'url', 'util', 'v8', 'vm', 'zlib', 'worker_threads', 'perf_hooks',
    'async_hooks', 'inspector', 'trace_events', 'wasi',
    'node:assert', 'node:buffer', 'node:child_process', 'node:cluster',
    'node:console', 'node:constants', 'node:crypto', 'node:dgram', 'node:dns',
    'node:domain', 'node:events', 'node:fs', 'node:http', 'node:https',
    'node:module', 'node:net', 'node:os', 'node:path', 'node:process',
    'node:punycode', 'node:querystring', 'node:readline', 'node:repl',
    'node:stream', 'node:string_decoder', 'node:timers', 'node:tls',
    'node:tty', 'node:url', 'node:util', 'node:v8', 'node:vm', 'node:zlib',
    'node:worker_threads', 'node:perf_hooks', 'node:async_hooks',
    'node:inspector', 'node:trace_events', 'node:wasi', 'node:test',
}

ALIAS_PREFIXES = ('@/', '~/', '#/', 'src/', '@app/', '@shared/')


def is_ts_file(file_path):
    return Path(file_path).suffix.lower() in TS_EXTENSIONS


def get_import_type(path):
    path = path.strip('\'"')
    base = path.split('/')[0]
    if base in NODE_BUILTINS or path.startswith('node:'):
        return 0
    if path.startswith('.'):
        return 3
    for p in ALIAS_PREFIXES:
        if path.startswith(p):
            return 2
    if path.startswith('@') and '/' in path:
        return 1
    return 1


def collapse_multiline_imports(content):
    def collapse(m):
        return re.sub(r'\s+', ' ', m.group(0))
    pattern = re.compile(
        r'import\s+(?:type\s+)?(?:[\w*,\s]*\{[^}]*\}[\w,\s]*|[\w*,\s]+)\s+from\s+[\'"][^\'"]+[\'"];?',
        re.DOTALL,
    )
    return pattern.sub(collapse, content)


def extract_imports(content):
    imports = []
    collapsed = collapse_multiline_imports(content)
    original_lines = content.split('\n')
    collapsed_lines = collapsed.split('\n')

    line_map = []
    orig_idx = 0
    for cl in collapsed_lines:
        line_map.append(orig_idx + 1)
        orig_idx += cl.count('\n') if False else 1

    pattern = re.compile(
        r'^\s*import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]|'
        r'^\s*import\s+[\'"]([^\'"]+)[\'"]'
    )
    for i, line in enumerate(collapsed_lines):
        m = pattern.match(line)
        if m:
            p = m.group(1) or m.group(2)
            imports.append((i + 1, p, get_import_type(p), line))
    return imports, collapsed_lines


def check_import_order(content, file_path):
    if not is_ts_file(file_path):
        return None
    imports, lines = extract_imports(content)
    if len(imports) < 2:
        return [], []
    blocking = []
    warnings = []
    prev_type = -1
    prev_line = 0
    type_names = ['node built-ins', 'external packages', 'internal aliases', 'relative imports']
    for ln, path, itype, _ in imports:
        if itype < prev_type:
            blocking.append(
                f"line {ln}: '{path}' ({type_names[itype]}) should come before {type_names[prev_type]}"
            )
        if prev_type != -1 and itype != prev_type:
            between = lines[prev_line:ln - 1]
            has_blank = any(l.strip() == '' for l in between)
            if not has_blank:
                warnings.append(f"line {ln}: missing blank line before import group change")
        prev_type = itype
        prev_line = ln
    return blocking, warnings


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
    result = check_import_order(content, fp)
    if not result:
        sys.exit(0)
    blocking, warnings = result
    if blocking:
        print("import organisation issues:", file=sys.stderr)
        for issue in blocking[:5]:
            print(f"  - {issue}", file=sys.stderr)
        if len(blocking) > 5:
            print(f"  ... and {len(blocking) - 5} more", file=sys.stderr)
        print("\nimports should be ordered: node built-ins -> external -> internal aliases -> relative", file=sys.stderr)
        sys.exit(2)
    if warnings:
        print("import organisation notes:", file=sys.stderr)
        for w in warnings[:3]:
            print(f"  - {w}", file=sys.stderr)
    sys.exit(0)


if __name__ == '__main__':
    main()
