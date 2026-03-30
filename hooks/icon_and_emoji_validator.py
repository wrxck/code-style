#!/usr/bin/env python3
"""
Claude Code hook to enforce:
- prefer Huge Icons for icons in typescript projects
- never use emojis in code
"""

import json
import re
import sys
from pathlib import Path

# typescript/javascript file extensions
TS_EXTENSIONS = {'.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs'}

# icon library imports to flag (prefer Huge Icons instead)
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

# emoji unicode ranges
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # geometric shapes extended
    "\U0001F800-\U0001F8FF"  # supplemental arrows-c
    "\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
    "\U00002702-\U000027B0"  # dingbats
    "\U000024C2-\U0001F251"  # enclosed characters
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002300-\U000023FF"  # misc technical (includes some emoji)
    "\U00002600-\U000026FF"  # misc symbols
    "\U00002700-\U000027BF"  # dingbats
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0001F000-\U0001F02F"  # mahjong tiles
    "\U0001F0A0-\U0001F0FF"  # playing cards
    "]+",
    flags=re.UNICODE
)

# common emoji shortcodes in strings
EMOJI_SHORTCODES = [
    r':\)',
    r':\(',
    r':D',
    r';-?\)',
    r'<3',
    r':heart:',
    r':smile:',
    r':thumbsup:',
    r':fire:',
    r':rocket:',
    r':star:',
    r':check:',
    r':x:',
    r':warning:',
]


def get_file_extension(file_path: str) -> str:
    """get the file extension from a path"""
    return Path(file_path).suffix.lower()


def is_typescript_file(file_path: str) -> bool:
    """check if the file is a typescript/javascript file"""
    return get_file_extension(file_path) in TS_EXTENSIONS


def check_icon_libraries(content: str, file_path: str) -> list[str]:
    """check for non-Huge Icons library imports"""
    if not is_typescript_file(file_path):
        return []

    issues = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, 1):
        for pattern, lib_name in ICON_LIBRARIES:
            if re.search(pattern, line):
                issues.append(
                    f"line {line_num}: prefer Huge Icons instead of {lib_name} - "
                    f"use 'hugeicons-react' package"
                )

    return issues


def check_emojis(content: str, file_path: str) -> list[str]:
    """check for emoji usage in code"""
    issues = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, 1):
        # skip comments for emoji shortcode detection (those are handled by comment validator)
        is_comment = (
            line.strip().startswith('//') or
            line.strip().startswith('#') or
            line.strip().startswith('/*') or
            line.strip().startswith('*')
        )

        # check for unicode emojis
        emoji_matches = EMOJI_PATTERN.findall(line)
        if emoji_matches:
            emojis_found = ''.join(emoji_matches)
            issues.append(
                f"line {line_num}: emoji detected '{emojis_found}' - "
                f"do not use emojis in code"
            )

        # check for emoji shortcodes in strings (not in comments)
        if not is_comment:
            # look for shortcodes inside strings
            string_pattern = r'["\'][^"\']*["\']'
            strings = re.findall(string_pattern, line)
            for string in strings:
                for shortcode in EMOJI_SHORTCODES:
                    if re.search(shortcode, string):
                        issues.append(
                            f"line {line_num}: emoji shortcode detected in string - "
                            f"do not use emojis in code"
                        )
                        break

    return issues


def validate_content(file_path: str, content: str) -> list[str]:
    """validate content for icon library usage and emojis"""
    all_issues = []

    all_issues.extend(check_icon_libraries(content, file_path))
    all_issues.extend(check_emojis(content, file_path))

    return all_issues


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    if not file_path:
        sys.exit(0)

    # get the content - for Edit it's new_string, for Write it's content
    new_content = tool_input.get('new_string', '') or tool_input.get('content', '')

    if not new_content:
        sys.exit(0)

    issues = validate_content(file_path, new_content)

    if issues:
        print("icon/emoji issues detected:", file=sys.stderr)
        for issue in issues[:5]:
            print(f"  • {issue}", file=sys.stderr)
        if len(issues) > 5:
            print(f"  ... and {len(issues) - 5} more issues", file=sys.stderr)
        print("\nreminder: use Huge Icons (hugeicons-react) for icons, never use emojis in code", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
