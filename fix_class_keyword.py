#!/usr/bin/env python3
"""
Fix the 'self.class' reserved keyword issue in auto-generated Kaitai parsers.
This script replaces 'self.class' with 'self.class_' to make it valid Python.
"""

import re
from pathlib import Path

def fix_class_keyword(file_path):
    """Replace self.class with self.class_ in the given file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace self.class with self.class_ (but not self.class_name, etc.)
    # Use word boundary to match exactly 'class' not 'class_something'
    fixed_content = re.sub(r'\bself\.class\b', 'self.class_', content)
    
    # Also fix debug references ['class'] -> ['class_']
    fixed_content = re.sub(r"\['class'\]", "['class_']", fixed_content)
    
    # And fix SEQ_FIELDS if it contains "class"
    fixed_content = re.sub(r'SEQ_FIELDS = \[(.*)"class"(.*)\]', r'SEQ_FIELDS = [\1"class_"\2]', fixed_content)
    
    if content != fixed_content:
        with open(file_path, 'w') as f:
            f.write(fixed_content)
        print(f"Fixed: {file_path}")
        return True
    return False

if __name__ == "__main__":
    parser_dir = Path(__file__).parent / "polyfile" / "kaitai" / "parsers"
    
    if parser_dir.exists():
        # Fix openpgp_message.py
        openpgp_file = parser_dir / "openpgp_message.py"
        if openpgp_file.exists():
            if fix_class_keyword(openpgp_file):
                print("Successfully fixed the 'class' keyword issue!")
            else:
                print("No changes needed for 'class' keyword.")
        else:
            print(f"Error: {openpgp_file} not found.")
    else:
        print(f"Error: Parser directory {parser_dir} not found.")
