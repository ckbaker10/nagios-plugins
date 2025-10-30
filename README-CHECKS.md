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

### check_kindle

**Purpose**: Monitor Kindle e-reader devices through a custom Kindle management platform API, tracking battery levels, connectivity status, and deep sleep behavior

**Usage**:
```bash
check_kindle -u <api_url> -s <serial> [options]
```

**Key Features**:
- Device connectivity and online status monitoring
- Battery level tracking with configurable thresholds
- Deep sleep mode support with configurable offline grace period
- Last seen timestamp tracking
- Device model and hostname identification
- IP address and serial number reporting
- SSL/TLS support with optional certificate verification

**Required Arguments**:
- `-u, --url`: Base URL of the Kindle API (e.g., http://10.10.10.8:22116/api)
- `-s, --serial`: Kindle device serial number (e.g., B077-XXXX-XXXX)

**Optional Arguments**:
- `--battery-warning`: Battery level warning threshold in percent (default: 25)
- `--battery-critical`: Battery level critical threshold in percent (default: 15)
- `--offline-hours`: Hours device can be offline before triggering CRITICAL (default: 4.0, for deep sleep mode)
- `--timeout`: HTTP request timeout in seconds (default: 10)
- `--insecure`: Disable SSL certificate verification
- `--test-connection`: Test API connectivity before checking device
- `--show-details`: Show additional device details (IP, serial) in output
- `-v, --verbose`: Verbose output for debugging

**Deep Sleep Mode Handling**:
Kindle devices enter deep sleep mode to conserve battery, making them appear offline for extended periods. The `--offline-hours` parameter prevents false alarms:
- If offline < threshold hours: Status OK with "Device in sleep mode" message
- If offline > threshold hours: Status CRITICAL with "Device OFFLINE" alert
- Default: 4.0 hours (adjust based on your devices' sleep patterns)

**Performance Data**:
- `battery`: Battery level percentage with warning/critical thresholds
- `offline`: Binary indicator (1=offline, 0=online)
- `offline_hours`: Actual hours since last seen

**Common Use Cases**:
- E-reader fleet management
- Battery level monitoring and maintenance scheduling
- Device availability tracking with sleep mode awareness
- Remote device health validation

**Example Commands**:

Basic monitoring with default thresholds:
```bash
check_kindle -u http://10.10.10.8:22116/api -s B077-XXXX-XXXX
```

Custom battery thresholds:
```bash
check_kindle -u http://10.10.10.8:22116/api -s B077-XXXX-XXXX --battery-warning 20 --battery-critical 10
```

Allow 8 hours of deep sleep before alerting:
```bash
check_kindle -u http://10.10.10.8:22116/api -s B077-XXXX-XXXX --offline-hours 8.0
```

Allow overnight sleep (12 hours):
```bash
check_kindle -u http://10.10.10.8:22116/api -s B077-XXXX-XXXX --offline-hours 12.0
```

With SSL and detailed output:
```bash
check_kindle -u https://kindle-api.example.com/api -s B077-XXXX-XXXX --show-details
```

Self-signed certificate support:
```bash
check_kindle -u https://10.10.10.8:22116/api -s B077-XXXX-XXXX --insecure
```

Test API connectivity:
```bash
check_kindle -u http://10.10.10.8:22116/api -s B077-XXXX-XXXX --test-connection --timeout 30
```

Verbose debugging:
```bash
check_kindle -u http://10.10.10.8:22116/api -s B077-XXXX-XXXX --show-details -v
```

**Icinga2 Configuration Example**:
```
object CheckCommand "check_kindle" {
  command = [ "/opt/nagios-plugins-lukas/check_kindle" ]
  
  arguments = {
    "-u" = {
      value = "$kindle_api_url$"
      required = true
    }
    "-s" = {
      value = "$kindle_serial$"
      required = true
    }
    "--battery-warning" = "$kindle_battery_warning$"
    "--battery-critical" = "$kindle_battery_critical$"
    "--offline-hours" = "$kindle_offline_hours$"
    "--timeout" = "$kindle_timeout$"
    "--insecure" = {
      set_if = "$kindle_insecure$"
    }
    "--test-connection" = {
      set_if = "$kindle_test_connection$"
    }
    "--show-details" = {
      set_if = "$kindle_show_details$"
    }
    "-v" = {
      set_if = "$kindle_verbose$"
    }
  }
}

object Service "Kindle Battery" {
  host_name = "kindle-living-room"
  check_command = "check_kindle"
  
  vars.kindle_api_url = "http://10.10.10.8:22116/api"
  vars.kindle_serial = "B077-1234-5678"
  vars.kindle_battery_warning = 25
  vars.kindle_battery_critical = 15
  vars.kindle_offline_hours = 8.0
}

# Example: Monitoring device with overnight sleep allowance
object Service "Kindle Bedroom" {
  host_name = "kindle-bedroom"
  check_command = "check_kindle"
  
  vars.kindle_api_url = "http://10.10.10.8:22116/api"
  vars.kindle_serial = "B077-8765-4321"
  vars.kindle_offline_hours = 12.0  # Allow overnight sleep
  vars.kindle_show_details = true
}

# Example: HTTPS with self-signed certificate
object Service "Kindle Office" {
  host_name = "kindle-office"
  check_command = "check_kindle"
  
  vars.kindle_api_url = "https://kindle-api.local/api"
  vars.kindle_serial = "B077-9999-1111"
  vars.kindle_insecure = true
  vars.kindle_timeout = 15
}
```

**Nagios Configuration Example**:
```
define command {
    command_name    check_kindle
    command_line    /opt/nagios-plugins-lukas/check_kindle -u $ARG1$ -s $ARG2$ --battery-warning $ARG3$ --battery-critical $ARG4$ --offline-hours $ARG5$
}

define command {
    command_name    check_kindle_basic
    command_line    /opt/nagios-plugins-lukas/check_kindle -u $ARG1$ -s $ARG2$
}

define service {
    use                     generic-service
    host_name               kindle-living-room
    service_description     Kindle Battery
    check_command           check_kindle!http://10.10.10.8:22116/api!B077-1234-5678!25!15!8.0
}

define service {
    use                     generic-service
    host_name               kindle-bedroom
    service_description     Kindle Status
    check_command           check_kindle!http://10.10.10.8:22116/api!B077-8765-4321!20!10!12.0
}
```

**API Response Format**:
The plugin expects the API endpoint `/monitoring/battery/{serial}` to return JSON in this format:
```json
{
  "device": {
    "serial": "B077-XXXX-XXXX",
    "hostname": "kindle-kt2",
    "model": "Kindle Touch 2",
    "battery": "85",
    "last_seen": "2025-10-30T10:15:30Z",
    "is_offline": false,
    "ip": "192.168.1.100"
  }
}
```

**Status Logic**:
1. **Device Offline**: 
   - If `is_offline=true` AND `offline_hours > --offline-hours`: CRITICAL
   - If `is_offline=true` AND `offline_hours ≤ --offline-hours`: OK (sleep mode)
2. **Device Online**:
   - Battery ≤ critical threshold: CRITICAL
   - Battery ≤ warning threshold: WARNING
   - Otherwise: OK

**Troubleshooting**:

Common issues and solutions:

1. **API connection failed**:
   - Verify the API URL is correct and accessible
   - Check network connectivity
   - Ensure API service is running
   - Try with `--test-connection` flag

2. **Device not found (404)**:
   - Verify the serial number is correct
   - Check that the device is registered in the API
   - Confirm the API endpoint format matches expectations

3. **SSL certificate verification failed**:
   - Use `--insecure` flag for self-signed certificates
   - Or install the proper CA certificate
   - Or use HTTP instead of HTTPS if acceptable

4. **Timeout errors**:
   - Increase timeout with `--timeout` option
   - Check API server performance
   - Verify network latency

5. **False offline alerts**:
   - Increase `--offline-hours` threshold to match device sleep patterns
   - Monitor actual sleep duration in performance data
   - Consider device-specific sleep schedules

6. **Invalid API response format**:
   - Enable verbose mode with `-v` to see actual API response
   - Verify API version compatibility
   - Check API documentation for expected format

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
- `--ignore-services`: Comma-separated list of service names to ignore (e.g., 'init-icinga2,backup')

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

# Ignore init containers and backups
./check_compose -p icinga-playground --ignore-services init-icinga2,backup
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
- `--ignore-down`: Ignore down interfaces in status determination (useful for statistics tracking)
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

Statistics tracking mode (ignore all errors and down interfaces):
```bash
check_eap772 -H 10.10.10.231 -u monitoring -p MySecurePassword --ignore-errors --ignore-down
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
    "--ignore-down" = {
      set_if = "$eap772_ignore_down$"
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

# Example: Statistics tracking (always OK, only collect performance data)
object Service "EAP772 Statistics" {
  host_name = "ap-office-3"
  check_command = "eap772"
  
  vars.eap772_host = "10.10.10.233"
  vars.eap772_username = "monitoring"
  vars.eap772_password = "MySecurePassword"
  vars.eap772_ignore_errors = true
  vars.eap772_ignore_down = true
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

define command {
    command_name    check_eap772_stats
    command_line    /opt/nagios-plugins-lukas/check_eap772 -H $ARG1$ -u $ARG2$ -p $ARG3$ --ignore-errors --ignore-down
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

define service {
    use                     generic-service
    host_name               ap-office-3
    service_description     EAP772 Statistics
    check_command           check_eap772_stats!10.10.10.233!monitoring!MySecurePassword
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