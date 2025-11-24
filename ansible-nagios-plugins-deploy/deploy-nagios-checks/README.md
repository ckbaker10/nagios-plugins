Nagios Plugins Deploy Role
==========================

This Ansible role clones, compiles, and installs the official Nagios plugins from the GitHub repository.

Requirements
------------

- Git must be available on the target system (installed by the role)
- Root/sudo access for installation
- Internet connectivity to clone the GitHub repository
- Supported OS: RHEL/CentOS/Rocky/Alma/Fedora 7+, Ubuntu 20.04+, Debian 10+

Role Variables
--------------

Available variables are listed below, along with default values (see `defaults/main.yml`):

```yaml
# Nagios plugins repository and version
nagios_plugins_repo: "https://github.com/nagios-plugins/nagios-plugins.git"
nagios_plugins_version: "release-2.4.12"

# Installation paths
nagios_plugins_install_prefix: "/opt/monitoring-nagios-git-2.4.12"
nagios_plugins_cgi_url: "/nagios/cgi-bin"

# Build directory (temporary)
nagios_plugins_build_dir: "/tmp/nagios-plugins-build"

# Required packages for building (automatically selected based on OS)
# For RHEL/Fedora: openssl-devel, perl-devel
# For Ubuntu/Debian: libssl-dev, libperl-dev
```

**Note:** The role automatically detects the OS family and installs the appropriate packages. No manual configuration needed for package names.

Dependencies
------------

None.

Example Playbook
----------------

Basic usage with default settings:

```yaml
- hosts: monitoring_servers
  become: true
  roles:
    - deploy-role
```

Custom installation path and version:

```yaml
- hosts: monitoring_servers
  become: true
  roles:
    - role: deploy-role
      nagios_plugins_version: "release-2.4.11"
      nagios_plugins_install_prefix: "/usr/local/nagios-plugins"
```

Using variables:

```yaml
- hosts: monitoring_servers
  vars:
    nagios_plugins_version: "release-2.4.12"
    nagios_plugins_install_prefix: "/opt/monitoring"
  become: true
  roles:
    - deploy-role
```

What This Role Does
-------------------

1. Installs required build dependencies (git, m4, gettext, automake, autoconf, gcc, make, etc.)
2. Clones the nagios-plugins repository from GitHub
3. Checks out the specified tag/version
4. Runs `./tools/setup` to initialize the build system
5. Runs `./configure` with specified prefix and CGI URL
6. Compiles the plugins using `make`
7. Installs the plugins to the specified directory
8. Installs setuid plugins (requires root)
9. Verifies the installation was successful

After Installation
------------------

The plugins will be installed to:
- `{{ nagios_plugins_install_prefix }}/libexec/` - Plugin executables

You can test a plugin with:
```bash
/opt/monitoring-nagios-git-2.4.12/libexec/check_http --help
```

License
-------

MIT-0

Author Information
------------------

Part of the nagios-plugins monitoring tools collection.
