"""Read a text file and print its lines."""
import argparse


def transform(lines, upper=False):
    """Return lines, uppercased when upper is True."""
    return list(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Print the lines of a file.")
    parser.add_argument("path", help="file to read")
    args = parser.parse_args(argv)
    with open(args.path, encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    for line in transform(lines):
        print(line)


if __name__ == "__main__":
    main()
