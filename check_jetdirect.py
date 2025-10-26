#!/usr/bin/env python3
"""
Nagios Plugin for SNMP Printer Monitoring
Checks printer status, consumable levels, and page counts via SNMP.

Converted from bash script version 1.1 by Yoann LAMY
Python version 2.0 - Enhanced error handling and performance data

Dependencies:
- pysnmp

Copyright (C) 2024 - GPLv2 License
"""

import argparse
import sys
import re
from typing import Optional, Tuple

# Nagios exit codes
NAGIOS_OK = 0
NAGIOS_WARNING = 1
NAGIOS_CRITICAL = 2
NAGIOS_UNKNOWN = 3

import subprocess
import shlex

class PrinterSNMP:
    """SNMP client for printer monitoring using system snmpget/snmpwalk commands"""
    
    # OID definitions (Printer-MIB)
    OID_NAME = "1.3.6.1.2.1.43.11.1.1.6.1"
    OID_TOTAL = "1.3.6.1.2.1.43.11.1.1.8.1"
    OID_STATUS = "1.3.6.1.2.1.43.11.1.1.9.1"
    
    OID_NAME_OTHER = "1.3.6.1.2.1.43.12.1.1.4.1"
    OID_TOTAL_OTHER = "1.3.6.1.2.1.43.10.2.1.9.1"
    OID_STATUS_OTHER = "1.3.6.1.2.1.43.10.2.1.10.1"
    
    OID_DEVICE_PRINTER = "1.3.6.1.2.1.25.3.2.1.3.1"
    OID_SERIAL_NUMBER = "1.3.6.1.2.1.43.5.1.1.17.1"
    OID_PAGE = "1.3.6.1.2.1.43.10.2.1.4.1.1"
    
    def __init__(self, hostname: str, community: str = "public"):
        self.hostname = hostname
        self.community = community
        # Check if snmpget is available
        try:
            subprocess.run(['snmpget', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise ImportError("snmpget command not found. Install net-snmp-utils package.")
    
    def snmp_get(self, oid: str, verbose: bool = False) -> Optional[str]:
        """Perform SNMP GET operation using system snmpget command"""
        try:
            if verbose:
                print(f"DEBUG: SNMP GET {oid} from {self.hostname}")
            
            cmd = [
                'snmpget', '-t', '2', '-r', '2', '-v', '1', 
                '-c', self.community, '-Ovq', self.hostname, oid
            ]
            
            if verbose:
                print(f"DEBUG: Running command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                if verbose:
                    print(f"DEBUG: SNMP GET failed with return code {result.returncode}")
                    print(f"DEBUG: stderr: {result.stderr}")
                return None
            
            value = result.stdout.strip()
            if verbose:
                print(f"DEBUG: SNMP Response: {value}")
            
            return value if value else None
            
        except subprocess.TimeoutExpired:
            if verbose:
                print("DEBUG: SNMP GET timeout")
            return None
        except Exception as e:
            if verbose:
                print(f"DEBUG: SNMP GET Exception: {e}")
            return None
    
    def snmp_walk(self, oid: str, verbose: bool = False) -> dict:
        """Perform SNMP WALK operation using system snmpwalk command"""
        results = {}
        try:
            if verbose:
                print(f"DEBUG: SNMP WALK {oid} from {self.hostname}")
            
            cmd = [
                'snmpwalk', '-t', '2', '-r', '2', '-v', '1',
                '-c', self.community, self.hostname, oid
            ]
            
            if verbose:
                print(f"DEBUG: Running command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                if verbose:
                    print(f"DEBUG: SNMP WALK failed with return code {result.returncode}")
                    print(f"DEBUG: stderr: {result.stderr}")
                return results
            
            # Parse snmpwalk output
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                # Parse format: OID = TYPE: VALUE
                parts = line.split(' = ')
                if len(parts) >= 2:
                    oid_part = parts[0].strip()
                    value_part = ' = '.join(parts[1:]).strip()
                    
                    # Remove type prefix (e.g., "STRING: ")
                    if ':' in value_part:
                        value_part = value_part.split(':', 1)[1].strip()
                    
                    # Extract index from OID
                    if '.' in oid_part:
                        index = oid_part.split('.')[-1]
                        results[index] = value_part
                        if verbose:
                            print(f"DEBUG: SNMP Walk Response: {oid_part} = {value_part}")
            
        except subprocess.TimeoutExpired:
            if verbose:
                print("DEBUG: SNMP WALK timeout")
        except Exception as e:
            if verbose:
                print(f"DEBUG: SNMP WALK Exception: {e}")
        
        return results


def find_consumable_id(printer: PrinterSNMP, consumable: str, verbose: bool = False) -> Optional[str]:
    """Find the SNMP index for a specific consumable"""
    consumable_patterns = {
        "black": ["black", "cartouche", "toner"],
        "cyan": ["cyan"],
        "magenta": ["magenta"],
        "yellow": ["yellow"],
        "drum": ["drum"]
    }
    
    patterns = consumable_patterns.get(consumable, [consumable])
    
    # First try primary OID
    names = printer.snmp_walk(printer.OID_NAME, verbose=verbose)
    for index, name in names.items():
        for pattern in patterns:
            if pattern.lower() in name.lower():
                return index
    
    # Try alternative OID
    names = printer.snmp_walk(printer.OID_NAME_OTHER, verbose=verbose)
    for index, name in names.items():
        for pattern in patterns:
            if pattern.lower() in name.lower():
                return index
    
    return None


def check_consumable(args) -> Tuple[int, str]:
    """Check printer consumable levels"""
    printer = PrinterSNMP(args.hostname, args.community)
    verbose = getattr(args, 'verbose', False)
    
    consumable_id = find_consumable_id(printer, args.consumable, verbose=verbose)
    if not consumable_id:
        return NAGIOS_UNKNOWN, f"UNKNOWN - Consumable '{args.consumable}' not found"
    
    # Get consumable data
    total = printer.snmp_get(f"{printer.OID_TOTAL}.{consumable_id}")
    status = printer.snmp_get(f"{printer.OID_STATUS}.{consumable_id}")
    
    # Try alternative OIDs if primary ones fail or return negative values
    if not total or not status or (total and total.startswith('-')):
        total = printer.snmp_get(f"{printer.OID_TOTAL_OTHER}.{consumable_id}")
        status = printer.snmp_get(f"{printer.OID_STATUS_OTHER}.{consumable_id}")
    
    if not total or not status:
        return NAGIOS_UNKNOWN, "UNKNOWN - Printer is waiting or consumable data unavailable"
    
    try:
        total_int = int(total)
        status_int = int(status)
        
        if total_int <= 0:
            return NAGIOS_UNKNOWN, "UNKNOWN - Invalid consumable total value"
        
        # Calculate percentages
        remaining_percent = (status_int * 100) // total_int
        used_percent = 100 - remaining_percent
        
        # Determine state based on thresholds
        exit_code = NAGIOS_OK
        if args.critical > 0 and used_percent > args.critical:
            exit_code = NAGIOS_CRITICAL
        elif args.warning > 0 and used_percent > args.warning:
            exit_code = NAGIOS_WARNING
        
        # Format consumable name for display
        consumable_names = {
            "black": "black cartridge",
            "cyan": "cyan cartridge", 
            "magenta": "magenta cartridge",
            "yellow": "yellow cartridge",
            "drum": "printing device"
        }
        consumable_display = consumable_names.get(args.consumable, "consumable")
        
        # Build status message
        if exit_code == NAGIOS_OK:
            status_prefix = "OK"
        elif exit_code == NAGIOS_WARNING:
            status_prefix = "WARNING"
        else:
            status_prefix = "CRITICAL"
        
        message = f"{status_prefix} - Utilisation of the {consumable_display}: {used_percent}%"
        message += f" | cons_used={used_percent};{args.warning};{args.critical};0;100"
        
        return exit_code, message
        
    except (ValueError, ZeroDivisionError):
        return NAGIOS_UNKNOWN, "UNKNOWN - Invalid consumable data received"


def check_pages(args) -> Tuple[int, str]:
    """Check printer page count"""
    printer = PrinterSNMP(args.hostname, args.community)
    verbose = getattr(args, 'verbose', False)
    
    # Try multiple OIDs for page count
    page_oids = [
        printer.OID_PAGE,                           # Standard page counter
        "1.3.6.1.2.1.43.10.2.1.4.1.1",            # Same as above (explicit)
        "1.3.6.1.4.1.11.2.3.9.4.2.1.1.16.1.1",    # HP-specific page counter
        "1.3.6.1.4.1.11.2.3.9.4.2.1.4.1.2.6.0",   # HP total pages
        "1.3.6.1.2.1.43.10.2.1.5.1.1",            # Media path page count
    ]
    
    for oid in page_oids:
        if verbose:
            print(f"DEBUG: Trying page count OID: {oid}")
        pages = printer.snmp_get(oid, verbose=verbose)
        if pages and pages != "No Such Object available on this agent at this OID":
            try:
                page_count = int(pages)
                if page_count >= 0:  # Valid page count
                    message = f"OK - Page count: {page_count} | pages={page_count};0;0;0"
                    return NAGIOS_OK, message
            except ValueError:
                if verbose:
                    print(f"DEBUG: Invalid page count data from OID {oid}: {pages}")
                continue
    
    return NAGIOS_UNKNOWN, "UNKNOWN - Unable to retrieve page count from any known OID"


def check_info(args) -> Tuple[int, str]:
    """Get printer information"""
    printer = PrinterSNMP(args.hostname, args.community)
    verbose = getattr(args, 'verbose', False)
    
    device = printer.snmp_get(printer.OID_DEVICE_PRINTER, verbose=verbose)
    serial = printer.snmp_get(printer.OID_SERIAL_NUMBER, verbose=verbose)
    
    if not device:
        return NAGIOS_UNKNOWN, "UNKNOWN - Unable to retrieve printer information"
    
    # Clean up serial number (remove quotes if present)
    if serial:
        serial = serial.strip('"\'')
    else:
        serial = "Unknown"
    
    message = f"OK - Info: {device} ({serial})"
    return NAGIOS_OK, message


def main():
    parser = argparse.ArgumentParser(
        description="Nagios plugin to check printer status via SNMP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -H 192.168.1.100 -C public -t consumable -o black -w 85 -c 90
  %(prog)s -H printer.domain.com -t page
  %(prog)s -H 10.0.0.50 -t info
  %(prog)s -H 192.168.1.100 -t consumable -o cyan -w 80 -c 95
        """
    )
    
    parser.add_argument(
        "-H", "--hostname",
        required=True,
        help="Name or IP address of printer (required)"
    )
    
    parser.add_argument(
        "-C", "--community",
        default="public",
        help="SNMP community name (default: public)"
    )
    
    parser.add_argument(
        "-t", "--type",
        choices=["consumable", "consummable", "page", "info"],
        default="page",
        help="Check type: consumable, page, or info (default: page)"
    )
    
    parser.add_argument(
        "-o", "--consumable",
        choices=["black", "cyan", "magenta", "yellow", "drum"],
        default="black",
        help="Consumable type for -t consumable (default: black)"
    )
    
    parser.add_argument(
        "-w", "--warning",
        type=int,
        default=0,
        help="Warning threshold for consumable usage percentage (default: 0)"
    )
    
    parser.add_argument(
        "-c", "--critical", 
        type=int,
        default=0,
        help="Critical threshold for consumable usage percentage (default: 0)"
    )
    
    parser.add_argument(
        "-V", "--version",
        action="version",
        version="%(prog)s 2.0 - Python version of check_snmp_printer"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose debugging output"
    )
    
    args = parser.parse_args()
    
    # Validate thresholds
    if args.warning < 0 or args.critical < 0:
        print("UNKNOWN - Thresholds must be positive integers")
        sys.exit(NAGIOS_UNKNOWN)
    
    if args.warning > 0 and args.critical > 0 and args.warning >= args.critical:
        print("UNKNOWN - Warning threshold must be less than critical threshold")
        sys.exit(NAGIOS_UNKNOWN)
    
    # Normalize type (handle legacy typo)
    check_type = "consumable" if args.type == "consummable" else args.type
    
    # Perform the appropriate check
    try:
        if check_type == "consumable":
            exit_code, message = check_consumable(args)
        elif check_type == "page":
            exit_code, message = check_pages(args)
        elif check_type == "info":
            exit_code, message = check_info(args)
        else:
            print("UNKNOWN - Invalid check type")
            sys.exit(NAGIOS_UNKNOWN)
        
        print(message)
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"UNKNOWN - Plugin error: {str(e)}")
        sys.exit(NAGIOS_UNKNOWN)


if __name__ == "__main__":
    main()