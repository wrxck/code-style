#!/usr/bin/env python3
"""
Claude Code hook to enforce import organisation.
Imports should be grouped and ordered:
1. Node built-ins (fs, path, etc.)
2. External packages (react, etc.)
3. Internal aliases (@/, ~/)
4. Relative imports (../, ./)

Groups should be separated by blank lines.
"""

import json
import re
import sys
from pathlib import Path

TS_EXTENSIONS = {'.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs'}

# node built-in modules
NODE_BUILTINS = {
    'assert', 'buffer', 'child_process', 'cluster', 'console', 'constants',
    'crypto', 'dgram', 'dns', 'domain', 'events', 'fs', 'http', 'https',
    'module', 'net', 'os', 'path', 'process', 'punycode', 'querystring',
    'readline', 'repl', 'stream', 'string_decoder', 'timers', 'tls',
    'tty', 'url', 'util', 'v8', 'vm', 'zlib', 'worker_threads', 'perf_hooks',
    'async_hooks', 'inspector', 'trace_events', 'wasi',
    # node: prefix versions
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


def is_ts_file(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in TS_EXTENSIONS


def get_import_type(import_path: str) -> int:
    """
    classify import into groups:
    0 = node built-in
    1 = external package
    2 = internal alias (@/, ~/, #/)
    3 = relative import
    """
    # strip quotes
    path = import_path.strip('\'"')

    # check for node built-ins
    base_module = path.split('/')[0]
    if base_module in NODE_BUILTINS or path.startswith('node:'):
        return 0

    # check for relative imports
    if path.startswith('.'):
        return 3

    # check for internal aliases
    if path.startswith('@/') or path.startswith('~/') or path.startswith('#/'):
        return 2

    # check for scoped packages (@org/package) - these are external
    if path.startswith('@') and '/' in path:
        return 1

    # everything else is external
    return 1


def extract_imports(content: str) -> list[tuple[int, str, int]]:
    """extract imports with line numbers and types"""
    imports = []
    lines = content.split('\n')

    import_pattern = re.compile(
        r'^import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]|'
        r'^import\s+[\'"]([^\'"]+)[\'"]'
    )

    for line_num, line in enumerate(lines, 1):
        match = import_pattern.match(line.strip())
        if match:
            import_path = match.group(1) or match.group(2)
            import_type = get_import_type(import_path)
            imports.append((line_num, import_path, import_type))

    return imports


def check_import_order(content: str, file_path: str) -> list[str]:
    """check if imports are properly ordered and grouped"""
    if not is_ts_file(file_path):
        return []

    imports = extract_imports(content)
    if len(imports) < 2:
        return []

    issues = []
    lines = content.split('\n')

    # check ordering within groups and between groups
    prev_type = -1
    prev_line = 0

    for line_num, import_path, import_type in imports:
        # check if types are out of order
        if import_type < prev_type:
            type_names = ['node built-ins', 'external packages', 'internal aliases', 'relative imports']
            issues.append(
                f"line {line_num}: '{import_path}' ({type_names[import_type]}) "
                f"should come before {type_names[prev_type]}"
            )

        # check for missing blank line between groups
        if prev_type != -1 and import_type != prev_type:
            # there should be a blank line between groups
            lines_between = lines[prev_line:line_num - 1]
            has_blank = any(line.strip() == '' for line in lines_between)
            if not has_blank:
                issues.append(
                    f"line {line_num}: missing blank line before import group change"
                )

        prev_type = import_type
        prev_line = line_num

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

    issues = check_import_order(content, file_path)

    if issues:
        print("import organisation issues:", file=sys.stderr)
        for issue in issues[:5]:
            print(f"  • {issue}", file=sys.stderr)
        if len(issues) > 5:
            print(f"  ... and {len(issues) - 5} more", file=sys.stderr)
        print("\nimports should be ordered: node built-ins → external → internal aliases → relative", file=sys.stderr)
        print("separate groups with blank lines", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
