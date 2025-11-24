#!/usr/bin/env python3
"""
Motivation for this tool:
Ubuntu / Rocky provide different versions of nagios monitoring tooling
I didn't know that before and want to use the same tools on both systems, obviously.

I simply compiled them from source on Rocky and was confused why I get different results on ubuntu
So I will simply compile them on all systems and deploy them via the parsed config and kickstart import

Parse nagios-plugins source code to extract command-line options
and generate Icinga2 CheckCommand definitions.
"""

import re
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class PluginOption:
    def __init__(self, short: str = None, long: str = None, 
                 has_arg: str = None, description: str = ""):
        self.short = short
        self.long = long
        self.has_arg = has_arg  # 'no_argument', 'required_argument', 'optional_argument'
        self.description = description.strip()
        
    def __repr__(self):
        return f"Option(-{self.short}, --{self.long}, {self.has_arg})"

class PluginParser:
    def __init__(self, source_file: Path, plugin_dir: str = None, command_prefix: str = None):
        self.source_file = source_file
        self.plugin_name = source_file.stem  # check_apt
        self.plugin_dir = plugin_dir  # Optional static path prefix
        self.command_prefix = command_prefix  # Optional command name prefix
        self.options: List[PluginOption] = []
        self.content = ""
        
    def parse(self) -> bool:
        """Parse the source file and extract options."""
        try:
            with open(self.source_file, 'r', encoding='utf-8', errors='ignore') as f:
                self.content = f.read()
        except Exception as e:
            print(f"Error reading {self.source_file}: {e}")
            return False
            
        # Determine file type and use appropriate parser
        if self.source_file.suffix == '.c':
            return self.parse_c_file()
        elif self.source_file.suffix == '.pl':
            return self.parse_perl_file()
        elif self.source_file.suffix in ['.py', '.sh']:
            return self.parse_script_file()
        else:
            return False
    
    def parse_c_file(self) -> bool:
        """Parse C source file for getopt_long options."""
        # Find the longopts struct array
        longopts_match = re.search(
            r'static\s+struct\s+option\s+longopts\[\s*\]\s*=\s*\{(.*?)\{0,\s*0,\s*0,\s*0\}',
            self.content, re.DOTALL
        )
        
        if not longopts_match:
            print(f"  No longopts found in {self.plugin_name}")
            return False
        
        longopts_content = longopts_match.group(1)
        
        # Parse each option line: {"name", required_argument, 0, 'x'}
        option_pattern = r'\{"([^"]+)",\s*(no_argument|required_argument|optional_argument),\s*0,\s*\'(.)\'\}'
        
        for match in re.finditer(option_pattern, longopts_content):
            long_name = match.group(1)
            has_arg = match.group(2)
            short_name = match.group(3)
            
            # Skip help and version (handled by Icinga2 already)
            if long_name in ['help', 'version']:
                continue
                
            opt = PluginOption(short=short_name, long=long_name, has_arg=has_arg)
            self.options.append(opt)
        
        # Try to extract descriptions from print_help()
        self.extract_c_descriptions()
        
        return len(self.options) > 0
    
    def extract_c_descriptions(self):
        """Extract option descriptions from print_help() function."""
        # Find print_help function
        help_match = re.search(r'void\s+print_help.*?\{(.*?)^}', self.content, re.DOTALL | re.MULTILINE)
        if not help_match:
            return
            
        help_content = help_match.group(1)
        
        # Look for patterns like: printf (" %s\n", "-U, --upgrade=OPTS");
        # followed by description lines
        for opt in self.options:
            # Build search pattern for this option
            patterns = []
            if opt.short and opt.long:
                patterns.append(rf'-{opt.short},?\s+--{opt.long}')
            elif opt.long:
                patterns.append(rf'--{opt.long}')
            elif opt.short:
                patterns.append(rf'-{opt.short}[,\s]')
                
            for pattern in patterns:
                # Find the option line and grab next few description lines
                opt_match = re.search(
                    rf'printf.*?{pattern}.*?\n((?:\s*printf\s*\([^;]+;\s*\n){{1,5}})',
                    help_content, re.IGNORECASE
                )
                
                if opt_match:
                    desc_lines = opt_match.group(1)
                    # Extract strings from printf calls
                    desc_parts = re.findall(r'printf\s*\([^"]*"([^"]+)"', desc_lines)
                    description = ' '.join(desc_parts).strip()
                    # Clean up
                    description = re.sub(r'%s', '', description)
                    description = re.sub(r'\s+', ' ', description)
                    opt.description = description
                    break
    
    def parse_perl_file(self) -> bool:
        """Parse Perl script for Getopt::Long options."""
        # Look for GetOptions() call - both formats:
        # GetOptions(...);
        # GetOptions
        #     ("opt" => ...);
        getopts_match = re.search(
            r'GetOptions\s*\((.*?)\)',
            self.content, re.DOTALL
        )
        
        if not getopts_match:
            print(f"  No GetOptions found in {self.plugin_name}")
            return False
        
        getopts_content = getopts_match.group(1)
        
        # Parse option specs in format: "V" => \$opt_V, "version" => \$opt_V,
        # or "w=s" => \$opt_w, "warning=s" => \$opt_w,
        # Pattern matches: "option_spec" => \$variable
        option_pattern = r'"([^"]+)"\s*=>\s*\\?\$(\w+)'
        
        # Track options by variable name to group short/long forms
        opt_by_var = {}
        
        for match in re.finditer(option_pattern, getopts_content):
            opt_spec = match.group(1)
            var_name = match.group(2)
            
            # Parse the option spec
            # Determine argument type from suffix
            has_arg = 'no_argument'
            clean_spec = opt_spec
            if '=' in opt_spec:
                has_arg = 'required_argument'
                clean_spec = opt_spec.split('=')[0]
            elif ':' in opt_spec:
                has_arg = 'optional_argument'
                clean_spec = opt_spec.split(':')[0]
            elif '!' in opt_spec:
                has_arg = 'no_argument'
                clean_spec = opt_spec.replace('!', '')
            
            # Skip help and version
            if clean_spec in ['h', 'V', 'help', 'version', 'usage']:
                continue
            
            # Group by variable name
            if var_name not in opt_by_var:
                opt_by_var[var_name] = PluginOption(has_arg=has_arg)
            
            # Add short or long option
            if len(clean_spec) == 1:
                opt_by_var[var_name].short = clean_spec
            else:
                opt_by_var[var_name].long = clean_spec
        
        # Convert to list
        self.options = list(opt_by_var.values())
        
        return len(self.options) > 0
    
    def parse_script_file(self) -> bool:
        """Parse shell or Python scripts (basic implementation)."""
        # This is more complex and varies widely, return False for now
        print(f"  Script parsing not yet implemented for {self.plugin_name}")
        return False
    
    def generate_icinga_command(self) -> str:
        """Generate Icinga2 CheckCommand definition."""
        lines = []
        # Apply command prefix if specified
        command_name = f"{self.command_prefix}_{self.plugin_name}" if self.command_prefix else self.plugin_name
        lines.append(f'object CheckCommand "{command_name}" {{')
        
        # Use static path if provided, otherwise use PluginDir variable
        if self.plugin_dir:
            lines.append(f'  command = [ "{self.plugin_dir}/{self.plugin_name}" ]')
        else:
            lines.append(f'  command = [ PluginDir + "/{self.plugin_name}" ]')
        
        lines.append('')
        lines.append('  arguments = {')
        
        hostname_var = None
        
        for opt in self.options:
            # Use long name if available, otherwise short
            opt_name = opt.long if opt.long else opt.short
            if not opt_name:
                continue
                
            var_name = opt_name.replace('-', '_')
            
            # Track hostname parameter for later vars assignment
            if opt_name in ['hostname', 'host', 'Hostname'] and opt.has_arg in ['required_argument', 'optional_argument']:
                if not hostname_var:  # Use first hostname parameter found
                    hostname_var = f'{self.plugin_name}_{var_name}'
            
            # Build argument block - prefer long form
            if opt.long:
                arg_key = f'--{opt.long}'
            else:
                arg_key = f'-{opt.short}'
            
            lines.append(f'    "{arg_key}" = {{')
            
            if opt.has_arg in ['required_argument', 'optional_argument']:
                lines.append(f'      value = "${self.plugin_name}_{var_name}$"')
                if opt.description:
                    lines.append(f'      description = "{opt.description[:80]}"')
            else:
                # Boolean flag
                lines.append(f'      set_if = "${self.plugin_name}_{var_name}$"')
                if opt.description:
                    lines.append(f'      description = "{opt.description[:80]}"')
            
            lines.append('    }')
        
        lines.append('  }')
        
        # Add default vars assignment for hostname parameter
        if hostname_var:
            lines.append('')
            lines.append(f'  vars.{hostname_var} = "$address$"')
        
        lines.append('}')
        lines.append('')
        
        return '\n'.join(lines)

def update_progress(filename: str, status: str, notes: str = "", progress_file: Optional[Path] = None):
    """Update parseprogress.txt with parsing status."""
    if not progress_file:
        return
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Create progress file if it doesn't exist
    if not progress_file.exists():
        progress_file.write_text(f"{filename}|{status}|{timestamp}|{notes}\n")
        return
    
    # Read all lines
    lines = progress_file.read_text().split('\n')
    
    # Update the matching line
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(filename + '|'):
            lines[i] = f"{filename}|{status}|{timestamp}|{notes}"
            updated = True
            break
    
    # Add new line if not found
    if not updated:
        lines.append(f"{filename}|{status}|{timestamp}|{notes}")
    
    # Write back
    progress_file.write_text('\n'.join(lines))

def main():
    parser = argparse.ArgumentParser(
        description='Parse Nagios plugins source code and generate Icinga2 CheckCommand definitions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -p /path/to/nagios-plugins -o commands.conf
  %(prog)s --plugins-dir ./plugins --output icinga-commands.conf --track-progress
  %(prog)s -p /opt/nagios-plugins/libexec -o /etc/icinga2/conf.d/commands-custom.conf
  %(prog)s -p ./plugins -o commands.conf --plugin-path /opt/monitoring-nagios-git-2.4.12/libexec
  %(prog)s -p ./plugins -o commands-git.conf --command-prefix git --plugin-path /opt/monitoring-git/libexec
        """
    )
    
    parser.add_argument(
        '-p', '--plugins-dir',
        required=True,
        type=Path,
        help='Path to nagios-plugins source directory containing check_*.c and check_*.pl files'
    )
    
    parser.add_argument(
        '-o', '--output',
        required=True,
        type=Path,
        help='Output file path for generated Icinga2 CheckCommand definitions'
    )
    
    parser.add_argument(
        '--track-progress',
        action='store_true',
        help='Enable progress tracking (creates parseprogress.txt in script directory)'
    )
    
    parser.add_argument(
        '--plugin-path',
        type=str,
        help='Static plugin path prefix (e.g., /opt/monitoring-nagios-git-2.4.12/libexec). If not specified, uses PluginDir variable.'
    )
    
    parser.add_argument(
        '--command-prefix',
        type=str,
        help='Prefix for CheckCommand object names (e.g., "git" produces "git_check_http"). Useful for distinguishing plugin versions.'
    )
    
    args = parser.parse_args()
    
    plugins_dir = args.plugins_dir.resolve()
    output_file = args.output.resolve()
    
    # Setup progress file if requested
    progress_file = None
    if args.track_progress:
        script_dir = Path(__file__).parent
        progress_file = script_dir / 'parseprogress.txt'
        print(f"Progress tracking enabled: {progress_file}")
    
    # Validate plugins directory
    if not plugins_dir.exists():
        print(f"Error: Plugins directory does not exist: {plugins_dir}")
        sys.exit(1)
    
    if not plugins_dir.is_dir():
        print(f"Error: Plugins path is not a directory: {plugins_dir}")
        sys.exit(1)
    
    # Find all check files (C and Perl)
    c_files = list(plugins_dir.rglob('check_*.c'))
    pl_files = list(plugins_dir.rglob('check_*.pl'))
    
    # Exclude test files
    c_files = [f for f in c_files if '/t/' not in str(f) and '/tests/' not in str(f)]
    pl_files = [f for f in pl_files if '/t/' not in str(f) and '/tests/' not in str(f)]
    
    all_files = sorted(c_files + pl_files, key=lambda x: x.name)
    
    print(f"Plugins directory: {plugins_dir}")
    print(f"Output file: {output_file}")
    if args.plugin_path:
        print(f"Plugin path: {args.plugin_path} (static)")
    else:
        print(f"Plugin path: PluginDir (variable)")
    if args.command_prefix:
        print(f"Command prefix: {args.command_prefix}")
    print(f"Found {len(c_files)} C plugin files and {len(pl_files)} Perl plugin files")
    
    all_commands = []
    all_commands.append('# Nagios Plugins 2.4.12 - Icinga2 CheckCommand Definitions')
    all_commands.append('# Auto-generated by parse_nagios_plugins.py')
    all_commands.append(f'# Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    all_commands.append(f'# Source: {plugins_dir}')
    all_commands.append('')
    
    processed = 0
    for plugin_file in all_files:
        print(f"\nParsing {plugin_file.name}...")
        update_progress(plugin_file.name, 'in-progress', progress_file=progress_file)
        
        parser_instance = PluginParser(plugin_file, plugin_dir=args.plugin_path, command_prefix=args.command_prefix)
        if parser_instance.parse():
            print(f"  Found {len(parser_instance.options)} options")
            for opt in parser_instance.options:
                print(f"    {opt}")
            
            command_def = parser_instance.generate_icinga_command()
            all_commands.append(command_def)
            
            update_progress(plugin_file.name, 'completed', f'{len(parser_instance.options)} options', progress_file=progress_file)
            processed += 1
        else:
            update_progress(plugin_file.name, 'error', 'Failed to parse', progress_file=progress_file)
    
    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text('\n'.join(all_commands))
    
    print(f"\n✓ Successfully parsed {processed}/{len(all_files)} plugins")
    print(f"✓ Generated: {output_file}")

if __name__ == '__main__':
    main()
