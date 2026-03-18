# ESP32 Troubleshooting Reference

## Flash / Connection Failures

### "Failed to connect to ESP32-S3: No serial data received"

**Cause:** Device is not in bootloader/download mode.

**Fix:**
1. Hold `BOOT` button
2. Press and release `RESET` button
3. Release `BOOT` button
4. Immediately run flash command (within ~10 seconds)

Note: The port number often changes when entering bootloader mode. Run `ls /dev/cu.*` after the button sequence to confirm the current port before flashing.

---

### "could not open port: No such file or directory"

**Cause:** Port number changed after entering bootloader mode (normal behavior for USB-JTAG devices).

**Fix:** Run `ls /dev/cu.*` and use the new port number.

---

### "No bootable app partitions in the partition table" (boot loop)

**Cause:** App binary was flashed to wrong address (`0x10000` instead of `0x20000`). This project uses OTA partition layout.

**Fix:** Reflash with correct address:
```bash
python -m esptool --chip esp32s3 --port PORT --baud 460800 \
  write-flash --flash-mode dio --flash-size 8MB --flash-freq 80m \
  0x0     firmware/esp32-csi-node/build/bootloader/bootloader.bin \
  0x8000  firmware/esp32-csi-node/build/partition_table/partition-table.bin \
  0xf000  firmware/esp32-csi-node/build/ota_data_initial.bin \
  0x20000 firmware/esp32-csi-node/build/esp32-csi-node.bin
```

---

### No serial port visible after plugging in

**macOS:** Install CP210x driver from https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
- After install: System Settings → Privacy & Security → allow the driver
- Replug USB after driver installation

**Check driver is loaded:**
```bash
kextstat | grep -i silabs
```

---

## WiFi / Network Issues

### WiFi won't connect after provisioning

1. Re-run provision.py with correct credentials
2. Verify SSID spelling (case-sensitive)
3. Check the ESP32 supports the WiFi band (2.4 GHz only for CSI)
4. Monitor serial output to see connection attempt messages

### No UDP frames received by server

1. Confirm `--target-ip` matches Mac's actual LAN IP: `ipconfig getifaddr en0`
2. Check firewall allows inbound UDP on port 5005:
   ```bash
   # macOS — System Settings → Firewall, or:
   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/bin/python3
   ```
3. Verify ESP32 and Mac are on the same WiFi network
4. Check server is listening: `lsof -i UDP:5005`

---

## Server Issues

### Port already in use

```bash
# Find what's using port 3000
lsof -ti :3000
# Kill it
kill $(lsof -ti :3000)
# Or just use a different port
cargo run -p wifi-densepose-sensing-server -- --http-port 3001 --source auto
```

### `cargo` not found

```bash
# Use full path
~/.cargo/bin/cargo run -p wifi-densepose-sensing-server -- --http-port 3001 --source auto
```

### Server starts but no CSI data

1. Check `--source auto` detected ESP32: look for `ESP32 CSI detected on UDP :5005` in logs
2. Confirm ESP32 serial output shows `CSI streaming active -> IP:5005`
3. Verify IPs match — ESP32's target-ip must equal the Mac's IP

---

## Build Issues

### Docker build fails on Windows

Must use Docker — `idf.py` does not work from Git Bash/MSYS2.
Prefix command with `MSYS_NO_PATHCONV=1` to prevent path mangling.

### `idf.py` or `idf_component_manager` errors

Clean the build directory and retry:
```bash
docker run --rm \
  -v "$(pwd)/firmware/esp32-csi-node:/project" -w /project \
  espressif/idf:v5.2 bash -c \
  "rm -rf build sdkconfig managed_components && idf.py set-target esp32s3 && idf.py build"
```
