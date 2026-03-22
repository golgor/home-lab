# Readme

## Installed applications

- Git
- TigerVNC
- Python 3
- RPi.GPIO (Python 3)
- SQLite
- MinIO
- CUPS
- K3s
- PostgreSQL

## NVME-boot
The following was added to /boot/firmware/config.txt on the boot partition before the first boot with DietPi:

```text
# Add to bottom of /boot/firmware/config.txt
dtparam=pciex1
```

https://www.jeffgeerling.com/blog/2023/nvme-ssd-boot-raspberry-pi-5/

## DietPi Init
The DietPi is initialized with `./dietpi.txt`. This file should be put in primary partition used to boot DietPi.
