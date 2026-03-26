#!/usr/bin/env python3
"""Soraya GB — ROM builder (no external dependencies)
Produces a valid 32KB Game Boy ROM with minimal init code and Soraya sprite.
"""
import struct, base64

ROM_SIZE = 32768
rom = bytearray([0xFF] * ROM_SIZE)

# ─── Nintendo logo ($0104–$0133, 48 bytes) ───────────────────────────────────
NINTENDO_LOGO = bytes([
    0xCE, 0xED, 0x66, 0x66, 0xCC, 0x0D, 0x00, 0x0B,
    0x03, 0x73, 0x00, 0x83, 0x00, 0x0C, 0x00, 0x0D,
    0x00, 0x08, 0x11, 0x1F, 0x88, 0x89, 0x00, 0x0E,
    0xDC, 0xCC, 0x6E, 0xE6, 0xDD, 0xDD, 0xD9, 0x99,
    0xBB, 0xBB, 0x67, 0x63, 0x6E, 0x0E, 0xEC, 0xCC,
    0xDD, 0xDC, 0x99, 0x9F, 0xBB, 0xB9, 0x33, 0x3E,
])
assert len(NINTENDO_LOGO) == 48
rom[0x0104:0x0134] = NINTENDO_LOGO

# ─── Header ($0134–$014C) ────────────────────────────────────────────────────
title = b'SORAYA GB'
rom[0x0134:0x0134 + len(title)] = title
rom[0x0143] = 0x00   # CGB flag: DMG only
rom[0x0146] = 0x00   # SGB flag: none
rom[0x0147] = 0x00   # Cartridge type: ROM only, no MBC
rom[0x0148] = 0x00   # ROM size: 32KB (2 banks)
rom[0x0149] = 0x00   # RAM size: none
rom[0x014A] = 0x01   # Destination: non-Japanese
rom[0x014B] = 0x33   # Old licensee: use new licensee
rom[0x014C] = 0x00   # Mask ROM version: 1.0

# ─── Entry point ($0100–$0103): NOP; JP $0150 ────────────────────────────────
rom[0x0100] = 0x00        # NOP
rom[0x0101] = 0xC3        # JP nn
rom[0x0102] = 0x50        # low  byte → $0150
rom[0x0103] = 0x01        # high byte → $0150

# ─── Init code at $0150 ──────────────────────────────────────────────────────
code = bytes([
    0xF3,              # DI
    0x31, 0xFE, 0xFF,  # LD SP, $FFFE
    0x3E, 0xE4,        # LD A, $E4  (BGP: 11=black 10=dark 01=light 00=white)
    0xEA, 0x47, 0xFF,  # LD ($FF47), A  — write BGP
    0x3E, 0x91,        # LD A, $91  (LCDC: LCD on, tile $8000, map $9800, BG on)
    0xEA, 0x40, 0xFF,  # LD ($FF40), A  — write LCDC
    0x76,              # HALT
    0x18, 0xFE,        # JR $-2  (infinite loop)
])
rom[0x0150:0x0150 + len(code)] = code

# ─── Sprite tile data at $0200 (2bpp, 4 tiles = 64 bytes) ───────────────────
# Palette: W=0 transparent/white, O=1 light, P=1 pink→light, D=2 dark, B=3 black
COLOR = {'W': 0, 'O': 1, 'P': 1, 'D': 2, 'B': 3}

SPRITE = [
    "WWWWWWWWWWWWWWWW",  # 0  transparent
    "WWBBWWWWWWBBWWWW",  # 1  ear tips
    "WBOOBWWWWBOOBWWW",  # 2  ears
    "WBOOBWWWWBOOBWWW",  # 3  ears
    "WBBBBBBBBBBBBWWW",  # 4  head outline
    "WBOOOOOOOOOOBWWW",  # 5  forehead
    "WBOOBWWWWBOOBWWW",  # 6  eyes
    "WBOOOOOOOOOOBWWW",  # 7
    "WBOOOOOOOOOOBWWW",  # 8
    "WBOOOOOOPOOOBWWW",  # 9  pink nose at (col=8, row=9)
    "WBOOOOOOOOOOBWWW",  # 10
    "WBBOOOOOOBBDWWWW",  # 11 chin + dark shadow
    "WWBOOOOOOBWWWWWW",  # 12 body
    "WWWBOOOOBWWWWWWW",  # 13 body taper
    "WWWWBBBBBWWWWWWW",  # 14 feet
    "WWWWWWWWWWWWWWWW",  # 15 transparent
]

# Verify
for i, row in enumerate(SPRITE):
    assert len(row) == 16, f"Row {i}: {len(row)} chars"

def pixels_to_2bpp_tiles(px):
    """16×16 pixel grid → 4 GB 2bpp tiles (64 bytes), row-major order."""
    tiles = bytearray()
    for tile_row in range(2):       # 0=top half, 1=bottom half
        for tile_col in range(2):   # 0=left half, 1=right half
            for row in range(8):
                y = tile_row * 8 + row
                lo = hi = 0
                for col in range(8):
                    x = tile_col * 8 + col
                    v = COLOR[px[y][x]]
                    bit = 7 - col  # MSB = leftmost pixel
                    lo |= (v & 1)       << bit
                    hi |= ((v >> 1) & 1) << bit
                tiles.append(lo)
                tiles.append(hi)
    assert len(tiles) == 64
    return tiles

rom[0x0200:0x0240] = pixels_to_2bpp_tiles(SPRITE)

# ─── Header checksum ($014D) — sum over $0134..$014C ─────────────────────────

chk = 0
for addr in range(0x0134, 0x014D):
    chk = (chk - rom[addr] - 1) & 0xFF
rom[0x014D] = chk

# ─── Global checksum ($014E–$014F, big-endian, not verified by hardware) ─────
gchk = (sum(rom) - rom[0x014E] - rom[0x014F]) & 0xFFFF
rom[0x014E] = (gchk >> 8) & 0xFF
rom[0x014F] = gchk & 0xFF

# ─── Write output ────────────────────────────────────────────────────────────
with open('/tmp/soraya.gb', 'wb') as f:
    f.write(rom)

b64 = base64.b64encode(bytes(rom)).decode()
with open('/tmp/soraya_rom_b64.txt', 'w') as f:
    f.write(b64)

# ─── Report ──────────────────────────────────────────────────────────────────
print(f"ROM: /tmp/soraya.gb")
print(f"Size: {len(rom)} bytes")
print(f"Header checksum $014D: 0x{rom[0x014D]:02X}")
print(f"Entry point: {' '.join(f'{b:02X}' for b in rom[0x0100:0x0104])}")
print(f"Title: {bytes(rom[0x0134:0x013F])!r}")
print(f"Nintendo logo $0104: {' '.join(f'{b:02X}' for b in rom[0x0104:0x010C])}")
print(f"BASE64_LEN: {len(b64)}")
