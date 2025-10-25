## check_gmodem 2
Check for Glasfasermodem 2 from Telekom

```
(nagios-plugins-lukas) root@mini-lenovo:/opt/nagios-plugins-lukas# python3 check_gmodem2 -H 192.168.100.1
OK - FW: 090144.1.0.009 - Link: 1000 - PLOAM: OK - RX: -14.1dBm TX: 2.5dBm | rx_power=-14.07dBm;; tx_power=2.52dBm tx_packets=268340125c rx_packets=53718213c rx_dropped=0c rx_errors=0c tx_bytes=357863307339B rx_bytes=15334274500B
```

## check_p110 
Check for Tapo P110 Switchable Sockets
Sources: https://github.com/mihai-dinculescu/tapo https://github.com/fishbigger/TapoP100

```
(nagios-plugins-lukas) root@mini-lenovo:/opt/nagios-plugins-lukas# python3 check_p110 -H 10.10.10.138 -u "emailaddress@mail.com" -p "Password" 
OK - P05 Mediaserver : Device: ON - Power: 24.7W | signal_level=2;2;1 rssi=-57dBm power=24.664W;; energy_today=482Wh energy_month=12169Wh
```