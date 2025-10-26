#!/usr/bin/env python3
"""
Nagios Plugin for Docker Compose Service Monitoring
Checks the status of services in a Docker Compose project.

Dependencies:
- docker-compose or docker compose command

Copyright (C) 2024 - GPLv3 License
"""

import argparse
import sys
import subprocess
import re
from typing import Tuple, Dict, List, Optional
from pathlib import Path

# Nagios exit codes
NAGIOS_OK = 0
NAGIOS_WARNING = 1
NAGIOS_CRITICAL = 2
NAGIOS_UNKNOWN = 3


class DockerComposeMonitor:
    """Docker Compose service monitor"""
    
    def __init__(self, project_name: str = None, compose_file: str = None, compose_dir: str = None):
        self.project_name = project_name
        self.compose_file = compose_file
        self.compose_dir = compose_dir
        self.docker_compose_cmd = self._detect_compose_command()
    
    def _detect_compose_command(self) -> List[str]:
        """Detect available docker-compose command"""
        # Try docker compose (newer syntax) first
        try:
            result = subprocess.run(['docker', 'compose', 'version'], 
                                  capture_output=True, check=True, timeout=5)
            return ['docker', 'compose']
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Try docker-compose (legacy)
        try:
            result = subprocess.run(['docker-compose', '--version'], 
                                  capture_output=True, check=True, timeout=5)
            return ['docker-compose']
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise ImportError("Neither 'docker compose' nor 'docker-compose' command found")
    
    def get_services_status(self, verbose: bool = False) -> Dict:
        """Get status of all services in the compose project"""
        cmd = self.docker_compose_cmd.copy()
        
        # Add project-specific options
        if self.project_name:
            cmd.extend(['-p', self.project_name])
        
        if self.compose_file:
            cmd.extend(['-f', self.compose_file])
        
        # Change to compose directory if specified
        original_cwd = None
        if self.compose_dir:
            original_cwd = Path.cwd()
            try:
                Path(self.compose_dir).resolve(strict=True)
            except (OSError, FileNotFoundError):
                raise Exception(f"Compose directory not found: {self.compose_dir}")
        
        cmd.extend(['ps', '--format', 'table'])
        
        if verbose:
            print(f"DEBUG: Running command: {' '.join(cmd)}")
            if self.compose_dir:
                print(f"DEBUG: Working directory: {self.compose_dir}")
        
        try:
            if self.compose_dir:
                import os
                os.chdir(self.compose_dir)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if verbose:
                print(f"DEBUG: Command exit code: {result.returncode}")
                print(f"DEBUG: stdout: {result.stdout}")
                if result.stderr:
                    print(f"DEBUG: stderr: {result.stderr}")
            
            if result.returncode != 0:
                raise Exception(f"Docker compose command failed: {result.stderr}")
            
            return self._parse_compose_output(result.stdout, verbose)
            
        except subprocess.TimeoutExpired:
            raise Exception("Docker compose command timed out")
        finally:
            if original_cwd:
                import os
                os.chdir(original_cwd)
    
    def _parse_compose_output(self, output: str, verbose: bool = False) -> Dict:
        """Parse docker-compose ps output"""
        lines = output.strip().split('\n')
        if len(lines) < 2:
            return {
                'services': [],
                'total': 0,
                'running': 0,
                'unhealthy': 0,
                'stopped': 0,
                'other': 0
            }
        
        services = []
        running_count = 0
        unhealthy_count = 0
        stopped_count = 0
        other_count = 0
        
        # Skip header line
        for line in lines[1:]:
            if not line.strip():
                continue
            
            # Use regex to parse table format more accurately
            # Match: NAME (spaces) IMAGE (spaces) COMMAND (spaces) SERVICE (spaces) CREATED (spaces) STATUS (spaces) PORTS
            
            # Split on multiple spaces to handle table columns better
            parts = re.split(r'\s{2,}', line.strip())
            if len(parts) < 6:
                # Fallback to regular split if regex doesn't work
                parts = line.split()
                if len(parts) < 6:
                    continue
            
            name = parts[0]
            
            # Extract service name from container name (format: project-service-number)
            service_match = re.match(r'^.*?-(.+?)-\d+$', name)
            if service_match:
                service = service_match.group(1)
            else:
                # Fallback: use the 4th column if available, otherwise extract from name
                if len(parts) > 3:
                    service = parts[3]
                else:
                    service = name.split('-')[1] if '-' in name else name
            
            # Status is typically in column 5 (0-indexed)
            if len(parts) >= 6:
                status_text = parts[5]
            else:
                # Find status in the line by looking for keywords
                status_match = re.search(r'(Up [^)]*(?:\([^)]*\))?|Exit(?:ed)? \d+|Restarting)', line)
                if status_match:
                    status_text = status_match.group(1)
                else:
                    status_text = "unknown"
            
            # Clean up status text - remove port mappings
            status_clean = re.sub(r'\s*\d+\.\d+\.\d+\.\d+:\d+->\d+/tcp.*$', '', status_text).strip()
            
            # Determine service state
            state = "unknown"
            status_lower = status_clean.lower()
            
            if "up" in status_lower:
                if "unhealthy" in status_lower:
                    state = "unhealthy"
                    unhealthy_count += 1
                else:
                    state = "running"
                    running_count += 1
            elif any(word in status_lower for word in ["exit", "exited"]):
                state = "stopped"
                stopped_count += 1
            elif "restarting" in status_lower:
                state = "restarting"
                other_count += 1
            else:
                state = "other"
                other_count += 1
            
            services.append({
                'name': name,
                'service': service,
                'status': status_clean,
                'state': state
            })
            
            if verbose:
                print(f"DEBUG: Parsed service - Name: {name}, Service: {service}, Status: {status_clean}, State: {state}")
        
        return {
            'services': services,
            'total': len(services),
            'running': running_count,
            'unhealthy': unhealthy_count,
            'stopped': stopped_count,
            'other': other_count
        }


def check_compose_status(args) -> Tuple[int, str]:
    """Check Docker Compose status and return Nagios result"""
    try:
        if args.verbose:
            print(f"DEBUG: Project name: {args.project_name or 'default'}")
            print(f"DEBUG: Compose file: {args.compose_file or 'default (docker-compose.yml)'}")
            print(f"DEBUG: Compose directory: {args.compose_dir or 'current directory'}")
        
        # Initialize monitor
        monitor = DockerComposeMonitor(
            project_name=args.project_name,
            compose_file=args.compose_file,
            compose_dir=args.compose_dir
        )
        
        # Get service status
        status_data = monitor.get_services_status(verbose=args.verbose)
        
        if args.verbose:
            print(f"DEBUG: Status data: {status_data}")
        
        # Analyze results
        total = status_data['total']
        running = status_data['running']
        unhealthy = status_data['unhealthy']
        stopped = status_data['stopped']
        other = status_data['other']
        
        # Determine exit code
        exit_code = NAGIOS_OK
        status_parts = []
        
        if total == 0:
            exit_code = NAGIOS_UNKNOWN
            status_prefix = "UNKNOWN"
            status_parts = ["No services found"]
        elif stopped > 0 or other > 0:
            exit_code = NAGIOS_CRITICAL
            status_prefix = "CRITICAL"
            if stopped > 0:
                status_parts.append(f"{stopped} stopped")
            if other > 0:
                status_parts.append(f"{other} in error state")
        elif unhealthy > 0:
            # Unhealthy services are critical by default, but can be configured as warning
            if args.unhealthy_warning:
                exit_code = NAGIOS_WARNING
                status_prefix = "WARNING"
            else:
                exit_code = NAGIOS_CRITICAL
                status_prefix = "CRITICAL"
            status_parts.append(f"{unhealthy} unhealthy")
        else:
            exit_code = NAGIOS_OK
            status_prefix = "OK"
            status_parts.append(f"All {running} services running")
        
        # Build summary
        summary_parts = []
        if running > 0:
            summary_parts.append(f"{running} running")
        if unhealthy > 0:
            summary_parts.append(f"{unhealthy} unhealthy")
        if stopped > 0:
            summary_parts.append(f"{stopped} stopped")
        if other > 0:
            summary_parts.append(f"{other} other")
        
        status_message = f"{status_prefix} - Docker Compose: {' - '.join(status_parts)}"
        
        if summary_parts:
            status_message += f" ({', '.join(summary_parts)})"
        
        # Add performance data
        perf_data = [
            f"total={total}",
            f"running={running}",
            f"unhealthy={unhealthy}",
            f"stopped={stopped}",
            f"other={other}"
        ]
        
        status_message += f" | {' '.join(perf_data)}"
        
        # Add service details if requested and there are issues
        if args.show_services and (exit_code != NAGIOS_OK or args.verbose):
            failed_services = []
            for service in status_data['services']:
                if service['state'] != 'running':
                    failed_services.append(f"{service['service']}:{service['state']}")
            
            if failed_services and len(failed_services) <= 5:  # Limit to 5 services
                status_message += f" - Issues: {', '.join(failed_services)}"
        
        return exit_code, status_message
        
    except Exception as e:
        error_msg = f"UNKNOWN - Docker Compose check error: {str(e)}"
        if args.verbose:
            print(f"DEBUG: Exception occurred: {type(e).__name__}")
            print(f"DEBUG: Exception message: {str(e)}")
            import traceback
            traceback.print_exc()
        return NAGIOS_UNKNOWN, error_msg


def main():
    parser = argparse.ArgumentParser(
        description="Nagios plugin to monitor Docker Compose services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s -p myproject
  %(prog)s -f /path/to/docker-compose.yml
  %(prog)s -d /opt/myapp --show-services
  %(prog)s -p icinga-playground --unhealthy-warning
        """
    )
    
    parser.add_argument(
        "-p", "--project",
        dest="project_name",
        help="Docker Compose project name"
    )
    
    parser.add_argument(
        "-f", "--file",
        dest="compose_file",
        help="Path to Docker Compose file"
    )
    
    parser.add_argument(
        "-d", "--directory",
        dest="compose_dir",
        help="Directory containing docker-compose.yml"
    )
    
    parser.add_argument(
        "--unhealthy-warning",
        action="store_true",
        help="Treat unhealthy services as WARNING instead of CRITICAL"
    )
    
    parser.add_argument(
        "--show-services",
        action="store_true",
        help="Include service details in output for failed services"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output for debugging"
    )
    
    parser.add_argument(
        "-V", "--version",
        action="version",
        version="%(prog)s 1.0 - Docker Compose monitoring for Nagios"
    )
    
    args = parser.parse_args()
    
    # Perform the check
    exit_code, message = check_compose_status(args)
    print(message)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()