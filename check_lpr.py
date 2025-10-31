#!/usr/bin/env python3
"""
Nagios Plugin for LPD/LPR Protocol Testing
Tests LPD (Line Printer Daemon) server status by sending a queue status request.

This plugin connects to an LPD server and queries the status of a print queue.
RFC 1179 requires the source port to be in the range 721-731 for LPD connections,
which requires root/elevated privileges.

Dependencies:
- None (uses standard library only)

Copyright (C) 2024 - GPLv3 License
Original C version: Copyright (c) 2002 Scott Lurndal

Fixed to actually work https://github.com/ckbaker10
"""

import argparse
import socket
import sys
import time
from typing import Tuple

# Nagios exit codes
NAGIOS_OK = 0
NAGIOS_WARNING = 1
NAGIOS_CRITICAL = 2
NAGIOS_UNKNOWN = 3

# LPD protocol constants
LPD_DEFAULT_PORT = 515
LPD_SOURCE_PORT_MIN = 721
LPD_SOURCE_PORT_MAX = 731
LPD_DEFAULT_SOURCE_PORT = 730
LPD_STATUS_COMMAND = 0x03  # Short form queue status


class LPDChecker:
    """LPD/LPR protocol checker"""
    
    def __init__(self, host: str, port: int = LPD_DEFAULT_PORT, 
                 source_port: int = LPD_DEFAULT_SOURCE_PORT,
                 queue: str = "pr2", timeout: int = 10, verbose: bool = False):
        self.host = host
        self.port = port
        self.source_port = source_port
        self.queue = queue
        self.timeout = timeout
        self.verbose = verbose
    
    def _validate_source_port(self) -> bool:
        """Validate that source port is in RFC 1179 required range"""
        if not (LPD_SOURCE_PORT_MIN <= self.source_port <= LPD_SOURCE_PORT_MAX):
            if self.verbose:
                print(f"WARNING: Source port {self.source_port} is outside "
                      f"RFC 1179 range ({LPD_SOURCE_PORT_MIN}-{LPD_SOURCE_PORT_MAX})")
                print("         Some LPD servers may reject the connection")
            return False
        return True
    
    def check_lpd(self) -> Tuple[int, str, float]:
        """
        Test LPD server by sending a queue status request
        
        Returns:
            Tuple of (exit_code, message, response_time)
        """
        start_time = time.time()
        sock = None
        
        try:
            # Validate source port
            self._validate_source_port()
            
            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            
            # Enable SO_REUSEADDR
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            if self.verbose:
                print(f"DEBUG: Binding to source port {self.source_port}")
            
            # Bind to privileged source port
            try:
                sock.bind(('', self.source_port))
            except PermissionError:
                return (NAGIOS_UNKNOWN, 
                       f"UNKNOWN - Permission denied binding to port {self.source_port}. "
                       f"Run as root or use sudo.",
                       0.0)
            except OSError as e:
                if e.errno == 98:  # Address already in use
                    return (NAGIOS_UNKNOWN,
                           f"UNKNOWN - Source port {self.source_port} already in use. "
                           f"Try a different port (721-731).",
                           0.0)
                return (NAGIOS_UNKNOWN,
                       f"UNKNOWN - Unable to bind to source port {self.source_port}: {e}",
                       0.0)
            
            if self.verbose:
                print(f"DEBUG: Connecting to {self.host}:{self.port}")
            
            # Connect to LPD server
            try:
                sock.connect((self.host, self.port))
            except socket.gaierror as e:
                return (NAGIOS_UNKNOWN,
                       f"UNKNOWN - Unable to resolve host '{self.host}': {e}",
                       0.0)
            except socket.timeout:
                return (NAGIOS_CRITICAL,
                       f"CRITICAL - Connection timeout to {self.host}:{self.port}",
                       time.time() - start_time)
            except ConnectionRefusedError:
                return (NAGIOS_CRITICAL,
                       f"CRITICAL - Connection refused by {self.host}:{self.port}",
                       time.time() - start_time)
            except OSError as e:
                return (NAGIOS_CRITICAL,
                       f"CRITICAL - Unable to connect to {self.host}:{self.port}: {e}",
                       time.time() - start_time)
            
            if self.verbose:
                print(f"DEBUG: Connected, sending queue status request for queue '{self.queue}'")
            
            # Send queue status inquiry
            # Format: <0x03><queue_name><newline>
            inquiry = bytes([LPD_STATUS_COMMAND]) + self.queue.encode('ascii') + b'\n'
            
            try:
                sock.sendall(inquiry)
            except socket.timeout:
                return (NAGIOS_CRITICAL,
                       f"CRITICAL - Send timeout to {self.host}:{self.port}",
                       time.time() - start_time)
            except OSError as e:
                return (NAGIOS_CRITICAL,
                       f"CRITICAL - Unable to send to {self.host}:{self.port}: {e}",
                       time.time() - start_time)
            
            if self.verbose:
                print(f"DEBUG: Waiting for response...")
            
            # Receive response
            try:
                response = sock.recv(256)
            except socket.timeout:
                return (NAGIOS_CRITICAL,
                       f"CRITICAL - Receive timeout from {self.host}:{self.port}",
                       time.time() - start_time)
            except OSError as e:
                return (NAGIOS_CRITICAL,
                       f"CRITICAL - Unable to receive from {self.host}:{self.port}: {e}",
                       time.time() - start_time)
            
            response_time = time.time() - start_time
            
            # Process response
            if not response:
                return (NAGIOS_CRITICAL,
                       f"CRITICAL - Empty response from {self.host}:{self.port}",
                       response_time)
            
            # Decode response, removing trailing newline
            try:
                response_text = response.decode('ascii', errors='replace').rstrip('\n')
                # LPRng returns command in first byte, replace with space if not printable
                if response_text and not response_text[0].isprintable():
                    response_text = ' ' + response_text[1:]
            except Exception:
                response_text = repr(response)
            
            if self.verbose:
                print(f"DEBUG: Response received: {response_text}")
            
            return (NAGIOS_OK,
                   f"OK - LPD: {response_text}",
                   response_time)
            
        except Exception as e:
            return (NAGIOS_UNKNOWN,
                   f"UNKNOWN - Unexpected error: {e}",
                   time.time() - start_time)
        
        finally:
            if sock:
                # Set linger to 0 (don't linger on close)
                try:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, 
                                   b'\x00\x00\x00\x00\x00\x00\x00\x00')
                except Exception:
                    pass
                sock.close()


def main():
    parser = argparse.ArgumentParser(
        description="Nagios plugin to test LPD/LPR printer daemon status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This plugin tests an LPD (Line Printer Daemon) server by sending a queue
status request. RFC 1179 specifies that the source port must be in the range
721-731, which requires root privileges.

Examples:
  %(prog)s -H printer.domain.com
  %(prog)s -H 192.168.1.100 -q lp -s 725
  %(prog)s -H printserver -p 515 -q pr2 -t 15
  sudo %(prog)s -H printer.local -q main_queue -v

Note: This plugin requires root privileges to bind to ports 721-731.
Run with sudo if you get permission errors.
        """
    )
    
    parser.add_argument(
        "-H", "--host",
        required=True,
        help="Hostname or IP address of LPD server"
    )
    
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=LPD_DEFAULT_PORT,
        help=f"LPD server port (default: {LPD_DEFAULT_PORT})"
    )
    
    parser.add_argument(
        "-s", "--source",
        type=int,
        default=LPD_DEFAULT_SOURCE_PORT,
        help=f"Source port to bind (default: {LPD_DEFAULT_SOURCE_PORT}, "
             f"valid: {LPD_SOURCE_PORT_MIN}-{LPD_SOURCE_PORT_MAX})"
    )
    
    parser.add_argument(
        "-q", "--queue",
        default="pr2",
        help="Queue name to check (default: pr2)"
    )
    
    parser.add_argument(
        "-t", "--timeout",
        type=int,
        default=10,
        help="Connection timeout in seconds (default: 10)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output for debugging"
    )
    
    parser.add_argument(
        "-V", "--version",
        action="version",
        version="%(prog)s 1.0 - LPD/LPR protocol checker for Nagios"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.port < 1 or args.port > 65535:
        print(f"ERROR: Port must be between 1 and 65535")
        sys.exit(NAGIOS_UNKNOWN)
    
    if args.source < 1 or args.source > 65535:
        print(f"ERROR: Source port must be between 1 and 65535")
        sys.exit(NAGIOS_UNKNOWN)
    
    if args.timeout < 1:
        print(f"ERROR: Timeout must be at least 1 second")
        sys.exit(NAGIOS_UNKNOWN)
    
    # Perform the check
    checker = LPDChecker(
        host=args.host,
        port=args.port,
        source_port=args.source,
        queue=args.queue,
        timeout=args.timeout,
        verbose=args.verbose
    )
    
    exit_code, message, response_time = checker.check_lpd()
    
    # Add performance data
    perf_data = f"response_time={response_time:.3f}s;;;0"
    
    print(f"{message} ({response_time:.3f}s response) | {perf_data}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
