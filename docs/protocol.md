# AMG65 USB Protocol Notes

These notes are the result of static analysis of the official Windows driver
`LEOBOG AMG65 Driver 1.0.3.3` and live testing on macOS. They are not an
official specification.

## Device

| Item | Value |
|---|---|
| USB vendor / product | `0x0C45` / `0x800A` |
| Command interface | USB interface 2, HID usage page `0xFF68`, usage `0x61` |
| Data interface | USB interface 3, HID usage page `0xFF67`, usage `0x61` |
| Configuration mode | Wired USB only; Bluetooth does not expose these interfaces |

Command writes are a leading zero report ID followed by a 64-byte payload.
The first payload byte is the command category, the second is the subcommand,
and byte 31 can carry a checksum. Responses echo the request bytes and use
byte 3 as status: `0x01` means accepted and `0xFF` means busy or retry.

The data interface has a 4096-byte interrupt OUT endpoint. On macOS it does
not receive a HID driver, so the implementation claims interface 3 through
libusb and writes 4096-byte blocks.

## Small LCD

The small LCD is 240 x 135 pixels with RGB565 little-endian pixels. A frame
is 64,800 bytes; the driver accepts up to 130 frames.

Upload sequence:

```text
04 18                                  start
04 72 [brightness@2] [block count@8..9] prepare
n x 4096-byte blocks                    data, one ACK per block
04 02                                  commit
```

The upload header starts with the frame count, followed by one delay byte
per frame. The delay byte is `max(1, milliseconds / 2)`, padded with zeros to
256 bytes. All RGB565 frames follow the header.

## LED matrix

The long strip contains 63 columns x 5 rows, for 315 LEDs and 945 color bytes
per frame. Pixels are reordered through `tool/key_pos.json` before transfer:

```python
output[key_pos[led]] = logical_frame[led]
```

### Persistent animation: `04 33`

`04 33` writes animation slot 6 in SPI flash. The firmware loops that slot
indefinitely, and the setting survives power loss. The driver limit is 260
frames.

```text
04 18
04 33 [block count@8..9]
n x 4096-byte blocks
04 02
04 F0                                  persist settings
```

Frame data layout:

```text
[frame count u16] [speed u16] [945-byte frame] x n [00] [AA 55]
```

The firmware at `0x6b6c` computes a period from the speed field as
`(speed * 5) & 0xFF` ticks. The implementation uses a 1 ms tick estimate and
repeats frames for delays above 255 ms.

`04 31` uses the same layout but targets the boot animation at flash
`0xEB0000`, which plays once. It is not a persistent slot.

### Live frame: `04 35`

`04 35` writes directly to display memory without touching flash. It pauses
the normal animation for roughly 2.5 seconds, so clients should resend about
once per second. The data is 945 LED bytes followed by `00 AA 55`; the
firmware reads only the first 945 bytes.

```text
04 18
04 35 [packet count@8]                 packet count = 15
15 x 64-byte command-channel packets
04 02
```

Do not send `04 F0` for a live frame.

### Other matrix commands

| Command | Purpose |
|---|---|
| `04 F0` | Save current settings to flash (`0xdd6a`), not a render command |
| `04 28` | Status request; response byte 12 is CPU, 13 GPU, 14..15 network |
| `04 17` | Brightness / sleep settings; byte 6 sleep light, byte 7 LED brightness |
| `04 18` | Start a command transaction |
| `04 02` | Commit a transaction |

## Small-screen time and status

Wired time synchronization uses the command channel:

```text
04 18
04 28 (payload byte 8 = 1)
00 01 5A year month day hour minute second 00 weekday ... AA 55
04 02
```

The older `0C 10` packet belongs to the wireless path and is rejected by the
wired firmware.

## Preset effects

The Christmas, aurora, game, rainbow, and Tetris animations are not stored
in firmware. The Windows driver reads them from the SQLite database
`db/ledlayer_v2.data`, table `t_default_led_frames`, then uploads generated
frames through `04 33`.

That vendor database is not included in this repository. Set
`AMG65_PRESET_DB` to a local copy extracted from the official driver to
enable these presets. All other controls work without it.

## Research scripts

`re_scripts/` contains the original one-off analysis helpers. They expect a
local driver extraction in `vendor/app/` by default; override it with
`AMG65_DRIVER_DIR`. Install their optional dependencies with
`pip install -r requirements-re.txt`.

