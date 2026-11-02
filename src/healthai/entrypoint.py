"""Dispatch raw conversion before importing AI or plotting dependencies."""
import argparse
import sys
import xml.etree.ElementTree as ET
import zipfile

from healthai import __version__


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "convert":
        parser = argparse.ArgumentParser(
            prog="healthai convert",
            description="Convert Apple Health XML/ZIP locally. No AI setup, uploads or telemetry.",
        )
        parser.add_argument("source", help="export.xml, export.zip, or an export directory")
        parser.add_argument("--format", choices=("csv", "json", "both"), default="csv")
        parser.add_argument("-o", "--out", default="health_export", help="New output directory (default: health_export)")
        parser.add_argument("--quiet", action="store_true", help="Hide progress; still report completion and warnings")
        args = parser.parse_args(sys.argv[2:])
        from healthai.exporter import convert_export

        def progress(message):
            if not args.quiet:
                print(message, file=sys.stderr, flush=True)

        try:
            report = convert_export(args.source, args.out, args.format, progress)
        except (OSError, ValueError, EOFError, ET.ParseError, zipfile.BadZipFile, RuntimeError) as error:
            print(f"Conversion failed: {error}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("Conversion cancelled; no output published.", file=sys.stderr)
            return 130
        print(f"Saved {sum(report['counts'].values()):,} rows to {args.out} in {report['elapsed_seconds']:.2f}s")
        for tag, count in report["counts"].items():
            print(f"  {tag}: {count:,}")
        if report["unsupported_top_level_elements"]:
            omitted = ", ".join(f"{tag}: {count}" for tag, count in report["unsupported_top_level_elements"].items())
            print(f"Warning: unsupported top-level elements were not exported ({omitted}).", file=sys.stderr)
        print("Details: export_report.json (local file only)")
        return 0
    if sys.argv[1:] == ["--version"]:
        print(f"healthai {__version__}")
        return 0
    from healthai.cli import main as interactive_main
    return interactive_main()
