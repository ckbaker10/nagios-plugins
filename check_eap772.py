#!/usr/bin/env python3
"""
Nagios Plugin for TP-Link Omada EAP772 Access Point Monitoring
Monitors system status, interfaces, and wireless performance via SNMPv3.

Dependencies:
- pysnmp

Copyright (C) 2024 - GPLv3 License
"""

import argparse
import sys
import subprocess
from typing import Tuple, Dict, List

# Nagios exit codes
NAGIOS_OK = 0
NAGIOS_WARNING = 1
NAGIOS_CRITICAL = 2
NAGIOS_UNKNOWN = 3


class EAP772Monitor:
    """TP-Link Omada EAP772 SNMP monitor"""
    
    # Standard SNMP OIDs
    OID_SYSTEM_DESCR = ".1.3.6.1.2.1.1.1.0"
    OID_SYSTEM_UPTIME = ".1.3.6.1.2.1.1.3.0"
    OID_SYSTEM_NAME = ".1.3.6.1.2.1.1.5.0"
    
    # Interface OIDs
    OID_IF_DESCR = ".1.3.6.1.2.1.2.2.1.2"
    OID_IF_OPER_STATUS = ".1.3.6.1.2.1.2.2.1.8"
    OID_IF_IN_OCTETS = ".1.3.6.1.2.1.2.2.1.10"
    OID_IF_OUT_OCTETS = ".1.3.6.1.2.1.2.2.1.16"
    OID_IF_IN_ERRORS = ".1.3.6.1.2.1.2.2.1.14"
    OID_IF_OUT_ERRORS = ".1.3.6.1.2.1.2.2.1.20"
    
    def __init__(self, host: str, username: str, auth_password: str, verbose: bool = False):
        self.host = host
        self.username = username
        self.auth_password = auth_password
        self.verbose = verbose
        
    def _snmp_get(self, oid: str) -> str:
        """Execute snmpget command"""
        cmd = [
            'snmpget',
            '-v3',
            '-l', 'authNoPriv',
            '-u', self.username,
            '-a', 'MD5',
            '-A', self.auth_password,
            self.host,
            oid
        ]
        
        if self.verbose:
            print(f"DEBUG: Running: {' '.join(cmd[:8])} [password hidden] {cmd[9:]}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                if self.verbose:
                    print(f"DEBUG: snmpget failed: {result.stderr}")
                return None
            
            # Parse output: "OID = TYPE: VALUE"
            output = result.stdout.strip()
            if '=' in output and ':' in output:
                value = output.split(':', 1)[1].strip()
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                return value
            return None
            
        except subprocess.TimeoutExpired:
            if self.verbose:
                print("DEBUG: snmpget timeout")
            return None
        except Exception as e:
            if self.verbose:
                print(f"DEBUG: snmpget exception: {e}")
            return None
    
    def _snmp_walk(self, oid: str) -> Dict[str, str]:
        """Execute snmpwalk command and return OID:value dict"""
        cmd = [
            'snmpwalk',
            '-v3',
            '-l', 'authNoPriv',
            '-u', self.username,
            '-a', 'MD5',
            '-A', self.auth_password,
            self.host,
            oid
        ]
        
        if self.verbose:
            print(f"DEBUG: Running snmpwalk for OID: {oid}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode != 0:
                if self.verbose:
                    print(f"DEBUG: snmpwalk failed: {result.stderr}")
                return {}
            
            # Parse output
            data = {}
            for line in result.stdout.strip().split('\n'):
                if '=' in line and ':' in line:
                    oid_part, value_part = line.split('=', 1)
                    value = value_part.split(':', 1)[1].strip() if ':' in value_part else value_part.strip()
                    # Extract index from OID
                    oid_clean = oid_part.strip()
                    if oid_clean.startswith('iso'):
                        oid_clean = '.' + oid_clean[3:]
                    # Get last part as index
                    index = oid_clean.split('.')[-1]
                    data[index] = value.strip('"')
            
            return data
            
        except subprocess.TimeoutExpired:
            if self.verbose:
                print("DEBUG: snmpwalk timeout")
            return {}
        except Exception as e:
            if self.verbose:
                print(f"DEBUG: snmpwalk exception: {e}")
            return {}
    
    def get_system_info(self) -> Dict:
        """Get basic system information"""
        return {
            'description': self._snmp_get(self.OID_SYSTEM_DESCR),
            'uptime': self._snmp_get(self.OID_SYSTEM_UPTIME),
            'name': self._snmp_get(self.OID_SYSTEM_NAME)
        }
    
    def get_interfaces(self, interface_filter: List[str] = None) -> List[Dict]:
        """Get interface information
        
        Args:
            interface_filter: List of interface names to monitor. If None, monitors default set.
        """
        if_names = self._snmp_walk(self.OID_IF_DESCR)
        if_status = self._snmp_walk(self.OID_IF_OPER_STATUS)
        if_in_octets = self._snmp_walk(self.OID_IF_IN_OCTETS)
        if_out_octets = self._snmp_walk(self.OID_IF_OUT_OCTETS)
        if_in_errors = self._snmp_walk(self.OID_IF_IN_ERRORS)
        if_out_errors = self._snmp_walk(self.OID_IF_OUT_ERRORS)
        
        # Default interfaces if no filter specified
        if interface_filter is None:
            interface_filter = ['eth0', 'br0', 'wifi0', 'wifi1', 'wifi2', 'ath0', 'ath10', 'ath20']
        
        interfaces = []
        for idx in if_names:
            name = if_names.get(idx, 'unknown')
            # Only monitor specified interfaces
            if name in interface_filter:
                status_val = if_status.get(idx, '2')
                interfaces.append({
                    'name': name,
                    'status': 'up' if status_val == '1' else 'down',
                    'in_octets': int(if_in_octets.get(idx, 0)),
                    'out_octets': int(if_out_octets.get(idx, 0)),
                    'in_errors': int(if_in_errors.get(idx, 0)),
                    'out_errors': int(if_out_errors.get(idx, 0))
                })
        
        return interfaces


def check_eap772(args) -> Tuple[int, str]:
    """Check EAP772 status and return Nagios result"""
    try:
        monitor = EAP772Monitor(
            host=args.host,
            username=args.username,
            auth_password=args.auth_password,
            verbose=args.verbose
        )
        
        # Get system info
        sys_info = monitor.get_system_info()
        
        if not sys_info['description']:
            return NAGIOS_UNKNOWN, "UNKNOWN - Cannot connect to device via SNMP"
        
        if args.verbose:
            print(f"DEBUG: System info: {sys_info}")
        
        # Parse interface filter if provided
        interface_filter = None
        if args.interfaces:
            interface_filter = [iface.strip() for iface in args.interfaces.split(',')]
            if args.verbose:
                print(f"DEBUG: Monitoring interfaces: {interface_filter}")
        
        # Get interface information
        interfaces = monitor.get_interfaces(interface_filter)
        
        if not interfaces:
            return NAGIOS_WARNING, "WARNING - No interfaces found"
        
        # Check interface status
        down_interfaces = [iface['name'] for iface in interfaces if iface['status'] == 'down']
        up_interfaces = [iface['name'] for iface in interfaces if iface['status'] == 'up']
        
        # Check for errors (unless --ignore-errors is set)
        error_interfaces = []
        if not args.ignore_errors:
            for iface in interfaces:
                total_errors = iface['in_errors'] + iface['out_errors']
                if total_errors > args.error_threshold:
                    error_interfaces.append(f"{iface['name']}({total_errors})")
        
        # Determine status
        exit_code = NAGIOS_OK
        status_prefix = "OK"
        status_parts = []
        
        if down_interfaces:
            critical_down = [iface for iface in down_interfaces if iface in ['eth0', 'br0']]
            if critical_down:
                exit_code = NAGIOS_CRITICAL
                status_prefix = "CRITICAL"
                status_parts.append(f"Critical interfaces down: {', '.join(critical_down)}")
            elif len(down_interfaces) > 2:
                exit_code = NAGIOS_WARNING
                status_prefix = "WARNING"
                status_parts.append(f"{len(down_interfaces)} interfaces down")
        
        if error_interfaces and exit_code == NAGIOS_OK:
            exit_code = NAGIOS_WARNING
            status_prefix = "WARNING"
            status_parts.append(f"High errors: {', '.join(error_interfaces)}")
        
        if exit_code == NAGIOS_OK:
            status_parts.append(f"All {len(up_interfaces)} monitored interfaces operational")
        
        # Build message
        name = sys_info['name'] or 'EAP772'
        uptime_str = sys_info['uptime'].split(')', 1)[0].replace('(', '').strip() if sys_info['uptime'] else 'unknown'
        
        message = f"{status_prefix} - {name} - {' - '.join(status_parts)}"
        
        if args.show_interfaces:
            interface_details = []
            for iface in interfaces[:5]:  # Show up to 5 interfaces
                interface_details.append(f"{iface['name']}:{iface['status']}")
            if interface_details:
                message += f" [{', '.join(interface_details)}]"
        
        # Add performance data
        perf_data = []
        perf_data.append(f"interfaces_up={len(up_interfaces)}")
        perf_data.append(f"interfaces_down={len(down_interfaces)}")
        
        for iface in interfaces:
            safe_name = iface['name'].replace('-', '_').replace('.', '_')
            perf_data.append(f"{safe_name}_in={iface['in_octets']}c")
            perf_data.append(f"{safe_name}_out={iface['out_octets']}c")
            if iface['in_errors'] > 0 or iface['out_errors'] > 0:
                perf_data.append(f"{safe_name}_errors={iface['in_errors'] + iface['out_errors']}c")
        
        message += f" | {' '.join(perf_data)}"
        
        return exit_code, message
        
    except Exception as e:
        error_msg = f"UNKNOWN - Error checking EAP772: {str(e)}"
        if args.verbose:
            import traceback
            traceback.print_exc()
        return NAGIOS_UNKNOWN, error_msg


def main():
    parser = argparse.ArgumentParser(
        description="Nagios plugin to monitor TP-Link Omada EAP772 access points",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -H 10.10.10.231 -u monitoring -p password
  %(prog)s -H 10.10.10.231 -u monitoring -p password --show-interfaces
  %(prog)s -H 10.10.10.231 -u monitoring -p password --error-threshold 1000 -v
  %(prog)s -H 10.10.10.231 -u monitoring -p password --ignore-errors
  %(prog)s -H 10.10.10.231 -u monitoring -p password -i eth0,br0
        """
    )
    
    parser.add_argument(
        "-H", "--host",
        required=True,
        help="Hostname or IP address of the EAP772"
    )
    
    parser.add_argument(
        "-u", "--username",
        required=True,
        help="SNMPv3 username"
    )
    
    parser.add_argument(
        "-p", "--auth-password",
        required=True,
        help="SNMPv3 authentication password"
    )
    
    parser.add_argument(
        "--error-threshold",
        type=int,
        default=100,
        help="Error count threshold for warning (default: 100)"
    )
    
    parser.add_argument(
        "--ignore-errors",
        action="store_true",
        help="Ignore interface error counts in status determination"
    )
    
    parser.add_argument(
        "-i", "--interfaces",
        help="Comma-separated list of interfaces to monitor (e.g., 'eth0,br0'). If not specified, monitors default set."
    )
    
    parser.add_argument(
        "--show-interfaces",
        action="store_true",
        help="Show interface status in output"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output for debugging"
    )
    
    parser.add_argument(
        "-V", "--version",
        action="version",
        version="%(prog)s 1.0 - TP-Link Omada EAP772 monitoring for Nagios"
    )
    
    args = parser.parse_args()
    
    # Perform the check
    exit_code, message = check_eap772(args)
    print(message)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
