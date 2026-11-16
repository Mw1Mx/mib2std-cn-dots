"""Native NORMAL65 visual rule; call only after resolving the source project."""
from pathlib import Path
import json
import struct
import zlib

PROJECT = Path(__file__).resolve().parent
SUPPORTED = {"firmware": "MST2_EU_SE_ZR_P0516T", "variant": "cpu", "source_skin": "skin4"}

def crc(data):
    return zlib.crc32(data) & 0xffffffff

def read_mcf(raw):
    count = struct.unpack_from('<I', raw, 48)[0]
    end = 52 + count * 16
    if struct.unpack_from('<I', raw, 44)[0] != crc(raw[20:44]):
        raise ValueError('MCF header CRC mismatch')
    if struct.unpack_from('<I', raw, end)[0] != crc(raw[48:end]):
        raise ValueError('MCF table CRC mismatch')
    result = {}
    for i in range(count):
        tag, mid, offset, length = struct.unpack_from('<4sIII', raw, 52 + i * 16)
        if tag != b'IMG ' or mid in result or offset < end + 4:
            raise ValueError('Invalid MCF entry')
        blob = raw[offset:offset + length]
        if len(blob) != length or len(blob) < 40:
            raise ValueError('Incomplete MCF payload')
        if struct.unpack_from('<I', blob, 4)[0] != mid:
            raise ValueError('MCF payload ID mismatch')
        if struct.unpack_from('<I', blob, 24)[0] != crc(blob[:24]):
            raise ValueError('MCF image header CRC mismatch')
        if struct.unpack_from('<I', blob, len(blob)-4)[0] != crc(blob[28:-4]):
            raise ValueError('MCF image body CRC mismatch')
        result[mid] = blob
    return result

def apply_mcf(raw, *, firmware, variant, source_skin):
    identity = dict(firmware=firmware, variant=variant, source_skin=source_skin)
    rules = json.loads((PROJECT / 'visual_rules.json').read_text(encoding='utf8'))
    if identity != SUPPORTED or rules['profile'] != SUPPORTED:
        raise ValueError('Visual rule requires source project MST2_EU_SE_ZR_P0516T/cpu/skin4')
    entries = read_mcf(raw)
    original = dict(entries)
    protected = set(rules['protected_mcf_ids'])
    for rule in rules['image_copies']:
        src, dst = rule['source_mcf_id'], rule['destination_mcf_id']
        if src != rule['source_export_index']+1 or dst != rule['destination_export_index']+1:
            raise ValueError('Export index and MCF ID disagree')
        if dst in protected or src not in entries or dst not in entries:
            raise ValueError('Missing or protected image destination')
        if entries[src][28:36] != entries[dst][28:36]:
            raise ValueError('Image dimensions or format differ')
        blob = bytearray(entries[src])
        struct.pack_into('<I', blob, 4, dst)
        struct.pack_into('<I', blob, 24, crc(blob[:24]))
        entries[dst] = bytes(blob)
    if any(entries[mid] != original[mid] for mid in protected):
        raise ValueError('Protected SD notice changed')
    table = struct.pack('<I', len(entries))
    offset = 56 + 16 * len(entries)
    payloads = []
    for mid, blob in entries.items():
        table += struct.pack('<4sIII', b'IMG ', mid, offset, len(blob))
        offset += len(blob)
        payloads.append(blob)
    # Image count is unchanged, so the original header remains valid.
    result = raw[:48] + table + struct.pack('<I', crc(table)) + b''.join(payloads)
    if read_mcf(result) != entries:
        raise ValueError('Rebuilt MCF validation failed')
    return result
