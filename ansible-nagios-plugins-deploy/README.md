# Nagios Plugins Ansible Deployment

This directory contains an Ansible role and playbook to deploy the official Nagios plugins from GitHub.

## Overview

The `deploy-nagios-checks` automates the process of:
1. Installing build dependencies (git, m4, gettext, automake, autoconf, gcc, make, etc.)
2. Cloning the nagios-plugins repository from https://github.com/nagios-plugins/nagios-plugins.git
3. Checking out the specified release tag (default: `release-2.4.12`)
4. Running `./tools/setup` to initialize the build system
5. Configuring with `./configure --prefix=/opt/monitoring-nagios-git-2.4.12`
6. Compiling the plugins
7. Installing to the target directory
8. Installing setuid plugins

## Quick Start

### 1. Configure Inventory

Edit `inventory.ini` to add your target hosts:

```ini
[monitoring_servers]
myserver ansible_host=192.168.1.100

[monitoring_servers:vars]
ansible_user=your_user
ansible_become=true
```

### 2. Run the Playbook

```bash
# Deploy to all hosts in inventory
ansible-playbook -i inventory.ini playbook.yml

# Deploy to specific host
ansible-playbook -i inventory.ini playbook.yml --limit myserver

# Dry run (check mode)
ansible-playbook -i inventory.ini playbook.yml --check

# Verbose output
ansible-playbook -i inventory.ini playbook.yml -vv
```

### 3. Verify Installation

After deployment, the plugins will be available at:
```bash
/opt/monitoring-nagios-git-2.4.12/libexec/
```

Test a plugin:
```bash
/opt/monitoring-nagios-git-2.4.12/libexec/check_http --help
/opt/monitoring-nagios-git-2.4.12/libexec/check_ping --help
```

## Configuration

### Default Variables

See `deploy-nagios-checks/defaults/main.yml` for all configurable options:

- `nagios_plugins_version`: Git tag/branch to checkout (default: `release-2.4.12`)
- `nagios_plugins_install_prefix`: Installation directory (default: `/opt/monitoring-nagios-git-2.4.12`)
- `nagios_plugins_cgi_url`: CGI URL for configure script (default: `/nagios/cgi-bin`)
- `nagios_plugins_build_dir`: Temporary build directory (default: `/tmp/nagios-plugins-build`)

### Custom Installation

Override variables in your playbook:

```yaml
---
- name: Deploy Nagios Plugins
  hosts: monitoring_servers
  become: true
  
  vars:
    nagios_plugins_version: "release-2.4.11"
    nagios_plugins_install_prefix: "/usr/local/nagios-plugins"
  
  roles:
    - deploy-nagios-checks
```

Or in inventory:

```ini
[monitoring_servers:vars]
nagios_plugins_version=release-2.4.11
nagios_plugins_install_prefix=/usr/local/nagios-plugins
```

## Requirements

- Ansible 2.9 or higher
- Target systems: RHEL/CentOS/Rocky/Alma/Fedora 7+, Ubuntu 20.04+, Debian 10+
- Root/sudo access on target hosts
- Internet connectivity to clone from GitHub

## Directory Structure

```
ansible-nagios-plugins-deploy/
├── deploy-nagios-checks/
│   ├── README.md              # Role documentation
│   ├── defaults/
│   │   └── main.yml          # Default variables
│   ├── tasks/
│   │   └── main.yml          # Main tasks
│   ├── handlers/
│   │   └── main.yml          # Handlers
│   ├── meta/
│   │   └── main.yml          # Role metadata
│   └── vars/
│       └── main.yml          # Additional variables
├── inventory.ini              # Example inventory
├── playbook.yml              # Main playbook
└── README.md                 # This file
```

## Troubleshooting

### Build Dependencies Missing

If the role fails during compilation, ensure all build dependencies are installed:

```bash
# RHEL/CentOS/Rocky/Alma/Fedora
sudo dnf install git m4 gettext automake autoconf gcc make openssl-devel perl perl-devel

# Ubuntu/Debian
sudo apt-get install git m4 gettext automake autoconf gcc make libssl-dev perl
```

### Permission Denied

Ensure you're running with `become: true` or using `--become` flag:

```bash
ansible-playbook -i inventory.ini playbook.yml --become --ask-become-pass
```

### Custom Configure Options

To add additional configure options, modify `deploy-nagios-checks/tasks/main.yml`:

```yaml
- name: Run configure script
  ansible.builtin.command:
    cmd: >
      ./configure
      --prefix={{ nagios_plugins_install_prefix }}
      --with-cgiurl={{ nagios_plugins_cgi_url }}
      --with-mysql
      --with-pgsql
    chdir: "{{ nagios_plugins_build_dir }}"
```

## Testing

Test the role with molecule (if available):

```bash
cd deploy-nagios-checks
molecule test
```

## License

MIT-0

## References

- Official Nagios Plugins: https://github.com/nagios-plugins/nagios-plugins
- Installation Guide: https://github.com/nagios-plugins/nagios-plugins/blob/master/INSTALLING
- Developer Guidelines: https://www.nagios-plugins.org/doc/guidelines.html
