import struct, zlib, os
os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'assets'), exist_ok=True)
base = os.path.join(os.path.dirname(__file__), '..', 'assets')

def png(w, h, rgba):
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    raw = b''.join(b'\x00' + bytes(rgba[y * w * 4:(y + 1) * w * 4]) for y in range(h))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')

def write_icon(name, rgb):
    w, h = 81, 81
    px = []
    for y in range(h):
        for x in range(w):
            if 18 <= x <= 62 and 18 <= y <= 62:
                px.extend(rgb + (255,))
            else:
                px.extend((255, 255, 255, 0))
    with open(os.path.join(base, name + '.png'), 'wb') as f:
        f.write(png(w, h, bytes(px)))

write_icon('tab-home', (153, 153, 153))
write_icon('tab-home-active', (7, 193, 96))
write_icon('tab-my', (153, 153, 153))
write_icon('tab-my-active', (7, 193, 96))
print('ok')
