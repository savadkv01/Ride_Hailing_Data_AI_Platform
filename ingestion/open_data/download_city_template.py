from pathlib import Path
import argparse
import requests


def download_file(input_url: str, output_file: Path, timeout_sec: int) -> Path:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(input_url, timeout=timeout_sec)
    response.raise_for_status()
    output_file.write_bytes(response.content)
    return output_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Template downloader for onboarding a new city open-data source.")
    parser.add_argument("--input-url", required=True, help="Public URL for city dataset file or API export endpoint.")
    parser.add_argument("--output-file", required=True, help="Destination file path under lakehouse/bronze/open/<city>/")
    parser.add_argument("--timeout-sec", type=int, default=180)
    args = parser.parse_args()

    path = download_file(args.input_url, Path(args.output_file), args.timeout_sec)
    print(f"Downloaded: {path}")


if __name__ == "__main__":
    main()
