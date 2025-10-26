#!/usr/bin/env python3
# +------------------------------------------------------------+
# |                                                            |
# |             | |             | |            | |             |
# |          ___| |__   ___  ___| | ___ __ ___ | | __          |
# |         / __| '_ \ / _ \/ __| |/ / '_ ` _ \| |/ /          |
# |        | (__| | | |  __/ (__|   <| | | | | |   <           |
# |         \___|_| |_|\___|\___|_|\_\_| |_| |_|_|\_\          |
# |                                   custom code by SVA       |
# |                                                            |
# +------------------------------------------------------------+
#
#   Nagios Plugin for Telekom Glasfasermodem 2
#   
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   Copyright (C) 2024  SVA System Vertrieb Alexander GmbH
#                       by michael.hoess@sva.de
# Icinga version by Lukas Bockel https://github.com/ckbaker10

import argparse
import json
import requests
import sys
from typing import Dict, Optional, Mapping
from dataclasses import dataclass


# Nagios exit codes
NAGIOS_OK = 0
NAGIOS_WARNING = 1
NAGIOS_CRITICAL = 2
NAGIOS_UNKNOWN = 3


@dataclass
class GlasModemStatus:
    device_name: str
    title: str
    dt: str
    tx_pkts: int
    tx_bytes: int
    tx_pwr: Optional[float]
    rx_pkts: int
    rx_pkts_dropped: int
    rx_pwr: Optional[float]
    rx_bip_crc: int
    link_status: int
    link_stability: int
    rx_bytes: int
    fw_version: str
    fw_version_standby: str
    hw_state: str
    hw_revision: str
    serial_no: str
    ploam_state: str
    ploam_success: bool
    rebooting: bool


def sint(s: str) -> int:
    """Safely convert string to int"""
    try:
        return int(s) if s else -1
    except (ValueError, TypeError):
        return -1


def sfloat(s: str) -> Optional[float]:
    """Safely convert string to float"""
    try:
        return float(s) if s else None
    except (ValueError, TypeError):
        return None


def fetch_data(host: str, timeout: int = 10) -> Optional[Mapping]:
    """Fetch status data from the glasfaser modem"""
    url_status = f"http://{host}/ONT/client/data/Status.json"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    try:
        r = requests.get(url_status, headers=headers, timeout=timeout)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"CRITICAL - Request failed: HTTP {r.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"CRITICAL - Connection error: {e}")
        return None


def parse_data(json_data: list) -> GlasModemStatus:
    """Parse the JSON data into GlasModemStatus object"""
    resd = {}
    for d in json_data:
        resd[d.get("varid", "")] = d.get("varvalue", "")

    return GlasModemStatus(
        device_name=resd.get("device_name", "Unknown"),
        title=resd.get("title", "Unknown"),
        dt=resd.get("datetime", ""),
        tx_pkts=sint(resd.get("txpackets", "0")),
        tx_bytes=sint(resd.get("txbytes", "0")),
        rx_pkts=sint(resd.get("rxpackets", "0")),
        rx_pkts_dropped=sint(resd.get("rxdrop_packates", "0")),
        rx_bip_crc=sint(resd.get("rxbip_crc", "0")),
        rx_bytes=sint(resd.get("rxbytes", "0")),
        tx_pwr=sfloat(resd.get("txpower")),
        rx_pwr=sfloat(resd.get("rxpower")),
        link_status=sint(resd.get("link_status", "0")),
        link_stability=sint(resd.get("stability", "0")),
        fw_version=resd.get("firmware_version", "Unknown"),
        fw_version_standby=resd.get("fw_version_standby", "Unknown"),
        serial_no=resd.get("serial_number", "Unknown"),
        hw_state=resd.get("hardware_state", "0"),
        hw_revision=resd.get("hardware_revision", "Unknown"),
        ploam_state=resd.get("ploam_state", "Unknown"),
        ploam_success=resd.get("ploam_success", "0") == "1",
        rebooting=resd.get("rebooting", "0") == "1",
    )


def check_status(status: GlasModemStatus, args) -> tuple:
    """Check modem status and return Nagios result"""
    exit_code = NAGIOS_OK
    messages = []
    performance_data = []

    # Check if rebooting
    if status.rebooting:
        exit_code = max(exit_code, NAGIOS_WARNING)
        messages.append("REBOOTING")

    # Check PLOAM success
    if not status.ploam_success:
        exit_code = max(exit_code, NAGIOS_CRITICAL)
        messages.append("PLOAM FAILED")

    # Check hardware state
    if status.hw_state == "0":
        exit_code = max(exit_code, NAGIOS_CRITICAL)
        messages.append("HW FAILED")

    # Check link status
    if status.link_status == 0:
        exit_code = max(exit_code, NAGIOS_CRITICAL)
        messages.append("LINK DOWN")

    # Check optical power levels if thresholds are provided
    if status.rx_pwr is not None:
        if args.rx_power_critical and status.rx_pwr < args.rx_power_critical:
            exit_code = max(exit_code, NAGIOS_CRITICAL)
            messages.append(f"RX POWER CRITICAL ({status.rx_pwr:.2f}dBm)")
        elif args.rx_power_warning and status.rx_pwr < args.rx_power_warning:
            exit_code = max(exit_code, NAGIOS_WARNING)
            messages.append(f"RX POWER LOW ({status.rx_pwr:.2f}dBm)")
        performance_data.append(f"rx_power={status.rx_pwr:.2f}dBm;{args.rx_power_warning or ''};{args.rx_power_critical or ''}")

    if status.tx_pwr is not None:
        performance_data.append(f"tx_power={status.tx_pwr:.2f}dBm")

    # Add packet statistics to performance data
    performance_data.extend([
        f"tx_packets={status.tx_pkts}c",
        f"rx_packets={status.rx_pkts}c",
        f"rx_dropped={status.rx_pkts_dropped}c",
        f"rx_errors={status.rx_bip_crc}c",
        f"tx_bytes={status.tx_bytes}B",
        f"rx_bytes={status.rx_bytes}B"
    ])

    # Build status message
    if exit_code == NAGIOS_OK:
        status_msg = "OK"
    elif exit_code == NAGIOS_WARNING:
        status_msg = "WARNING"
    else:
        status_msg = "CRITICAL"

    # Create summary
    summary_parts = []
    if messages:
        summary_parts.extend(messages)
    
    summary_parts.extend([
        f"FW: {status.fw_version}",
        f"Link: {status.link_status}",
        f"PLOAM: {'OK' if status.ploam_success else 'FAIL'}"
    ])

    if status.rx_pwr is not None and status.tx_pwr is not None:
        summary_parts.append(f"RX: {status.rx_pwr:.1f}dBm TX: {status.tx_pwr:.1f}dBm")

    summary = " - ".join(summary_parts)
    
    # Format output
    output = f"{status_msg} - {summary}"
    if performance_data:
        output += f" | {' '.join(performance_data)}"

    return exit_code, output


def main():
    parser = argparse.ArgumentParser(
        description="Nagios plugin to check Telekom Glasfasermodem 2 status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -H 192.168.100.1
  %(prog)s -H 192.168.100.1 --rx-power-warning -15 --rx-power-critical -20
  %(prog)s -H modem.local --timeout 5
        """
    )
    
    parser.add_argument(
        "-H", "--hostname", 
        required=True,
        help="Hostname or IP address of the glasfaser modem"
    )
    
    parser.add_argument(
        "-t", "--timeout", 
        type=int, 
        default=10,
        help="Connection timeout in seconds (default: 10)"
    )
    
    parser.add_argument(
        "--rx-power-warning", 
        type=float,
        help="RX power warning threshold in dBm (e.g., -15)"
    )
    
    parser.add_argument(
        "--rx-power-critical", 
        type=float,
        help="RX power critical threshold in dBm (e.g., -20)"
    )
    
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Validate thresholds
    if (args.rx_power_warning is not None and args.rx_power_critical is not None and 
        args.rx_power_warning < args.rx_power_critical):
        print("UNKNOWN - Warning threshold must be greater than critical threshold")
        sys.exit(NAGIOS_UNKNOWN)

    # Fetch data
    data = fetch_data(args.hostname, args.timeout)
    if data is None:
        sys.exit(NAGIOS_CRITICAL)

    try:
        # Parse data
        status = parse_data(data)
        
        # Verbose output
        if args.verbose:
            print(f"Device: {status.device_name}")
            print(f"Serial: {status.serial_no}")
            print(f"Hardware: {status.hw_revision} (State: {status.hw_state})")
            print(f"Firmware: {status.fw_version} (Standby: {status.fw_version_standby})")
            print(f"PLOAM: {status.ploam_state} (Success: {status.ploam_success})")
            print(f"Link Status: {status.link_status} (Stability: {status.link_stability})")
            if status.rx_pwr is not None:
                print(f"RX Power: {status.rx_pwr:.2f} dBm")
            if status.tx_pwr is not None:
                print(f"TX Power: {status.tx_pwr:.2f} dBm")
            print(f"TX: {status.tx_pkts} pkts, {status.tx_bytes} bytes")
            print(f"RX: {status.rx_pkts} pkts, {status.rx_bytes} bytes, {status.rx_pkts_dropped} dropped, {status.rx_bip_crc} errors")
            print()

        # Check status and output result
        exit_code, output = check_status(status, args)
        print(output)
        sys.exit(exit_code)

    except Exception as e:
        print(f"UNKNOWN - Error processing data: {e}")
        sys.exit(NAGIOS_UNKNOWN)


if __name__ == "__main__":
    main()