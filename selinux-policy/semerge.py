#!/usr/bin/env python3
# /// script
# requires-python = ">=3.6"
# dependencies = []
# ///
"""
SELinux Policy Merger

This script accepts SELinux rules via STDIN (e.g. the output of audit2allow)
and also by referencing an existing policy file. It merges the two to produce
an output file which contains the contents of both sources.
"""

import sys
import argparse
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Set


class SELinuxPolicyMerger:
    """Merge and deduplicate SELinux policy files"""
    
    def __init__(self):
        self.types: Set[str] = set()
        self.classes: Dict[str, Set[str]] = defaultdict(set)
        self.allows: Dict[str, Dict[str, Dict[str, Set[str]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(set))
        )
    
    def parse_module_header(self, lines: List[str]) -> Optional[Tuple[str, str]]:
        """Extract module name and version from policy header"""
        if not lines:
            return None
        
        # Search for module declaration in the file (usually near the top)
        for line in lines[:50]:  # Check first 50 lines
            line = line.strip()
            # module resnet-nrpe 1.45;
            match = re.match(r'^module\s+([\w\-_]+)\s+([\d\.]+);$', line)
            if match:
                return match.group(1), match.group(2)
        return None
    
    def parse_policy(self, lines: List[str]):
        """Parse SELinux policy lines and add to internal data structures"""
        for line in lines:
            line = line.strip()
            
            # type rpm_exec_t;
            match = re.match(r'^\s*type\s+(\w+);?$', line)
            if match:
                self.types.add(match.group(1))
                continue
            
            # class file rename;
            match = re.match(r'^\s*class\s+(\w+)\s+(\w+);$', line)
            if match:
                self.classes[match.group(1)].add(match.group(2))
                continue
            
            # class file { rename execute setattr read };
            match = re.match(r'^\s*class\s+(\w+)\s+\{\s*([\s\w]+)\s*\};$', line)
            if match:
                class_name = match.group(1)
                perms = match.group(2).split()
                self.classes[class_name].update(perms)
                continue
            
            # allow nagios_services_plugin_t dhcpd_state_t:file read;
            match = re.match(r'^\s*allow\s+(\w+)\s+(\w+):(\w+)\s+(\w+);$', line)
            if match:
                allow, obj, cls, perm = match.groups()
                self.allows[allow][obj][cls].add(perm)
                continue
            
            # allow nagios_services_plugin_t dhcpd_state_t:file { read getattr };
            match = re.match(r'^\s*allow\s+(\w+)\s+(\w+):(\w+)\s+\{\s*([\s\w]+)\s*\};$', line)
            if match:
                allow, obj, cls, perms_str = match.groups()
                perms = perms_str.split()
                self.allows[allow][obj][cls].update(perms)
                continue
    
    def increment_version(self, version: str) -> str:
        """Increment the last component of a version number"""
        parts = version.split('.')
        parts[-1] = str(int(parts[-1]) + 1)
        return '.'.join(parts)
    
    def format_output(self, module_name: str, module_version: str) -> str:
        """Format the merged policy as a string"""
        output = []
        
        # Header
        output.append(f"module {module_name} {module_version};\n\n")
        output.append("require {\n")
        
        # Types
        for type_name in sorted(self.types):
            output.append(f"\ttype {type_name};\n")
        
        if self.types:
            output.append("\n")
        
        # Classes
        for class_name in sorted(self.classes.keys()):
            perms = sorted(self.classes[class_name])
            output.append(f"\tclass {class_name} {{ {' '.join(perms)} }};\n")
        
        output.append("}\n")
        
        # Allow rules
        for allow in sorted(self.allows.keys()):
            output.append(f"\n#============= {allow} ==============\n")
            for obj in sorted(self.allows[allow].keys()):
                for cls in sorted(self.allows[allow][obj].keys()):
                    perms = sorted(self.allows[allow][obj][cls])
                    output.append(f"allow {allow} {obj}:{cls} {{ {' '.join(perms)} }};\n")
        
        return ''.join(output)


def main():
    parser = argparse.ArgumentParser(
        description='Merge SELinux policy files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script accepts SELinux rulesets via STDIN (e.g. the output of audit2allow) and by
reading an existing policy file. It merges, deduplicates and sorts the two inputs to
produce an output policy which contains the contents of both sources.

EXAMPLES:

  semerge.py -i existingpolicy.te -o existingpolicy.te
      Deduplicates and alphabetises existingpolicy.te

  cat existingpolicy.te | semerge.py > existingpolicy.te
      Equivalent to the above

  cat /var/log/audit/audit.log | audit2allow | semerge.py -i existingpolicy.te -o newpolicy.te
      Create newpolicy.te which merges new rules from audit2allow into existingpolicy.te
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        help='Read an existing SELinux policy file'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Write the resulting merged policy to a file (defaults to STDOUT)'
    )
    
    parser.add_argument(
        '-v', '--version',
        help='Override the module version number (defaults to incrementing input version)'
    )
    
    parser.add_argument(
        '-n', '--name',
        help='Override the module name (defaults to input file module name)'
    )
    
    args = parser.parse_args()
    
    merger = SELinuxPolicyMerger()
    
    stdin_name = None
    stdin_version = None
    file_name = None
    file_version = None
    
    # Read from STDIN if available
    if not sys.stdin.isatty():
        stdin_lines = [line.rstrip('\n') for line in sys.stdin]
        if len(stdin_lines) > 1:
            header = merger.parse_module_header(stdin_lines)
            if header:
                stdin_name, stdin_version = header
            merger.parse_policy(stdin_lines)
    
    # Read from input file if specified
    if args.input:
        try:
            with open(args.input, 'r') as f:
                file_lines = [line.rstrip('\n') for line in f]
            
            if len(file_lines) > 1:
                header = merger.parse_module_header(file_lines)
                if header:
                    file_name, file_version = header
                merger.parse_policy(file_lines)
        except IOError as e:
            print(f"Can't open {args.input} for reading: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Require at least one input source
    if not args.input and sys.stdin.isatty():
        print("Must provide input via -i flag or STDIN", file=sys.stderr)
        sys.exit(1)
    
    # Determine module name (priority: arg > file > stdin)
    module_name = args.name or file_name or stdin_name
    if not module_name:
        print("Must set module name", file=sys.stderr)
        sys.exit(1)
    
    # Determine module version (priority: arg > increment file > increment stdin)
    if args.version:
        module_version = args.version
    elif file_version:
        module_version = merger.increment_version(file_version)
    elif stdin_version:
        module_version = merger.increment_version(stdin_version)
    else:
        print("Must set module version", file=sys.stderr)
        sys.exit(1)
    
    # Generate output
    output = merger.format_output(module_name, module_version)
    
    # Write to file or stdout
    if args.output:
        try:
            with open(args.output, 'w') as f:
                f.write(output)
        except IOError as e:
            print(f"Can't open {args.output} for writing: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output, end='')


if __name__ == '__main__':
    main()
