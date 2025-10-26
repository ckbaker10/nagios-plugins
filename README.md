# Nagios Plugins Collection## check_gmodem 2

Check for Glasfasermodem 2 from Telekom

A comprehensive collection of Nagios/Icinga monitoring plugins for modern infrastructure monitoring.

```

## Quick Start(nagios-plugins-lukas) root@mini-lenovo:/opt/nagios-plugins-lukas# python3 check_gmodem2 -H 192.168.100.1

OK - FW: 090144.1.0.009 - Link: 1000 - PLOAM: OK - RX: -14.1dBm TX: 2.5dBm | rx_power=-14.07dBm;; tx_power=2.52dBm tx_packets=268340125c rx_packets=53718213c rx_dropped=0c rx_errors=0c tx_bytes=357863307339B rx_bytes=15334274500B

### Prerequisites```



- Python 3.8+ ## check_p110 

- UV package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))Check for Tapo P110 Switchable Sockets

- Nagios or Icinga monitoring systemSources: https://github.com/mihai-dinculescu/tapo https://github.com/fishbigger/TapoP100



### Installation```

(nagios-plugins-lukas) root@mini-lenovo:/opt/nagios-plugins-lukas# python3 check_p110 -H 10.10.10.138 -u "emailaddress@mail.com" -p "Password" 

1. **Install UV** (if not already installed):OK - P05 Mediaserver : Device: ON - Power: 24.7W | signal_level=2;2;1 rssi=-57dBm power=24.664W;; energy_today=482Wh energy_month=12169Wh

```bash```

curl -LsSf https://astral.sh/uv/install.sh | sh

```## check_jetdirect 

Original Author : Yoann LAMY - converted to python - debugging bash is horrible

2. **Clone and install plugins**:

```bash```

git clone https://github.com/ckbaker10/nagios-plugins.git /opt/nagios-plugins-lukas(nagios-plugins-lukas) root@mini-lenovo:/opt/nagios-plugins-lukas# python3 check_jetdirect -H 10.10.10.151 -t page

cd /opt/nagios-plugins-lukasOK - Page count: 143437 | pages=143437;0;0;0

sudo ./install.sh```

```

```

3. **Verify installation**:(nagios-plugins-lukas) root@mini-lenovo:/opt/nagios-plugins-lukas# python3 check_jetdirect -H 10.10.10.151 -t consumable -o black -w 85 -c 90

```bashOK - Utilisation of the black cartridge: 7% | cons_used=7;85;90;0;100

sudo -u nagios /opt/nagios-plugins-lukas/check_gmodem2 --help```

sudo -u nagios /opt/nagios-plugins-lukas/check_p110 --help

sudo -u nagios /opt/nagios-plugins-lukas/check_jetdirect --help```

sudo -u nagios /opt/nagios-plugins-lukas/check_goss --help(nagios-plugins-lukas) root@mini-lenovo:/opt/nagios-plugins-lukas# python3 check_jetdirect -H 10.10.10.151 -t info

sudo -u nagios /opt/nagios-plugins-lukas/check_compose --helpOK - Info: "hp LaserJet 1320 series" (CNGW53HN8C)

``````

All commands should display help information without errors.

## Plugin Documentation

For detailed information about each plugin, their features, usage examples, and configuration:

**[See README-CHECKS.md](README-CHECKS.md)** for complete plugin documentation

## Architecture

This collection uses a wrapper-based architecture for maximum portability:

- **Python Scripts** (`*.py`): Core plugin logic with proper dependency isolation
- **Wrapper Scripts** (`check_*`): Bash wrappers that activate virtual environment and execute Python scripts
- **Virtual Environment** (`.venv/`): Isolated Python dependencies managed by UV
- **Installation Script** (`install.sh`): Automated setup with proper permissions for Nagios user

## Manual Installation

If you prefer manual setup:

```bash
# Create virtual environment with UV
uv venv .venv

# Install dependencies
uv pip install -e .

# Set ownership for Nagios user
sudo chown -R nagios:nagios /opt/nagios-plugins-lukas

# Make wrapper scripts executable
sudo chmod +x /opt/nagios-plugins-lukas/check_*
```

## Supported Plugins

- **check_gmodem2** - Telekom fiber modem monitoring via HTTP API
- **check_p110** - TP-Link smart plug monitoring with KLAP protocol support  
- **check_jetdirect** - Network printer monitoring via SNMP
- **check_goss** - Infrastructure validation using Goss framework
- **check_compose** - Docker Compose service monitoring

## Docker Setup

For Docker Compose monitoring, see **[DOCKER-SETUP.md](DOCKER-SETUP.md)** for configuring unprivileged access.

## Requirements

All dependencies are automatically managed by UV and installed in an isolated virtual environment. Key dependencies include:

- requests - HTTP client library
- pycryptodome - Encryption for smart device protocols  
- pysnmp - SNMP protocol support
- pydantic - Data validation and parsing

## Integration

### Nagios Configuration

```cfg
define command {
    command_name    check_p110
    command_line    /opt/nagios-plugins-lukas/check_p110 -H $HOSTADDRESS$ -u $ARG1$ -p $ARG2$
}
```

### Icinga2 Configuration  

```cfg
object CheckCommand "check_compose" {
    import "plugin-check-command"
    command = [ "/opt/nagios-plugins-lukas/check_compose" ]
    arguments = {
        "-p" = "$compose_project$"
        "--show-services" = { set_if = "$compose_show_services$" }
    }
}
```

## Troubleshooting

### Permission Issues
```bash
# Fix ownership
sudo chown -R nagios:nagios /opt/nagios-plugins-lukas

# Fix permissions
sudo chmod +x /opt/nagios-plugins-lukas/check_*
```

### Virtual Environment Issues
```bash
# Recreate virtual environment
cd /opt/nagios-plugins-lukas
sudo -u nagios uv venv .venv --force
sudo -u nagios uv pip install -e .
```

### Test Individual Plugin
```bash
# Run with verbose output
sudo -u nagios /opt/nagios-plugins-lukas/check_p110 -H device.local -u user -p pass -v
```

## Contributing

1. Follow Nagios plugin conventions (exit codes 0-3)
2. Include performance data in standard format
3. Provide comprehensive error handling
4. Add tests and documentation
5. Update pyproject.toml for new dependencies

## License

GPLv3 - See LICENSE file for details.