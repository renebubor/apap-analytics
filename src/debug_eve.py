
from pathlib import Path

file_path = Path(
    "data/raw/sd_initial/DATALOG/20261020/"
    "20261020_214926_EVE.edf"
)

raw = file_path.read_bytes()

header_size = int(raw[184:192].decode("ascii").strip())

# Eelmises kontrollis tuvastasime:
# 19 näidet annotatsioonikanalis, 1 CRC-kanalis.
annotation_bytes = 19 * 2
record_bytes = (19 + 1) * 2

print("EDF päise suurus:", header_size)
print("Faili tegelik suurus:", len(raw))

for i in range(3):
    start = header_size + i * record_bytes
    annotation_data = raw[start:start + annotation_bytes]

    print(f"\nKirje {i + 1}")
    print("Toorbaidid:", repr(annotation_data))
    print("Iga teine bait:", repr(annotation_data[::2]))
    print("Tekst:", repr(annotation_data[::2].decode("latin-1")))
