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

### check_compose

**Purpose**: Monitor Docker Compose services and container health status

**Usage**:
```bash
check_compose [options]
check_compose -p <project_name> [options]
check_compose -f <compose_file> [options]
check_compose -d <directory> [options]
```

**Key Features**:
- Multi-project Docker Compose monitoring
- Service state detection (running, stopped, unhealthy, restarting)
- Container health status validation
- Automatic compose command detection (docker compose vs docker-compose)
- Configurable severity levels for unhealthy containers
- Service-level failure reporting
- Performance data for service counts

**Options**:
- `-p/--project`: Specify Docker Compose project name
- `-f/--file`: Path to specific docker-compose.yml file
- `-d/--directory`: Directory containing docker-compose.yml
- `--unhealthy-warning`: Treat unhealthy containers as WARNING instead of CRITICAL
- `--show-services`: Include individual service details in output

**Status Detection**:
- **Running**: Service is up and operational
- **Unhealthy**: Service is running but health check fails
- **Stopped**: Service has exited or is not running
- **Restarting**: Service is in restart loop
- **Other**: Unknown or error states

**Performance Data**: Includes total services, running count, unhealthy count, stopped count, and other state count

**Security**: Requires Docker access permissions.

**Common Use Cases**:
- Container orchestration monitoring
- Application stack health validation
- Microservices deployment verification
- Development environment status checks

---

### check_jetdirect

**Purpose**: Monitor network printers via SNMP protocol

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

**Arguments**:
- `-H, --hostname`: Printer hostname or IP address (required)
- `-C, --community`: SNMP community string (default: public)
- `-t, --type`: Check type - `consumable`, `page`, or `info` (default: page)
- `-o, --consumable`: Consumable type when using `-t consumable` - `black`, `cyan`, `magenta`, `yellow`, or `drum` (default: black)
- `-w, --warning`: Warning threshold for consumable usage percentage (default: 0)
- `-c, --critical`: Critical threshold for consumable usage percentage (default: 0)
- `-v, --verbose`: Enable verbose debugging output

**Check Types**:
- `page`: Monitor total page count (default)
- `consumable`: Monitor toner/ink levels with thresholds
- `info`: Retrieve printer model and serial number

**Consumable Types**: 
Use with `-o` option when check type is `consumable`:
- `black`: Black toner/ink cartridge
- `cyan`: Cyan toner/ink cartridge
- `magenta`: Magenta toner/ink cartridge
- `yellow`: Yellow toner/ink cartridge
- `drum`: Drum unit

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

define command {
    command_name    check_docker_compose
    command_line    $USER1$/check_compose -p $ARG1$ $ARG2$
}

define command {
    command_name    check_docker_compose_file
    command_line    $USER1$/check_compose -f $ARG1$ $ARG2$
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

# Monitor Docker Compose services
./check_compose -p icinga-playground --show-services

# Monitor compose stack with file path
./check_compose -f /opt/myapp/docker-compose.yml --unhealthy-warning
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

---

### check_eap772

**Purpose**: Monitor TP-Link Omada EAP772 access points via SNMPv3 protocol

**Usage**:
```bash
check_eap772 -H <hostname> -u <username> -p <password> [options]
```

**Key Features**:
- System information monitoring (uptime, description, location, contact)
- Network interface status tracking (up/down detection)
- Interface traffic monitoring (bytes in/out with rate calculation)
- Error rate monitoring (errors, discards per interface)
- Critical interface validation (eth0, br0 must be operational)
- Comprehensive performance data for trending

**Required Arguments**:
- `-H, --host`: Hostname or IP address of the EAP772 access point
- `-u, --username`: SNMPv3 username (e.g., "monitoring")
- `-p, --password`: SNMPv3 authentication password (MD5 protocol)

**Optional Arguments**:
- `--error-threshold`: Error count threshold for warning (default: 100)
- `--ignore-errors`: Ignore interface error counts in status determination
- `-i, --interfaces`: Comma-separated list of interfaces to monitor (e.g., 'eth0,br0'). If not specified, monitors default set: eth0, br0, wifi0, wifi1, wifi2, ath0, ath10, ath20
- `--show-interfaces`: Show interface status in output
- `-v, --verbose`: Enable verbose output for debugging

**SNMPv3 Configuration**:
- Security Level: authNoPriv (authentication without encryption)
- Auth Protocol: MD5
- No encryption protocol required
- Standard SNMP OIDs used (IF-MIB)

**Performance Data**:
For each network interface:
- `{interface}_bytes_in`: Inbound bytes counter
- `{interface}_bytes_out`: Outbound bytes counter
- `{interface}_errors_in`: Inbound error counter
- `{interface}_errors_out`: Outbound error counter
- `{interface}_discards_in`: Inbound discard counter
- `{interface}_discards_out`: Outbound discard counter
- `{interface}_status`: Interface operational status (1=up, 2=down)

**Common Use Cases**:
- Wireless access point health monitoring
- Network interface status validation
- Traffic and error rate trending
- Critical interface availability tracking (uplink and management)

**Example Commands**:

Basic monitoring:
```bash
check_eap772 -H 10.10.10.231 -u monitoring -p MySecurePassword
```

With custom error threshold:
```bash
check_eap772 -H 10.10.10.231 -u monitoring -p MySecurePassword --error-threshold 1000
```

Ignore error counts:
```bash
check_eap772 -H 10.10.10.231 -u monitoring -p MySecurePassword --ignore-errors
```

Monitor only specific interfaces:
```bash
check_eap772 -H 10.10.10.231 -u monitoring -p MySecurePassword -i eth0,br0
```

Verbose debugging:
```bash
check_eap772 -H 10.10.10.231 -u monitoring -p MySecurePassword -v
```

**Icinga2 Configuration Example**:
```
object CheckCommand "eap772" {
  command = [ "/opt/nagios-plugins-lukas/check_eap772" ]
  
  arguments = {
    "-H" = "$eap772_host$"
    "-u" = "$eap772_username$"
    "-p" = "$eap772_password$"
    "--error-threshold" = "$eap772_error_threshold$"
    "--ignore-errors" = {
      set_if = "$eap772_ignore_errors$"
    }
    "-i" = "$eap772_interfaces$"
    "--show-interfaces" = {
      set_if = "$eap772_show_interfaces$"
    }
  }
}

object Service "EAP772 Health" {
  host_name = "ap-office-1"
  check_command = "eap772"
  
  vars.eap772_host = "10.10.10.231"
  vars.eap772_username = "monitoring"
  vars.eap772_password = "MySecurePassword"
  vars.eap772_error_threshold = 1000
}

# Example: Monitor only critical interfaces and ignore errors
object Service "EAP772 Critical Interfaces" {
  host_name = "ap-office-2"
  check_command = "eap772"
  
  vars.eap772_host = "10.10.10.232"
  vars.eap772_username = "monitoring"
  vars.eap772_password = "MySecurePassword"
  vars.eap772_interfaces = "eth0,br0"
  vars.eap772_ignore_errors = true
}
```

**Nagios Configuration Example**:
```
define command {
    command_name    check_eap772
    command_line    /opt/nagios-plugins-lukas/check_eap772 -H $ARG1$ -u $ARG2$ -p $ARG3$ --error-threshold $ARG4$
}

define command {
    command_name    check_eap772_filtered
    command_line    /opt/nagios-plugins-lukas/check_eap772 -H $ARG1$ -u $ARG2$ -p $ARG3$ -i $ARG4$ --ignore-errors
}

define service {
    use                     generic-service
    host_name               ap-office-1
    service_description     EAP772 Health
    check_command           check_eap772!10.10.10.231!monitoring!MySecurePassword!1000
}

define service {
    use                     generic-service
    host_name               ap-office-2
    service_description     EAP772 Critical Interfaces
    check_command           check_eap772_filtered!10.10.10.232!monitoring!MySecurePassword!eth0,br0
}
```

**Monitored SNMP OIDs**:
- `.1.3.6.1.2.1.1.1.0` - sysDescr (System description)
- `.1.3.6.1.2.1.1.3.0` - sysUpTime (System uptime)
- `.1.3.6.1.2.1.1.4.0` - sysContact (System contact)
- `.1.3.6.1.2.1.1.5.0` - sysName (System name)
- `.1.3.6.1.2.1.1.6.0` - sysLocation (System location)
- `.1.3.6.1.2.1.2.2.1.2` - ifDescr (Interface descriptions)
- `.1.3.6.1.2.1.2.2.1.8` - ifOperStatus (Interface operational status)
- `.1.3.6.1.2.1.2.2.1.10` - ifInOctets (Inbound byte counter)
- `.1.3.6.1.2.1.2.2.1.14` - ifInErrors (Inbound error counter)
- `.1.3.6.1.2.1.2.2.1.16` - ifOutOctets (Outbound byte counter)
- `.1.3.6.1.2.1.2.2.1.19` - ifInDiscards (Inbound discard counter)
- `.1.3.6.1.2.1.2.2.1.20` - ifOutErrors (Outbound error counter)
- `.1.3.6.1.2.1.2.2.1.13` - ifOutDiscards (Outbound discard counter)

**Troubleshooting**:

Common issues and solutions:

1. **SNMPv3 authentication failure**: 
   - Verify username and password are correct
   - Confirm auth protocol is MD5 (not SHA)
   - Security level must be authNoPriv (not authPriv)
   - Check that SNMPv3 user is configured on the device

2. **SNMP timeout**:
   - Verify network connectivity to the device
   - Check firewall rules allow UDP port 161
   - Confirm SNMP service is enabled on the EAP772
   - Try with verbose mode to see SNMP command details

3. **Critical interface down**:
   - eth0 or br0 interfaces are required to be operational
   - Check physical network connections
   - Verify device configuration
   - Review device logs for hardware issues

4. **High error rates**:
   - Investigate network quality issues
   - Check for cable problems or interference
   - Review switch port statistics for duplex mismatches
   - Adjust thresholds if normal for environment

5. **Missing performance data**:
   - Ensure SNMP permissions include IF-MIB read access
   - Verify OID support with snmpwalk testing
   - Check that interface counters are being updated