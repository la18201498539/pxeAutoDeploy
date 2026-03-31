import re
import subprocess


def get_interfaces() -> dict:
    """Return {interface_name: ip_address} for all non-loopback interfaces."""
    try:
        result = subprocess.run(
            ["ip", "-o", "addr", "show"],
            capture_output=True, text=True, check=True
        )
        interfaces = {}
        for line in result.stdout.splitlines():
            match = re.search(r'\d+:\s+(\S+)\s+inet\s+([\d.]+)/', line)
            if match:
                iface = match.group(1)
                ip = match.group(2)
                if iface != "lo":
                    interfaces[iface] = ip
        return interfaces
    except Exception:
        return {}


def get_disks() -> list:
    """Return list of disk device paths, e.g. ['/dev/sda', '/dev/vda']."""
    try:
        result = subprocess.run(
            ["lsblk", "-d", "-n", "-o", "NAME,SIZE,TYPE"],
            capture_output=True, text=True, check=True
        )
        disks = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[2] == "disk":
                disks.append(f"/dev/{parts[0]}")
        return disks if disks else ["/dev/sda"]
    except Exception:
        return ["/dev/sda"]
