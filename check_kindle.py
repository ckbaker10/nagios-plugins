#!/usr/bin/env python3
"""
Nagios Plugin for Kindle Device Monitoring
Monitors Kindle device status via REST API including battery level, connectivity, and last seen timestamp.

Dependencies:
- requests

Copyright (C) 2024 - GPLv3 License
"""

import argparse
import sys
import requests
from typing import Tuple, Dict, Optional
import json
from datetime import datetime, timezone
import urllib3

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Nagios exit codes
NAGIOS_OK = 0
NAGIOS_WARNING = 1
NAGIOS_CRITICAL = 2
NAGIOS_UNKNOWN = 3


class KindleMonitor:
    """Kindle device monitor via REST API"""
    
    def __init__(self, base_url: str, timeout: int = 10, verify_ssl: bool = True, verbose: bool = False):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.verbose = verbose
        self.session = requests.Session()
        
        if not verify_ssl:
            self.session.verify = False
        
        # Set headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Nagios-Check-Kindle/1.0'
        })
    
    def _make_request(self, endpoint: str, method: str = 'GET') -> Tuple[Optional[Dict], Optional[str]]:
        """Make HTTP request to API endpoint
        
        Returns:
            Tuple of (response_data, error_message)
        """
        url = f"{self.base_url}{endpoint}"
        
        if self.verbose:
            print(f"DEBUG: Making {method} request to: {url}")
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout
            )
            
            if self.verbose:
                print(f"DEBUG: Response status: {response.status_code}")
                print(f"DEBUG: Response headers: {dict(response.headers)}")
            
            # Try to parse JSON response
            try:
                data = response.json()
                if self.verbose:
                    print(f"DEBUG: Response data: {json.dumps(data, indent=2)}")
            except json.JSONDecodeError:
                data = {"raw_response": response.text}
                if self.verbose:
                    print(f"DEBUG: Non-JSON response: {response.text}")
            
            if response.status_code == 200:
                return data, None
            elif response.status_code == 404:
                error_msg = data.get('error', 'Device not found') if isinstance(data, dict) else 'Device not found'
                return None, error_msg
            elif response.status_code == 500:
                error_msg = data.get('error', 'Internal server error') if isinstance(data, dict) else 'Internal server error'
                return None, error_msg
            else:
                error_msg = f"HTTP {response.status_code}: {data.get('error', response.text) if isinstance(data, dict) else response.text}"
                return None, error_msg
                
        except requests.exceptions.Timeout:
            return None, f"Request timeout after {self.timeout} seconds"
        except requests.exceptions.ConnectionError as e:
            return None, f"Connection error: {str(e)}"
        except requests.exceptions.RequestException as e:
            return None, f"Request error: {str(e)}"
        except Exception as e:
            return None, f"Unexpected error: {str(e)}"
    
    def get_device_status(self, serial: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Get device information
        
        Args:
            serial: Device serial number
            
        Returns:
            Tuple of (device_data, error_message)
        """
        # Use monitoring battery endpoint (returns battery + basic status)
        endpoint = f"/monitoring/battery/{serial}"
        return self._make_request(endpoint)
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Test API connectivity
        
        Returns:
            Tuple of (success, error_message)
        """
        endpoint = "/"
        data, error = self._make_request(endpoint)
        
        if error:
            return False, error
        
        if data and isinstance(data, dict):
            return True, None
        
        return False, "Invalid API response format"


def format_uptime(last_seen: Optional[str]) -> str:
    """Format last seen timestamp into human readable format
    
    Args:
        last_seen: ISO timestamp string or None
        
    Returns:
        Human readable time difference
    """
    if not last_seen:
        return "never"
    
    try:
        # Parse ISO timestamp
        last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        diff = now - last_seen_dt
        
        days = diff.days
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h ago"
        elif hours > 0:
            return f"{hours}h {minutes}m ago"
        else:
            return f"{minutes}m ago"
            
    except (ValueError, TypeError):
        return "invalid"


def check_kindle(args) -> Tuple[int, str]:
    """Check Kindle device status and return Nagios result"""
    try:
        monitor = KindleMonitor(
            base_url=args.url,
            timeout=args.timeout,
            verify_ssl=not args.insecure,
            verbose=args.verbose
        )
        
        # Test API connectivity first if requested
        if args.test_connection:
            success, error = monitor.test_connection()
            if not success:
                return NAGIOS_UNKNOWN, f"UNKNOWN - API connection failed: {error}"
            
            if args.verbose:
                print("DEBUG: API connection test successful")
        
        # Get device status
        device_data, error = monitor.get_device_status(args.serial)
        
        if error:
            return NAGIOS_UNKNOWN, f"UNKNOWN - API request failed: {error}"
        
        if not device_data or not isinstance(device_data, dict):
            return NAGIOS_UNKNOWN, "UNKNOWN - Invalid API response format"
        
        # Extract device information (monitoring endpoint format)
        device = device_data.get('device', {})
        if not device:
            return NAGIOS_UNKNOWN, "UNKNOWN - No device data in API response"
        
        # Extract device details from monitoring endpoint
        serial = device.get('serial', args.serial)
        hostname = device.get('hostname', 'unknown')
        battery_raw = device.get('battery', '0')  # Note: 'battery' not 'battery_level'
        last_seen = device.get('last_seen')
        model = device.get('model', 'unknown')
        is_offline = device.get('is_offline', True)  # Note: 'is_offline' not 'is_online'
        
        # Parse battery level
        try:
            if isinstance(battery_raw, (int, float)):
                battery_level = int(battery_raw)
            elif isinstance(battery_raw, str):
                battery_level = int(battery_raw.replace('%', ''))
            else:
                battery_level = 0
        except (ValueError, AttributeError):
            battery_level = 0
        
        # Format last seen
        last_seen_str = format_uptime(last_seen)
        
        # Determine device status based on connectivity and battery
        exit_code = NAGIOS_OK
        status_prefix = "OK"
        
        # Check online status (is_offline is True when device is offline)
        if is_offline:
            exit_code = NAGIOS_CRITICAL
            status_prefix = "CRITICAL"
            status_msg = f"{status_prefix} - {hostname} ({model}) - Device OFFLINE (Last seen: {last_seen_str})"
        else:
            # Check battery thresholds
            if battery_level <= args.battery_critical:
                exit_code = NAGIOS_CRITICAL
                status_prefix = "CRITICAL"
            elif battery_level <= args.battery_warning:
                exit_code = NAGIOS_WARNING
                status_prefix = "WARNING"
            
            status_msg = f"{status_prefix} - {hostname} ({model}) - Battery: {battery_level}%, Last seen: {last_seen_str}"
        
        # Add performance data
        perf_data = []
        perf_data.append(f"battery={battery_level}%;{args.battery_warning};{args.battery_critical};0;100")
        perf_data.append(f"offline={1 if is_offline else 0}")
        
        # Add device details if requested
        if args.show_details:
            ip = device.get('ip', 'unknown')
            status_msg += f" [IP: {ip}, Serial: {serial}]"
        
        # Append performance data
        final_message = status_msg
        if perf_data:
            final_message += f" | {' '.join(perf_data)}"
        
        return exit_code, final_message
        
    except Exception as e:
        error_msg = f"UNKNOWN - Error checking Kindle device: {str(e)}"
        if args.verbose:
            import traceback
            traceback.print_exc()
        return NAGIOS_UNKNOWN, error_msg


def main():
    parser = argparse.ArgumentParser(
        description="Nagios plugin to monitor Kindle devices via REST API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -u http://10.10.10.8:22116/api -s B077-XXXX-XXXX
  %(prog)s -u https://kindle-api.example.com/api -s B077-XXXX-XXXX --insecure
  %(prog)s -u http://10.10.10.8:22116/api -s B077-XXXX-XXXX --battery-warning 20 --battery-critical 10
  %(prog)s -u http://10.10.10.8:22116/api -s B077-XXXX-XXXX --show-details -v
  %(prog)s -u http://10.10.10.8:22116/api -s B077-XXXX-XXXX --test-connection --timeout 30
        """
    )
    
    parser.add_argument(
        "-u", "--url",
        required=True,
        help="Base URL of the Kindle API (e.g., http://10.10.10.8:22116/api)"
    )
    
    parser.add_argument(
        "-s", "--serial",
        required=True,
        help="Kindle device serial number"
    )
    
    parser.add_argument(
        "--battery-warning",
        type=int,
        default=25,
        help="Battery level warning threshold in percent (default: 25)"
    )
    
    parser.add_argument(
        "--battery-critical",
        type=int,
        default=15,
        help="Battery level critical threshold in percent (default: 15)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="HTTP request timeout in seconds (default: 10)"
    )
    
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable SSL certificate verification"
    )
    
    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Test API connectivity before checking device"
    )
    
    parser.add_argument(
        "--show-details",
        action="store_true",
        help="Show additional device details (IP, serial) in output"
    )
    

    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output for debugging"
    )
    
    parser.add_argument(
        "-V", "--version",
        action="version",
        version="%(prog)s 1.0 - Kindle device monitoring for Nagios"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.battery_critical >= args.battery_warning:
        print("ERROR: Critical threshold must be lower than warning threshold")
        sys.exit(NAGIOS_UNKNOWN)
    
    if not (0 <= args.battery_warning <= 100) or not (0 <= args.battery_critical <= 100):
        print("ERROR: Battery thresholds must be between 0 and 100")
        sys.exit(NAGIOS_UNKNOWN)
    
    # Perform the check
    exit_code, message = check_kindle(args)
    print(message)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()