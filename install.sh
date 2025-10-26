#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR=$SCRIPT_DIR
NAGIOS_USER="nagios"

echo "Setting up Nagios plugins for user: $NAGIOS_USER"
echo "Plugin directory: $PLUGIN_DIR"

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
else
    echo "NOTE: Not running as root - skipping goss binary installation"
    echo "      Run 'sudo ./install.sh' if you need goss installed"
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
        usermod -aG docker "$NAGIOS_USER"
        echo "Added '$NAGIOS_USER' to docker group for Docker Compose monitoring"
        echo "NOTE: You may need to restart Nagios/Icinga service for group changes to take effect"
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
for script in check_p110 check_jetdirect check_goss check_gmodem2 check_compose; do
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
    echo "  2. For Docker monitoring, see DOCKER-SETUP.md"
    echo "  3. For plugin documentation, see README-CHECKS.md"
    echo ""
    echo "Manual test commands:"
    echo "  sudo -u nagios $PLUGIN_DIR/check_gmodem2 --help"
    echo "  sudo -u nagios $PLUGIN_DIR/check_p110 --help"
    echo "  sudo -u nagios $PLUGIN_DIR/check_jetdirect --help"
    echo "  sudo -u nagios $PLUGIN_DIR/check_goss --help"
    echo "  sudo -u nagios $PLUGIN_DIR/check_compose --help"
else
    echo "WARNING: Some plugins failed testing. Check permissions and dependencies."
    echo "Debug with: sudo -u $NAGIOS_USER $PLUGIN_DIR/check_<plugin> --help"
fi

echo ""
echo "For detailed plugin usage, see: $PLUGIN_DIR/README-CHECKS.md"
