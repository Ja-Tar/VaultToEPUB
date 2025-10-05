import argparse
from .vtoepub import generate_epub
from pathlib import Path

def get_version():
    return "0.1.0"

def main():
    parser = argparse.ArgumentParser(description="VaultToEPUB command line interface")
    parser.add_argument("input_dir", type=str, help="Path to the input directory containing markdown files")
    parser.add_argument("-k", "--keep_temp", action="store_true", help="Keep temporary files after EPUB generation (for debugging purposes)")
    parser.add_argument("-o", "--output_file", type=str, nargs='?', default=None, help="Path to the output EPUB file")
    parser.add_argument("-V", "--version", action="version", version=get_version())
    args = parser.parse_args()
    generate(args.input_dir, args.keep_temp, args.output_file)

def generate(input_dir: str, keep_temp: bool = False, output_file: str | None = None):
    generate_epub(Path(input_dir), keep_temp, Path(output_file) if output_file else None)