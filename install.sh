#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR=$SCRIPT_DIR
NAGIOS_USER="nagios"

echo "=========================================="
echo "Nagios Plugins Installation Script"
echo "=========================================="
echo ""

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "Detected OS: $NAME ${VERSION_ID:-unknown}"
    echo "OS ID: $ID"
    
    # Check for supported distributions
    case "$ID" in
        ubuntu|debian)
            echo "Distribution: Debian-based (compatible)"
            ;;
        rocky|rhel|centos|fedora|almalinux)
            echo "Distribution: RHEL-based (compatible)"
            if [[ "$VERSION_ID" =~ ^8 ]]; then
                echo "Version: 8.x series detected"
            fi
            ;;
        *)
            echo "WARNING: Untested distribution - script may need adjustments"
            ;;
    esac
else
    echo "WARNING: Cannot detect OS distribution"
fi

echo ""
echo "Setting up Nagios plugins for user: $NAGIOS_USER"
echo "Plugin directory: $PLUGIN_DIR"
echo ""

# Check if running as root for optional goss installation
if [ "$EUID" -eq 0 ]; then
    # Check if goss is already installed
    if ! command -v goss &> /dev/null; then
        echo "Goss not found - installing goss binary..."
        GOSS_VERSION="v0.4.4"
        GOSS_URL="https://github.com/goss-org/goss/releases/download/${GOSS_VERSION}/goss-linux-amd64"
        
        if curl -L "$GOSS_URL" -o /usr/bin/goss 2>/dev/null; then
            chmod +x /usr/bin/goss
            echo "Goss ${GOSS_VERSION} installed successfully to /usr/bin/goss"
        else
            echo "WARNING: Failed to download goss. check_goss plugin will require manual goss installation."
        fi
    else
        GOSS_INSTALLED_VERSION=$(goss --version 2>/dev/null || echo "unknown")
        echo "Goss already installed: $GOSS_INSTALLED_VERSION"
    fi
    
    # Create /opt/goss directory if it doesn't exist
    if [ ! -d "/opt/goss" ]; then
        echo "Creating /opt/goss directory..."
        mkdir -p /opt/goss
        chown "$NAGIOS_USER:$NAGIOS_USER" /opt/goss
        echo "Created /opt/goss directory"
    fi
    
    # Copy goss.yaml from /root if it exists
    if [ -f "/root/goss.yaml" ]; then
        if [ -f "/opt/goss/goss.yaml" ]; then
            echo "goss.yaml already exists in /opt/goss - skipping copy (not overwriting existing file)"
        else
            echo "Found goss.yaml in /root - copying to /opt/goss/goss.yaml..."
            cp /root/goss.yaml /opt/goss/goss.yaml
            chown "$NAGIOS_USER:$NAGIOS_USER" /opt/goss/goss.yaml
            chmod 644 /opt/goss/goss.yaml
            echo "Copied goss.yaml to /opt/goss/goss.yaml"
        fi
    else
        echo "No goss.yaml found in /root - skipping copy"
    fi
    
    # Configure sudo rules for check_smart and check_lm_sensors
    echo "Configuring sudo rules for check_smart and check_lm_sensors..."
    SUDOERS_FILE="/etc/sudoers.d/nagios-plugins"
    
    # Detect OS for distribution-specific paths
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_ID="$ID"
        OS_VERSION_ID="$VERSION_ID"
        echo "Detected OS: $NAME ${VERSION_ID:-unknown}"
    else
        OS_ID="unknown"
        echo "WARNING: Cannot detect OS, assuming generic paths"
    fi
    
    # Find paths to required binaries (check multiple locations)
    SMARTCTL_PATH=$(command -v smartctl 2>/dev/null)
    if [ -z "$SMARTCTL_PATH" ]; then
        # Try common paths for different distributions
        for path in /usr/sbin/smartctl /sbin/smartctl /usr/local/sbin/smartctl; do
            if [ -x "$path" ]; then
                SMARTCTL_PATH="$path"
                break
            fi
        done
        # Default fallback
        SMARTCTL_PATH="${SMARTCTL_PATH:-/usr/sbin/smartctl}"
    fi
    
    SENSORS_PATH=$(command -v sensors 2>/dev/null)
    if [ -z "$SENSORS_PATH" ]; then
        # Try common paths
        for path in /usr/bin/sensors /bin/sensors /usr/local/bin/sensors; do
            if [ -x "$path" ]; then
                SENSORS_PATH="$path"
                break
            fi
        done
        SENSORS_PATH="${SENSORS_PATH:-/usr/bin/sensors}"
    fi
    
    HDDTEMP_PATH=$(command -v hddtemp 2>/dev/null)
    if [ -z "$HDDTEMP_PATH" ]; then
        # Try common paths
        for path in /usr/sbin/hddtemp /sbin/hddtemp /usr/local/sbin/hddtemp; do
            if [ -x "$path" ]; then
                HDDTEMP_PATH="$path"
                break
            fi
        done
        HDDTEMP_PATH="${HDDTEMP_PATH:-/usr/sbin/hddtemp}"
    fi
    
    echo "  smartctl path: $SMARTCTL_PATH"
    echo "  sensors path: $SENSORS_PATH"
    echo "  hddtemp path: $HDDTEMP_PATH"
    
    # Create sudoers file with NOPASSWD rules
    cat > "$SUDOERS_FILE" << EOF
# Nagios plugins - minimal permissions for hardware monitoring
# Allow nagios user to run smartctl, sensors, and hddtemp without password
Defaults:$NAGIOS_USER !requiretty
$NAGIOS_USER ALL=(root) NOPASSWD: $SMARTCTL_PATH
$NAGIOS_USER ALL=(root) NOPASSWD: $SENSORS_PATH
$NAGIOS_USER ALL=(root) NOPASSWD: $HDDTEMP_PATH
EOF
    
    # Set correct permissions on sudoers file
    chmod 0440 "$SUDOERS_FILE"
    
    # Validate sudoers syntax
    if visudo -c -f "$SUDOERS_FILE" >/dev/null 2>&1; then
        echo "Sudo rules configured successfully in $SUDOERS_FILE"
    else
        echo "ERROR: Invalid sudoers syntax, removing file"
        rm -f "$SUDOERS_FILE"
        echo "WARNING: check_smart and check_lm_sensors will require manual sudo configuration"
    fi
    
    # Provide distribution-specific package installation hints if binaries are missing
    if [ ! -x "$SMARTCTL_PATH" ]; then
        echo ""
        echo "WARNING: smartctl not found. Install smartmontools package:"
        case "$OS_ID" in
            rocky|rhel|centos|fedora)
                echo "  sudo dnf install smartmontools"
                ;;
            debian|ubuntu)
                echo "  sudo apt-get install smartmontools"
                ;;
            *)
                echo "  Install smartmontools package for your distribution"
                ;;
        esac
    fi
    
    if [ ! -x "$SENSORS_PATH" ]; then
        echo ""
        echo "WARNING: sensors not found. Install lm_sensors package:"
        case "$OS_ID" in
            rocky|rhel|centos|fedora)
                echo "  sudo dnf install lm_sensors"
                ;;
            debian|ubuntu)
                echo "  sudo apt-get install lm-sensors"
                ;;
            *)
                echo "  Install lm_sensors package for your distribution"
                ;;
        esac
    fi
    
    if [ ! -x "$HDDTEMP_PATH" ]; then
        echo ""
        echo "WARNING: hddtemp not found. Install hddtemp package:"
        case "$OS_ID" in
            rocky|rhel|centos|fedora)
                echo "  sudo dnf install hddtemp"
                echo "  (Note: hddtemp may need EPEL repository on Rocky/RHEL)"
                ;;
            debian|ubuntu)
                echo "  sudo apt-get install hddtemp"
                ;;
            *)
                echo "  Install hddtemp package for your distribution"
                ;;
        esac
    fi
else
    echo "NOTE: Not running as root - skipping goss binary installation and sudo configuration"
    echo "      Run 'sudo ./install.sh' if you need goss installed or sudo rules configured"
fi

# Install UV for nagios user
echo "Installing UV for nagios user..."
sudo -u "$NAGIOS_USER" bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'

# Find UV path for nagios user
NAGIOS_HOME=$(sudo -u "$NAGIOS_USER" bash -c 'echo $HOME')
UV_PATH=""

# Check common UV installation locations for nagios user
for path in "$NAGIOS_HOME/.local/bin/uv" "$NAGIOS_HOME/.cargo/bin/uv" "/home/$NAGIOS_USER/.local/bin/uv" "/home/$NAGIOS_USER/.cargo/bin/uv"; do
    if [ -f "$path" ]; then
        UV_PATH="$path"
        break
    fi
done

if [ -z "$UV_PATH" ]; then
    echo "ERROR: UV installation failed for nagios user"
    exit 1
fi

echo "UV package manager available for nagios user at: $UV_PATH"

# Check if nagios user exists
if ! id "$NAGIOS_USER" &>/dev/null; then
    echo "ERROR: User '$NAGIOS_USER' does not exist. Please create the nagios user first."
    exit 1
fi

echo "Nagios user '$NAGIOS_USER' exists"

# Check if Docker is installed and add nagios user to docker group
if command -v docker &> /dev/null; then
    echo "Docker found - adding '$NAGIOS_USER' user to docker group..."
    if ! groups "$NAGIOS_USER" | grep -q docker; then
        # Check if docker group exists, create if needed (for some minimal installations)
        if ! getent group docker >/dev/null; then
            echo "Docker group doesn't exist, creating it..."
            groupadd docker
        fi
        
        usermod -aG docker "$NAGIOS_USER"
        echo "Added '$NAGIOS_USER' to docker group for Docker Compose monitoring"
        
        # Restart monitoring service to apply group changes
        service_restarted=false
        if systemctl is-active --quiet icinga2 2>/dev/null; then
            echo "Restarting Icinga2 service to apply docker group changes..."
            systemctl restart icinga2
            service_restarted=true
            echo "Icinga2 service restarted successfully"
        elif systemctl is-active --quiet nagios 2>/dev/null; then
            echo "Restarting Nagios service to apply docker group changes..."
            systemctl restart nagios
            service_restarted=true
            echo "Nagios service restarted successfully"
        elif systemctl is-active --quiet nagios4 2>/dev/null; then
            echo "Restarting Nagios4 service to apply docker group changes..."
            systemctl restart nagios4
            service_restarted=true
            echo "Nagios4 service restarted successfully"
        fi
        
        if [ "$service_restarted" = false ]; then
            echo "NOTE: Nagios/Icinga service not detected or not running"
            echo "      Please restart your monitoring service manually for docker group changes to take effect:"
            echo "      sudo systemctl restart icinga2"
            echo "      (or sudo systemctl restart nagios)"
        fi
    else
        echo "User '$NAGIOS_USER' is already in docker group"
    fi
else
    echo "Docker not found - skipping docker group setup"
    echo "Install Docker and run this script again if you need Docker Compose monitoring"
fi

# Navigate to plugin directory
cd "$PLUGIN_DIR" || {
    echo "ERROR: Cannot access plugin directory: $PLUGIN_DIR"
    exit 1
}

# Remove existing virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf .venv
fi

# Set initial permissions for the plugin directory
echo "Setting initial permissions..."
chown -R "$NAGIOS_USER:$NAGIOS_USER" "$PLUGIN_DIR"
chmod -R u+rwX,g+rX,o+rX "$PLUGIN_DIR"

# Create virtual environment as nagios user
echo "Creating virtual environment..."
sudo -u "$NAGIOS_USER" "$UV_PATH" venv .venv

# Install dependencies
echo "Installing Python dependencies..."
if ! sudo -u "$NAGIOS_USER" "$UV_PATH" pip install -e .; then
    echo "ERROR: Failed to install Python dependencies."
    echo "This might be due to network connectivity issues."
    echo "Try the following troubleshooting steps:"
    echo "   1. Check internet connectivity: ping pypi.org"
    echo "   2. Check DNS resolution: nslookup pypi.org"
    echo "   3. Retry the installation: bash install.sh"
    echo "   4. Manual installation: sudo -u nagios $UV_PATH pip install -e ."
    exit 1
fi

# Set ownership of entire directory to nagios user
echo "Setting ownership to '$NAGIOS_USER' user..."
chown -R "$NAGIOS_USER:$NAGIOS_USER" "$PLUGIN_DIR"

echo ""
echo "Installation complete!"
echo ""
echo "Testing plugins..."

# Test each plugin
all_tests_passed=true
for script in check_p110 check_jetdirect check_goss check_gmodem2 check_compose check_eap772 check_kindle check_smart check_lm_sensors check_space_usage check_lpr; do
    if [[ -f "$PLUGIN_DIR/$script" ]]; then
        echo -n "  Testing $script: "
        if sudo -u "$NAGIOS_USER" "$PLUGIN_DIR/$script" --help >/dev/null 2>&1; then
            echo "OK"
        else
            echo "FAILED"
            all_tests_passed=false
        fi
    fi
done

echo ""

if $all_tests_passed; then
    echo "All plugins are working correctly!"
    echo ""
    echo "Next steps:"
    echo "  1. Configure Nagios/Icinga commands using plugin paths"
    echo "  2. For plugin documentation, see README-CHECKS.md"
    echo ""
    echo "Manual test commands:"
    echo "  sudo -u nagios $PLUGIN_DIR/check_gmodem2 --help"
    echo "  sudo -u nagios $PLUGIN_DIR/check_p110 --help"
    echo "  sudo -u nagios $PLUGIN_DIR/check_jetdirect --help"
    echo "  sudo -u nagios $PLUGIN_DIR/check_goss --help"
    echo "  sudo -u nagios $PLUGIN_DIR/check_compose --help"
    echo "  sudo -u nagios $PLUGIN_DIR/check_eap772 --help"
    echo "  sudo -u nagios $PLUGIN_DIR/check_kindle --help"
    echo "  sudo -u nagios $PLUGIN_DIR/check_smart --help"
    echo "  sudo -u nagios $PLUGIN_DIR/check_lm_sensors --help"
    echo "  sudo -u nagios $PLUGIN_DIR/check_space_usage --help"
    echo "  sudo -u nagios $PLUGIN_DIR/check_lpr --help"
else
    echo "WARNING: Some plugins failed testing. Check permissions and dependencies."
    echo "Debug with: sudo -u $NAGIOS_USER $PLUGIN_DIR/check_<plugin> --help"
fi

echo ""
echo "For detailed plugin usage, see: $PLUGIN_DIR/README-CHECKS.md"
