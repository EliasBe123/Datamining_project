"""Download the three public CNS files and verify Figshare's published checksums."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

API = "https://api.figshare.com/v2/articles/7267433/versions/1"
FILES = {"bt_symmetric.csv", "calls.csv", "sms.csv"}


def md5(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "md5").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/raw"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(API, timeout=60) as response:
        metadata = json.load(response)
    selected = [f for f in metadata["files"] if f["name"] in FILES]
    if {f["name"] for f in selected} != FILES:
        raise RuntimeError("Figshare is missing an expected file; inspect its metadata.")
    for entry in selected:
        destination = args.output / entry["name"]
        expected = entry["computed_md5"]
        if destination.exists():
            if md5(destination) != expected:
                raise RuntimeError(f"Existing {destination} differs from Figshare; move it before retrying.")
            print(f"Verified existing {destination}", flush=True)
            continue
        temporary = destination.with_suffix(".csv.part")
        print(f"Downloading {entry['name']} ({entry['size']:,} bytes)", flush=True)
        try:
            with urllib.request.urlopen(entry["download_url"], timeout=120) as source:
                with temporary.open("wb") as target:
                    shutil.copyfileobj(source, target)
            if md5(temporary) != expected:
                raise RuntimeError(f"Checksum mismatch for {entry['name']}")
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    (args.output / "figshare_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
