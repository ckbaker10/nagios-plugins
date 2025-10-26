#!/usr/bin/env python3
"""
Nagios Plugin for Goss Validation Monitoring
Runs goss validate and reports test results.

Goss is a YAML-based serverspec alternative tool for validating server configurations.

Dependencies:
- goss binary in PATH

Copyright (C) 2024 - GPLv3 License
"""

import argparse
import sys
import subprocess
import re
import json
from typing import Tuple, Dict, Any
from pathlib import Path

# Nagios exit codes
NAGIOS_OK = 0
NAGIOS_WARNING = 1
NAGIOS_CRITICAL = 2
NAGIOS_UNKNOWN = 3


class GossValidator:
    """Goss validation runner and parser"""
    
    def __init__(self, goss_file: str = None, vars_file: str = None, package_manager: str = None):
        self.goss_file = goss_file
        self.vars_file = vars_file
        self.package_manager = package_manager
        
        # Check if goss is available
        try:
            result = subprocess.run(['goss', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise ImportError("goss command not found. Install goss from https://github.com/goss-org/goss")
    
    def run_validation(self, output_format: str = "tap", verbose: bool = False) -> subprocess.CompletedProcess:
        """Run goss validate command"""
        cmd = ['goss']
        
        # Add global options first
        if self.goss_file:
            cmd.extend(['-g', self.goss_file])
        
        if self.vars_file:
            cmd.extend(['--vars', self.vars_file])
        
        if self.package_manager:
            cmd.extend(['--package', self.package_manager])
        
        # Add validate subcommand
        cmd.append('validate')
        
        # Add validate options
        if output_format:
            cmd.extend(['-f', output_format])
        
        if verbose:
            print(f"DEBUG: Running command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if verbose:
                print(f"DEBUG: Command exit code: {result.returncode}")
                print(f"DEBUG: stdout: {result.stdout}")
                if result.stderr:
                    print(f"DEBUG: stderr: {result.stderr}")
            return result
        except subprocess.TimeoutExpired:
            raise Exception("Goss validation timed out after 60 seconds")
    
    def parse_tap_output(self, output: str) -> Dict[str, Any]:
        """Parse TAP (Test Anything Protocol) output"""
        lines = output.strip().split('\n')
        results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'failures': [],
            'version': None
        }
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # TAP version
            if line.startswith('TAP version'):
                results['version'] = line
            
            # Test plan
            elif line.startswith('1..'):
                try:
                    results['total'] = int(line.split('..')[1])
                except (ValueError, IndexError):
                    pass
            
            # Test results
            elif line.startswith('ok ') or line.startswith('not ok '):
                if line.startswith('ok '):
                    if '# SKIP' in line:
                        results['skipped'] += 1
                    else:
                        results['passed'] += 1
                else:  # not ok
                    results['failed'] += 1
                    # Extract test name/description
                    test_desc = line.replace('not ok ', '').split('#')[0].strip()
                    results['failures'].append(test_desc)
        
        return results
    
    def parse_console_output(self, output: str) -> Dict[str, Any]:
        """Parse console output format (like the provided example)"""
        lines = output.strip().split('\n')
        results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'failures': [],
            'details': []
        }
        
        in_failures = False
        current_failure = None
        
        for line in lines:
            line = line.strip()
            
            # Look for failure section
            if line == "Failures/Skipped:":
                in_failures = True
                continue
            
            # Parse summary line
            if line.startswith("Count:"):
                # Format: "Count: 41, Failed: 6, Skipped: 4"
                parts = line.split(', ')
                for part in parts:
                    if ':' in part:
                        key, value = part.split(':', 1)
                        key = key.strip().lower()
                        try:
                            value = int(value.strip())
                            if key == 'count':
                                results['total'] = value
                            elif key == 'failed':
                                results['failed'] = value
                            elif key == 'skipped':
                                results['skipped'] = value
                        except ValueError:
                            pass
                
                # Calculate passed
                results['passed'] = results['total'] - results['failed'] - results['skipped']
                break
            
            # Parse failure details
            if in_failures and line:
                if line.endswith(':'):
                    # New failure/skip entry
                    current_failure = line[:-1]
                elif line.startswith('Expected') or line.startswith('to equal'):
                    # Failure detail
                    if current_failure:
                        results['failures'].append(current_failure)
                        results['details'].append(f"{current_failure}: {line}")
                        current_failure = None
        
        return results


def check_goss_validation(args) -> Tuple[int, str]:
    """Check Goss validation and return Nagios result"""
    try:
        if args.verbose:
            print(f"DEBUG: Goss file: {args.goss_file or 'default (goss.yaml)'}")
            print(f"DEBUG: Vars file: {args.vars_file or 'none'}")
            print(f"DEBUG: Package manager: {args.package_manager or 'auto-detect'}")
        
        # Initialize validator
        validator = GossValidator(
            goss_file=args.goss_file,
            vars_file=args.vars_file,
            package_manager=args.package_manager
        )
        
        # Run validation
        result = validator.run_validation(output_format=args.output_format, verbose=args.verbose)
        
        # Parse results based on output format
        if args.output_format == 'tap':
            parsed = validator.parse_tap_output(result.stdout)
        else:
            # Default rspecish format (similar to console)
            parsed = validator.parse_console_output(result.stdout)
        
        if args.verbose:
            print(f"DEBUG: Parsed results: {parsed}")
        
        # Determine exit code - any failure is CRITICAL in infrastructure testing
        total = parsed.get('total', 0)
        passed = parsed.get('passed', 0)
        failed = parsed.get('failed', 0)
        skipped = parsed.get('skipped', 0)
        
        if failed > 0:
            exit_code = NAGIOS_CRITICAL
            status_prefix = "CRITICAL"
            if failed == 1:
                status_parts = [f"1 test failed"]
            else:
                status_parts = [f"{failed} tests failed"]
        elif total == 0:
            exit_code = NAGIOS_UNKNOWN
            status_prefix = "UNKNOWN"
            status_parts = ["No tests found"]
        else:
            exit_code = NAGIOS_OK
            status_prefix = "OK"
            status_parts = [f"All {passed} tests passed"]
        
        # Add summary
        summary_parts = []
        if passed > 0:
            summary_parts.append(f"{passed} passed")
        if failed > 0:
            summary_parts.append(f"{failed} failed")
        if skipped > 0:
            summary_parts.append(f"{skipped} skipped")
        
        if not status_parts:
            status_parts = [f"Total: {total}"]
        
        status_message = f"{status_prefix} - Goss validation: {' - '.join(status_parts)}"
        
        if summary_parts:
            status_message += f" ({', '.join(summary_parts)})"
        
        # Add performance data
        fail_percentage = (failed / total * 100) if total > 0 else 0
        perf_data = [
            f"total={total}",
            f"passed={passed}",
            f"failed={failed}",
            f"skipped={skipped}",
            f"fail_percent={fail_percentage:.1f}%"
        ]
        
        status_message += f" | {' '.join(perf_data)}"
        
        # Add failure details if requested and not too many
        if args.show_failures and failed > 0 and failed <= 5:
            failures = parsed.get('failures', [])[:3]  # Limit to first 3
            if failures:
                failure_list = ', '.join(failures)
                status_message += f" - Failed: {failure_list}"
        
        return exit_code, status_message
        
    except Exception as e:
        error_msg = f"UNKNOWN - Goss validation error: {str(e)}"
        if args.verbose:
            print(f"DEBUG: Exception occurred: {type(e).__name__}")
            print(f"DEBUG: Exception message: {str(e)}")
            import traceback
            traceback.print_exc()
        return NAGIOS_UNKNOWN, error_msg


def main():
    parser = argparse.ArgumentParser(
        description="Nagios plugin to monitor Goss validation results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s -g /etc/goss/server.yaml
  %(prog)s -g custom.yaml --vars vars.yaml --show-failures
  %(prog)s -f tap --allow-skipped
  %(prog)s -g /etc/goss/web.yaml --vars /etc/goss/web-vars.yaml
        """
    )
    
    parser.add_argument(
        "-g", "--goss-file",
        help="Path to goss file (default: goss.yaml)"
    )
    
    parser.add_argument(
        "--vars",
        dest="vars_file",
        help="Path to variables file"
    )
    
    parser.add_argument(
        "--package",
        dest="package_manager",
        choices=["apk", "deb", "pacman", "rpm"],
        help="Package manager to use for package tests"
    )
    
    parser.add_argument(
        "-f", "--format",
        dest="output_format",
        choices=["rspecish", "tap", "json", "junit", "nagios", "documentation", "structured"],
        default="rspecish",
        help="Output format (default: rspecish)"
    )
    
    parser.add_argument(
        "--allow-skipped",
        action="store_true",
        help="Don't treat skipped tests as failures"
    )
    
    parser.add_argument(
        "--show-failures",
        action="store_true",
        help="Include failure details in output (limited to 3 failures)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output for debugging"
    )
    
    parser.add_argument(
        "-V", "--version",
        action="version",
        version="%(prog)s 1.0 - Goss validation monitoring for Nagios"
    )
    
    args = parser.parse_args()
    
    # No threshold validation needed - any failure is critical
    
    # Perform the check
    exit_code, message = check_goss_validation(args)
    print(message)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()