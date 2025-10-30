# Nagios Plugins 2.4.12 - Icinga2 Import Summary

**Generated:** 2025-10-30  
**Source Repository:** nagios-plugins 2.4.12  
**Parsing Script:** `/opt/nagios-plugins-lukas/debug_files/parse_nagios_plugins.py`

## Overview

Automatically parsed nagios-plugins 2.4.12 source code repository to extract command-line options and generate Icinga2 CheckCommand definitions.

## Results

- **Total Files Processed:** 56 plugins (42 C, 14 Perl)
- **Successfully Parsed:** 51 plugins (91%)
- **Failed to Parse:** 5 plugins (9%)
- **Generated Config:** `commands-nagios-plugins-2.4.12.conf` (2,100 lines)

## Successfully Parsed Plugins

### C Plugins (37/42)
- check_apt
- check_by_ssh
- check_cluster
- check_dbi
- check_dig
- check_disk
- check_fping
- check_hpjd
- check_http
- check_ide_smart
- check_ldap
- check_load
- check_mrtg
- check_mrtgtraf
- check_mysql
- check_mysql_query
- check_nagios
- check_nt
- check_ntp
- check_ntp_peer
- check_ntp_time
- check_nwstat
- check_overcr
- check_pgsql
- check_ping
- check_procs
- check_radius
- check_real
- check_smtp
- check_snmp
- check_ssh
- check_swap
- check_tcp
- check_time
- check_ups
- check_uptime
- check_users

### Perl Plugins (14/14)
- check_breeze
- check_disk_smb
- check_file_age
- check_flexlm
- check_ifoperstatus
- check_ifstatus
- check_ircd
- check_mailq
- check_mssql
- check_netdns
- check_ntp
- check_rpc
- check_ssl_validity
- check_wave

## Failed Plugins (No longopts)

These 5 C plugins don't use the standard `getopt_long()` function:
- check_dhcp - Uses custom argument parsing
- check_icmp - Uses custom argument parsing
- check_dns - Uses custom argument parsing
- check_dummy - Minimal plugin, no arguments
- check_game - Uses custom argument parsing

## Parsing Methodology

### C Source Files
1. Extract `struct option longopts[]` array
2. Parse each option: `{"name", required_argument, 0, 'x'}`
3. Map to Icinga2 argument definitions
4. Attempted to extract descriptions from `print_help()` function

### Perl Scripts
1. Locate `GetOptions()` call
2. Parse option specs: `"w=s" => \$opt_w, "warning=s" => \$opt_w`
3. Group short/long options by variable name
4. Map argument types: `=s` (required), `:s` (optional), `!` (boolean)

## Installation

1. **Copy to Icinga Master:**
   ```bash
   scp commands-nagios-plugins-2.4.12.conf icinga-master:/etc/icinga2/conf.d/
   ```

2. **Verify Configuration:**
   ```bash
   icinga2 daemon -C
   ```

3. **Reload Icinga2:**
   ```bash
   systemctl reload icinga2
   ```

## Usage in Icinga Director

1. Navigate to Icinga Director → Commands → External Commands
2. Import commands from `/etc/icinga2/conf.d/commands-nagios-plugins-2.4.12.conf`
3. Or manually import via:
   ```bash
   icingacli director kickstart
   ```

## Variable Naming Convention

All Icinga2 custom variables follow the pattern:
```
$<plugin_name>_<option_name>$
```

Examples:
- `$check_mysql_hostname$` → `--hostname` option
- `$check_http_ssl$` → `--ssl` flag
- `$check_disk_warning$` → `--warning` threshold

## Command Structure

Each CheckCommand includes:
- **command:** Full path using `PluginDir + "/check_name"`
- **arguments:** Dictionary of all command-line options
  - Value arguments: `value = "$variable$"`
  - Boolean flags: `set_if = "$variable$"`

## Example CheckCommand

```
object CheckCommand "check_mysql" {
  command = [ PluginDir + "/check_mysql" ]

  arguments = {
    "--hostname" = {
      value = "$check_mysql_hostname$"
    }
    "--port" = {
      value = "$check_mysql_port$"
    }
    "--username" = {
      value = "$check_mysql_username$"
    }
    "--password" = {
      value = "$check_mysql_password$"
    }
    "--database" = {
      value = "$check_mysql_database$"
    }
    "--warning" = {
      value = "$check_mysql_warning$"
    }
    "--critical" = {
      value = "$check_mysql_critical$"
    }
    "--check-slave" = {
      set_if = "$check_mysql_check_slave$"
    }
    "--ssl" = {
      set_if = "$check_mysql_ssl$"
    }
  }
}
```

## Limitations

1. **Descriptions Missing:** Option descriptions were not reliably extracted from source
2. **Custom Parsing:** 5 plugins use custom argument parsing (not getopt_long)
3. **Shell Scripts:** Shell script plugins (2 files) were not parsed
4. **Default Values:** Plugin default values are not included
5. **Argument Dependencies:** Inter-option dependencies not captured

## Future Enhancements

1. Parse help output at runtime to extract descriptions
2. Add support for custom argument parsers
3. Include default values from source code
4. Add argument validation rules
5. Generate Icinga Director basket files

## Progress Tracking

All parsing progress is tracked in:
```
/opt/nagios-plugins-lukas/debug_files/parseprogress.txt
```

Format: `filename|status|timestamp|notes`

## Files

- **Parser Script:** `/opt/nagios-plugins-lukas/debug_files/parse_nagios_plugins.py`
- **Generated Config:** `/opt/nagios-plugins-lukas/icinga-custom-commands/commands-nagios-plugins-2.4.12.conf`
- **Progress Log:** `/opt/nagios-plugins-lukas/debug_files/parseprogress.txt`
- **Source Repository:** `/opt/nagios-plugins-lukas/debug_files/nagios-plugins/`

## Plugin Path Configuration

The generated commands use `PluginDir` which defaults to:
- Debian/Ubuntu: `/usr/lib/nagios/plugins`
- RHEL/CentOS: `/usr/lib64/nagios/plugins`
- Source Install: `/usr/local/nagios/libexec`

Adjust `PluginDir` in `/etc/icinga2/constants.conf` if needed.

## Testing

Test individual commands:
```bash
# Test check_mysql command
icinga2 object list --type CheckCommand --name check_mysql

# Test with parameters
/usr/lib/nagios/plugins/check_mysql --hostname localhost --username nagios --password secret
```

## Support

For issues with:
- **Parsing errors:** Check `/opt/nagios-plugins-lukas/debug_files/parseprogress.txt`
- **Missing options:** Review source file in `debug_files/nagios-plugins/`
- **Icinga2 config:** Run `icinga2 daemon -C` for validation
- **Plugin execution:** Test plugin directly from command line

## References

- Nagios Plugins: https://www.nagios-plugins.org/
- Icinga2 CheckCommand: https://icinga.com/docs/icinga-2/latest/doc/09-object-types/#checkcommand
- Icinga Director: https://icinga.com/docs/director/latest/
