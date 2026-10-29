
from pathlib import Path


RAW_DIR = Path("data/raw/sd_initial/DATALOG")

FILES = [
    "20261021/20261021_204456_BRP.edf",
    "20261021/20261021_204608_BRP.edf",
    "20261020/20261020_214934_BRP.edf",
]


def read_number(data):
    return int(data.decode("ascii").strip())


def check_file(file_path):
    raw = file_path.read_bytes()

    header_size = read_number(raw[184:192])
    record_count = read_number(raw[236:244])
    record_duration = float(
        raw[244:252].decode("ascii").strip()
    )
    signal_count = read_number(raw[252:256])

    # EDF: samples per data record
    samples_offset = 256 + signal_count * 216

    samples = [
        read_number(
            raw[
                samples_offset + i * 8:
                samples_offset + (i + 1) * 8
            ]
        )
        for i in range(signal_count)
    ]

    record_size = sum(samples) * 2
    data_size = len(raw) - header_size

    full_records, remainder = divmod(
        data_size, record_size
    )

    print(f"\nFail: {file_path.name}")
    print(f"Faili suurus: {len(raw)} baiti")
    print(f"Päise kirjeid: {record_count}")
    print(f"Näite kirje kohta: {samples}")
    print(f"Ühe kirje suurus: {record_size} baiti")
    print(f"Täielikke kirjeid: {full_records}")
    print(f"Ülejäänud baite: {remainder}")
    print(
        f"Arvutatud kestus: "
        f"{full_records * record_duration / 60:.1f} min"
    )


for name in FILES:
    check_file(RAW_DIR / name)
