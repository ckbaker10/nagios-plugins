# Nagios Plugin Checks Documentation

This document describes the available Nagios monitoring plugins in this repository.

## Overview

This collection provides monitoring plugins for various network devices and system validation tools. All plugins follow standard Nagios conventions with proper exit codes, performance data, and comprehensive error handling.

## Available Plugins

### check_gmodem2

**Purpose**: Monitor Telekom Glasfasermodem 2 fiber optic modems via HTTP API

**Usage**:
```bash
check_gmodem2 -H <hostname> [options]
```

**Key Features**:
- Real-time optical power monitoring (RX/TX power levels)
- Link status and stability monitoring
- PLOAM (Physical Layer Operations Administration and Maintenance) status checking
- Hardware state validation
- Firmware version reporting
- Network statistics (packets, bytes, drops, errors)

**Thresholds**:
- `--rx-power-warning`: RX optical power warning threshold in dBm
- `--rx-power-critical`: RX optical power critical threshold in dBm

**Performance Data**: Includes optical power levels, packet statistics, byte counters, and error rates

**Common Use Cases**:
- Fiber connection quality monitoring
- ISP service level validation
- Network infrastructure health checks

---

### check_p110

**Purpose**: Monitor TP-Link P110 smart plugs with energy monitoring capabilities

**Usage**:
```bash
check_p110 -H <hostname> -u <email> -p <password> [options]
```

**Key Features**:
- Protocol auto-discovery (Passthrough/KLAP)
- Device power state monitoring
- Energy consumption tracking (current power, daily/monthly usage)
- Signal strength monitoring (WiFi RSSI and signal level)
- Safety status monitoring (power protection, overcurrent, charging status)
- State expectation validation

**Authentication**: Requires TP-Link cloud account credentials

**Thresholds**:
- `--power-warning/--power-critical`: Power consumption thresholds in Watts
- `--signal-warning/--signal-critical`: WiFi signal level thresholds
- `--expect-on/--expect-off`: Expected device state validation
- `--expect-power-protection`: Expected power protection status
- `--expect-overcurrent`: Expected overcurrent protection status
- `--expect-charging`: Expected charging status

**Performance Data**: Power consumption, energy usage, signal strength, device status

**Common Use Cases**:
- Smart home device monitoring
- Power consumption analysis
- Remote device availability checking
- Energy usage reporting

---

### check_jetdirect

**Purpose**: Monitor network printers via SNMP using HP JetDirect or compatible print servers

**Usage**:
```bash
check_jetdirect -H <hostname> [options]
```

**Key Features**:
- Multiple check types: consumables, page counts, printer information
- Automatic printer compatibility detection
- Multiple OID support for different printer models
- Consumable level monitoring (toner, ink cartridges, drums)
- Page counter tracking
- Printer identification and status

**Check Types**:
- `page`: Monitor total page count (default)
- `consumable`: Monitor toner/ink levels with thresholds
- `info`: Retrieve printer model and serial number

**Consumable Types**: black, cyan, magenta, yellow, drum

**Thresholds**:
- `--warning/--critical`: Consumable usage percentage thresholds

**Performance Data**: Page counts, consumable usage percentages

**Dependencies**: Requires net-snmp-utils (snmpget/snmpwalk commands)

**Common Use Cases**:
- Print fleet management
- Consumable inventory tracking
- Printer availability monitoring
- Usage statistics collection

---

### check_goss

**Purpose**: Execute Goss validation tests and report infrastructure compliance

**Usage**:
```bash
check_goss [-g <goss_file>] [options]
```

**Key Features**:
- Infrastructure as code validation
- Multiple output format support (rspecish, TAP, JSON, JUnit)
- Variable file support for templating
- Package manager specific testing
- Failure detail reporting
- Any test failure treated as CRITICAL (infrastructure binary principle)

**Configuration Options**:
- `-g/--goss-file`: Path to Goss YAML configuration file
- `--vars`: Variables file for Goss templating
- `--package`: Package manager for package tests (apk, deb, pacman, rpm)
- `-f/--format`: Output format selection

**Performance Data**: Test counts, pass/fail statistics, failure percentage

**Dependencies**: Requires goss binary in PATH

**Common Use Cases**:
- Server configuration validation
- Compliance checking
- Infrastructure drift detection
- Deployment verification
- Security baseline validation

## General Plugin Features

### Standard Nagios Compliance
- Exit codes: 0 (OK), 1 (WARNING), 2 (CRITICAL), 3 (UNKNOWN)
- Performance data output for graphing and trending
- Comprehensive help documentation
- Timeout handling and error management

### Common Options
- `-H/--hostname`: Target device hostname or IP address
- `-t/--timeout`: Connection timeout in seconds
- `-v/--verbose`: Debug output for troubleshooting
- `-V/--version`: Plugin version information
- `--help`: Detailed usage information and examples

### Error Handling
- Network connectivity validation
- Authentication failure detection
- Protocol compatibility checking
- Graceful degradation with informative error messages
- Timeout protection for all network operations

## Installation Requirements

### Python Dependencies
Install via pip or package manager:
```bash
pip install -r requirements.txt
```

Required packages:
- requests (HTTP client)
- pycryptodome (P110 encryption)
- pkcs7 (P110 protocol support)
- urllib3 (HTTP utilities)

### System Dependencies
- net-snmp-utils (for check_jetdirect)
- goss binary (for check_goss)

### File Permissions
Ensure plugins are executable:
```bash
chmod +x check_*
```

## Integration Examples

### Nagios Configuration
```
define command {
    command_name    check_gmodem2
    command_line    $USER1$/check_gmodem2 -H $HOSTADDRESS$ --rx-power-warning -15 --rx-power-critical -20
}

define command {
    command_name    check_p110
    command_line    $USER1$/check_p110 -H $HOSTADDRESS$ -u $ARG1$ -p $ARG2$ --power-warning 1000
}
```

### Command Line Testing
```bash
# Test fiber modem with optical power thresholds
./check_gmodem2 -H 192.168.100.1 --rx-power-warning -15 --rx-power-critical -20

# Monitor smart plug with power and state validation
./check_p110 -H 192.168.1.100 -u user@example.com -p password --expect-on --power-warning 50

# Check printer toner levels
./check_jetdirect -H printer.domain.com -t consumable -o black -w 85 -c 90

# Validate server configuration
./check_goss -g /etc/goss/server.yaml --show-failures
```

## Performance Data Format

All plugins output performance data in Nagios standard format:
```
'label'=value[UOM];[warn];[crit];[min];[max]
```

Where:
- UOM: Unit of measurement (W, dBm, %, c for counters)
- warn/crit: Warning and critical thresholds
- min/max: Minimum and maximum expected values

This enables integration with monitoring dashboards, trending systems, and alerting tools.

## Troubleshooting

### Common Issues
1. **Permission denied**: Verify plugin executable permissions
2. **Module not found**: Install required Python dependencies
3. **Connection timeout**: Check network connectivity and firewall rules
4. **Authentication failed**: Verify credentials and account access
5. **SNMP timeout**: Confirm SNMP community strings and device configuration

### Debug Mode
Use `-v/--verbose` flag for detailed troubleshooting information:
```bash
./check_p110 -H device.local -u user -p pass -v
```

This provides protocol discovery details, authentication steps, and API response data for problem diagnosis.