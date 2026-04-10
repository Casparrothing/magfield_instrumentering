# Connecting to EV3 via SSH

The EV3 runs [ev3dev](https://www.ev3dev.org/), a Debian-based Linux distribution. You connect to it over SSH to transfer files and run the server script.

## Requirements

- EV3 brick with ev3dev (brickman) installed and booted
- USB cable **or** WiFi/USB dongle connected to the same network as your PC
- SSH client (built into macOS/Linux; on Windows use PowerShell or [PuTTY](https://www.putty.org/))

---

## 1. Connect the EV3 to your PC

**Option A — USB cable (easiest)**
Plug a standard USB-A to Mini-B cable between the EV3 and your PC. ev3dev sets up a virtual network interface automatically. The EV3's IP over USB is always:
```
192.168.2.3
```

**Option B — WiFi**
Insert a compatible USB WiFi dongle, connect to your network via the brickman menu (`Wireless and Networks → Wi-Fi`), and note the IP shown on the EV3 display.

---

## 2. SSH into the EV3

```bash
ssh robot@192.168.2.3
```

Default credentials:
| Field | Value |
|-------|-------|
| Username | `robot` |
| Password | `maker` |

---

## 3. Transfer files to the EV3
In the SSH
```bash
nano server.py
```

Copy the contents from ev3dev_server.py
---

## 4. Run the server script

Once SSH'd in:

```bash
python3 server.py
```

The script listens on port 5000 for commands from the PC-side script (`ev3_arduino.py`).

To stop a running script:
```bash
pkill -9 -f server.py
```

If port 5000 is still in use after killing the script, free it with:
```bash
fuser -k 5000/tcp
```
