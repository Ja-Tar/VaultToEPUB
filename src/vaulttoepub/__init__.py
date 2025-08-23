import argparse

def get_version():
    return "0.1.0"

def main():
    pass

parser = argparse.ArgumentParser(description="VaultToEPUB command line interface")
parser.add_argument("--version", action="version", version=get_version())
args = parser.parse_args()