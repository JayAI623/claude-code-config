---
name: ruview-esp32-setup
description: This skill should be used when the user asks to "set up ESP32", "flash ESP32 firmware", "connect ESP32 to RuView", "provision WiFi on ESP32", "set up a sensing node", "烧录固件", "设置ESP32节点", or wants to add a new ESP32-S3 hardware node to the WiFi-DensePose / RuView project.
version: 0.1.0
---

# RuView ESP32-S3 Node Setup

End-to-end procedure for flashing and connecting an ESP32-S3 sensing node to the RuView WiFi-DensePose system.

> **Supported hardware only:** ESP32-S3 (8 MB flash). Original ESP32 and ESP32-C3 are NOT supported — single-core, cannot run the CSI DSP pipeline.

---

## Prerequisites

Install required tools before starting:

```bash
# esptool for flashing
pip install esptool

# NVS partition generator for WiFi provisioning
pip install esp-idf-nvs-partition-gen

# Docker Desktop — required for cross-platform firmware build
# Download: https://www.docker.com/products/docker-desktop/
docker --version
```

---

## Step 1: Find the Serial Port

Plug in the ESP32-S3 via USB, then run:

```bash
ls /dev/cu.*
```

Expected results by port type:

| Port name | Meaning |
|-----------|---------|
| `/dev/cu.usbmodem*` | Built-in USB-JTAG (ESP32-S3 native, no driver needed) |
| `/dev/cu.SLAB_USBtoUART` | CP210x bridge chip (install driver if missing) |
| `/dev/cu.usbserial-*` | CH340/FTDI bridge |

If no port appears: install the [CP210x driver](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers), then replug.

---

## Step 2: Build Firmware (Docker)

Run from the **repository root** (`/path/to/RuView`):

```bash
docker run --rm \
  -v "$(pwd)/firmware/esp32-csi-node:/project" -w /project \
  espressif/idf:v5.2 bash -c \
  "rm -rf build sdkconfig && idf.py set-target esp32s3 && idf.py build"
```

- On Windows Git Bash, prefix with `MSYS_NO_PATHCONV=1`
- First run pulls the Docker image (~1 GB), takes 5–10 min
- Subsequent builds: ~2 min

**Build outputs** (all needed for flashing):
```
firmware/esp32-csi-node/build/bootloader/bootloader.bin
firmware/esp32-csi-node/build/partition_table/partition-table.bin
firmware/esp32-csi-node/build/ota_data_initial.bin
firmware/esp32-csi-node/build/esp32-csi-node.bin
```

Verify correct flash addresses from the build:
```bash
cat firmware/esp32-csi-node/build/flash_args
# Should show: 0x0, 0x8000, 0xf000, 0x20000
```

---

## Step 3: Enter Bootloader Mode

The ESP32-S3 must be in download/bootloader mode to accept a flash:

1. **Hold** the `BOOT` button (or `0` button)
2. **Press and release** the `RESET` button (or `EN` button)
3. **Release** the `BOOT` button

The serial port number may change when entering bootloader mode. Re-run `ls /dev/cu.*` to confirm the current port.

**Verification:**
```bash
python -m esptool --port /dev/cu.usbmodem1101 chip_id
# Success: "Chip is ESP32-S3"
# Failure: "Failed to connect" → repeat the button sequence
```

---

## Step 4: Flash Firmware

Replace `PORT` with the actual serial port:

```bash
python -m esptool --chip esp32s3 --port PORT --baud 460800 \
  write-flash --flash-mode dio --flash-size 8MB --flash-freq 80m \
  0x0     firmware/esp32-csi-node/build/bootloader/bootloader.bin \
  0x8000  firmware/esp32-csi-node/build/partition_table/partition-table.bin \
  0xf000  firmware/esp32-csi-node/build/ota_data_initial.bin \
  0x20000 firmware/esp32-csi-node/build/esp32-csi-node.bin
```

> **Critical:** Use `0x20000` for the app binary, NOT `0x10000`. The OTA partition table requires `0x20000`. Using the wrong address causes boot loop with `No bootable app partitions` error.

After flashing, the device auto-resets. The port number reverts to the original `usbmodem` address.

---

## Step 5: Provision WiFi

Configure WiFi credentials without reflashing — written to NVS (Non-Volatile Storage):

```bash
# Get the Mac's local IP (this becomes the aggregator target)
ipconfig getifaddr en0

python firmware/esp32-csi-node/provision.py \
  --port PORT \
  --ssid "YourWiFiSSID" \
  --password "YourWiFiPassword" \
  --target-ip 192.168.x.x   # Mac's IP from above
```

WiFi settings can be changed anytime by re-running `provision.py` — no reflash needed.

---

## Step 6: Verify Boot

Press RESET once (without BOOT) to boot normally, then read serial output:

```bash
python -c "
import serial, time
s = serial.Serial('/dev/tty.usbmodem1101', 115200, timeout=2)
deadline = time.time() + 12
while time.time() < deadline:
    data = s.read(512)
    if data:
        print(data.decode('utf-8', errors='replace'), end='', flush=True)
s.close()
"
```

**Expected output:**
```
I (321) main: ESP32-S3 CSI Node (ADR-018) -- Node ID: 1
I (345) main: WiFi STA initialized, connecting to SSID: YourWiFi
I (1023) main: Connected to WiFi
I (1025) main: CSI streaming active -> 192.168.x.x:5005
```

CSI frames arriving:
```
I (6702) csi_collector: CSI cb #200: len=128 rssi=-42 ch=1
```

---

## Step 7: Start Sensing Server

```bash
cd rust-port/wifi-densepose-rs
~/.cargo/bin/cargo run -p wifi-densepose-sensing-server -- --http-port 3001 --source auto
```

- Use `--http-port 3001` (or another port) if 3000 is occupied
- `--source auto` auto-detects the ESP32 CSI stream on UDP :5005

Open the UI:
```bash
open http://localhost:3001/ui/index.html
```

---

## Step 8: Verify Node Connection

> **Important:** `/api/v1/sensing/latest` returns only the most recently received frame — not all nodes at once. With multiple nodes each pushing ~20 Hz, each query hits a different node's frame. Sample over several seconds to see all active nodes.

```bash
# Sample 5 times over 5 seconds — all node_ids that appear are online
for i in 1 2 3 4 5; do
  curl -s http://localhost:3001/api/v1/sensing/latest | python -c \
    "import json,sys; d=json.load(sys.stdin); [print(f'node_id={n.get(\"node_id\")}') for n in d.get('nodes',[])]"
  sleep 1
done
```

Expected output with 3 nodes online:
```
node_id=1
node_id=3
node_id=2
node_id=1
node_id=3
```

---

## Troubleshooting

See `references/troubleshooting.md` for detailed solutions. Common issues:

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Failed to connect` on flash | Not in bootloader mode | Repeat BOOT+RESET sequence |
| Port changes after BOOT+RESET | Normal behavior | Re-run `ls /dev/cu.*` |
| `No bootable app partitions` boot loop | Wrong flash address (0x10000) | Reflash with `0x20000` for app |
| No port visible | Missing driver | Install CP210x driver |
| `No serial data received` | Wrong port or not in bootloader mode | Check port and retry |
| WiFi won't connect | Wrong SSID/password | Re-run `provision.py` |
| No UDP frames on server | Firewall or wrong target-ip | Check IP and firewall UDP 5005 |
| Port busy on server start | Another app on port 3000 | Use `--http-port 3001` |

---

## Additional Resources

- **`references/troubleshooting.md`** — Detailed troubleshooting for all known failure modes
- **`references/nvs-keys.md`** — Full NVS configuration key reference (edge tiers, WASM, TDM mesh)
- Firmware source: `firmware/esp32-csi-node/README.md`
- Architecture decisions: `docs/adr/ADR-039-esp32-edge-intelligence.md`
