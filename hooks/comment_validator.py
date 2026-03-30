#!/usr/bin/env python3
"""
Claude Code hook to validate code comments:
- lowercase only (no capital letters)
- only when truly needed
- british english spelling
"""

import json
import re
import sys
from pathlib import Path

# common american -> british spelling replacements
BRITISH_SPELLINGS = {
    'color': 'colour',
    'colors': 'colours',
    'behavior': 'behaviour',
    'behaviors': 'behaviours',
    'favor': 'favour',
    'favors': 'favours',
    'favorite': 'favourite',
    'favorites': 'favourites',
    'honor': 'honour',
    'honors': 'honours',
    'humor': 'humour',
    'labor': 'labour',
    'labors': 'labours',
    'neighbor': 'neighbour',
    'neighbors': 'neighbours',
    'rumor': 'rumour',
    'rumors': 'rumours',
    'vapor': 'vapour',
    'vigor': 'vigour',
    'initialize': 'initialise',
    'initializes': 'initialises',
    'initialized': 'initialised',
    'initializing': 'initialising',
    'initialization': 'initialisation',
    'organize': 'organise',
    'organizes': 'organises',
    'organized': 'organised',
    'organizing': 'organising',
    'organization': 'organisation',
    'recognize': 'recognise',
    'recognizes': 'recognises',
    'recognized': 'recognised',
    'recognizing': 'recognising',
    'synchronize': 'synchronise',
    'synchronizes': 'synchronises',
    'synchronized': 'synchronised',
    'synchronizing': 'synchronising',
    'optimize': 'optimise',
    'optimizes': 'optimises',
    'optimized': 'optimised',
    'optimizing': 'optimising',
    'optimization': 'optimisation',
    'utilize': 'utilise',
    'utilizes': 'utilises',
    'utilized': 'utilised',
    'utilizing': 'utilising',
    'utilization': 'utilisation',
    'customize': 'customise',
    'customizes': 'customises',
    'customized': 'customised',
    'customizing': 'customising',
    'customization': 'customisation',
    'analyze': 'analyse',
    'analyzes': 'analyses',
    'analyzed': 'analysed',
    'analyzing': 'analysing',
    'center': 'centre',
    'centers': 'centres',
    'centered': 'centred',
    'centering': 'centring',
    'meter': 'metre',
    'meters': 'metres',
    'liter': 'litre',
    'liters': 'litres',
    'fiber': 'fibre',
    'fibers': 'fibres',
    'theater': 'theatre',
    'theaters': 'theatres',
    'catalog': 'catalogue',
    'catalogs': 'catalogues',
    'dialog': 'dialogue',
    'dialogs': 'dialogues',
    'program': 'programme',
    'programs': 'programmes',
    'defense': 'defence',
    'offense': 'offence',
    'license': 'licence',
    'practice': 'practise',
    'gray': 'grey',
    'grays': 'greys',
    'canceled': 'cancelled',
    'canceling': 'cancelling',
    'traveled': 'travelled',
    'traveling': 'travelling',
    'traveler': 'traveller',
    'travelers': 'travellers',
    'modeling': 'modelling',
    'modeled': 'modelled',
    'labeled': 'labelled',
    'labeling': 'labelling',
}

# file extensions and their comment patterns
COMMENT_PATTERNS = {
    # single-line comment patterns by extension
    '.py': [r'#\s*(.*)'],
    '.js': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.ts': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.jsx': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.tsx': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.java': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.c': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.cpp': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.h': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.hpp': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.cs': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.go': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.rs': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.swift': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.kt': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.scala': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.rb': [r'#\s*(.*)'],
    '.sh': [r'#\s*(.*)'],
    '.bash': [r'#\s*(.*)'],
    '.zsh': [r'#\s*(.*)'],
    '.pl': [r'#\s*(.*)'],
    '.php': [r'//\s*(.*)', r'#\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.lua': [r'--\s*(.*)'],
    '.sql': [r'--\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.r': [r'#\s*(.*)'],
    '.R': [r'#\s*(.*)'],
    '.yaml': [r'#\s*(.*)'],
    '.yml': [r'#\s*(.*)'],
    '.toml': [r'#\s*(.*)'],
    '.ini': [r'[;#]\s*(.*)'],
    '.css': [r'/\*\s*(.*?)\s*\*/'],
    '.scss': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.less': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
    '.html': [r'<!--\s*(.*?)\s*-->'],
    '.xml': [r'<!--\s*(.*?)\s*-->'],
    '.vue': [r'<!--\s*(.*?)\s*-->'],
    '.svelte': [r'<!--\s*(.*?)\s*-->', r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
}

# words/phrases that suggest unnecessary comments
UNNECESSARY_PATTERNS = [
    r'^todo:?\s*$',  # empty todos
    r'^fixme:?\s*$',  # empty fixmes
    r'^hack:?\s*$',  # empty hacks
    r'^note:?\s*$',  # empty notes
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
    r'^constructor$',
    r'^destructor$',
    r'^getter$',
    r'^setter$',
    r'^default\s+(value|case)$',
]


def get_file_extension(file_path: str) -> str:
    """get the file extension from a path"""
    return Path(file_path).suffix.lower()


def extract_comments(content: str, extension: str) -> list[tuple[int, str]]:
    """extract comments from code content, returns list of (line_number, comment_text)"""
    if extension not in COMMENT_PATTERNS:
        return []

    comments = []
    patterns = COMMENT_PATTERNS[extension]
    lines = content.split('\n')

    for line_num, line in enumerate(lines, 1):
        for pattern in patterns:
            matches = re.finditer(pattern, line)
            for match in matches:
                comment_text = match.group(1).strip() if match.groups() else match.group(0).strip()
                if comment_text:
                    comments.append((line_num, comment_text))

    return comments


def check_lowercase(comment: str) -> list[str]:
    """check if comment contains uppercase letters (excluding acronyms and code references)"""
    issues = []

    # skip if it looks like a licence/copyright header
    if any(word in comment.lower() for word in ['copyright', 'license', 'licence', 'author', 'spdx']):
        return issues

    # skip urls
    if re.search(r'https?://', comment):
        return issues

    # skip if it's likely a code reference (contains camelCase or snake_case identifiers)
    code_ref_pattern = r'`[^`]+`|[a-z]+[A-Z][a-zA-Z]*|[A-Z]{2,}'
    cleaned = re.sub(code_ref_pattern, '', comment)

    # check for uppercase in remaining text
    words = cleaned.split()
    for word in words:
        # skip if word is all caps (likely acronym) or starts sentence after period
        if word.isupper() and len(word) <= 5:
            continue
        # check if word starts with uppercase
        if word and word[0].isupper():
            issues.append(f"uppercase found: '{word}' should be lowercase")
            break  # only report first instance

    return issues


def check_british_spelling(comment: str) -> list[str]:
    """check for american spellings that should be british"""
    issues = []
    comment_lower = comment.lower()

    for american, british in BRITISH_SPELLINGS.items():
        # use word boundaries to avoid partial matches
        if re.search(rf'\b{american}\b', comment_lower):
            issues.append(f"use british spelling: '{american}' -> '{british}'")

    return issues


def check_unnecessary(comment: str) -> list[str]:
    """check if comment appears to be unnecessary"""
    issues = []
    comment_lower = comment.lower().strip()

    # skip if comment is substantial (more than 5 words)
    if len(comment_lower.split()) > 5:
        return issues

    for pattern in UNNECESSARY_PATTERNS:
        if re.search(pattern, comment_lower):
            issues.append(f"potentially unnecessary comment: '{comment}' - comments should explain why, not what")
            break

    return issues


def validate_comments(file_path: str, content: str) -> list[str]:
    """validate all comments in the given content"""
    extension = get_file_extension(file_path)
    if not extension:
        return []

    comments = extract_comments(content, extension)
    all_issues = []

    for line_num, comment in comments:
        issues = []
        issues.extend(check_lowercase(comment))
        issues.extend(check_british_spelling(comment))
        issues.extend(check_unnecessary(comment))

        for issue in issues:
            all_issues.append(f"line {line_num}: {issue}")

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

    issues = validate_comments(file_path, new_content)

    if issues:
        print("comment style issues detected:", file=sys.stderr)
        for issue in issues[:5]:  # limit to 5 issues to avoid spam
            print(f"  • {issue}", file=sys.stderr)
        if len(issues) > 5:
            print(f"  ... and {len(issues) - 5} more issues", file=sys.stderr)
        print("\nreminder: comments should be lowercase, use british spelling, and only added when necessary", file=sys.stderr)
        sys.exit(2)  # block the tool call

    sys.exit(0)


if __name__ == '__main__':
    main()
