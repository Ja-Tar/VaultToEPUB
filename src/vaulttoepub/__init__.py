import argparse
from .vtoepub import generate_epub
from pathlib import Path

def get_version():
    return "0.1.0"

def main(input_dir: str, f_to_one_file: bool = False, output_file: str | None = None):
    generate_epub(Path(input_dir), f_to_one_file, Path(output_file) if output_file else None)

parser = argparse.ArgumentParser(description="VaultToEPUB command line interface")
parser.add_argument("input_dir", type=str, help="Path to the input directory containing markdown files")
parser.add_argument("-f", "--folder_to_one_file", action="store_true", help="Option to turn lower folder with only .md to single file")
parser.add_argument("-o", "--output_file", type=str, nargs='?', default=None, help="Path to the output EPUB file")
parser.add_argument("-V", "--version", action="version", version=get_version())
args = parser.parse_args()
main(args.input_dir, args.folder_to_one_file, args.output_file)