"""Dispatch offline commands before importing AI or plotting dependencies."""
import argparse
import sys
import xml.etree.ElementTree as ET
import zipfile

from healthai import __version__


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "dashboard":
        return dashboard_main(sys.argv[2:])
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


def dashboard_main(argv):
    parser = argparse.ArgumentParser(
        prog="healthai dashboard",
        description="Create an offline HTML dashboard from Apple Health XML/ZIP. No AI setup or uploads.",
    )
    parser.add_argument("source", nargs="?", help="export.xml, export.zip, or an export directory")
    parser.add_argument("--demo", action="store_true", help="Use fictional sample data; no export or dependencies needed")
    parser.add_argument("--month", help="Report month YYYY-MM (default: latest month in the export)")
    from healthai.dashboard import TEMPLATES
    parser.add_argument("--template", choices=TEMPLATES, default="report", help="Visual layout (default: report); also switchable inside the HTML")
    parser.add_argument("--source", action="append", default=[], dest="sources", help="Include this device/app source only; repeat for multiple sources")
    parser.add_argument("-o", "--out", default="health-dashboard.html", help="New HTML file (default: health-dashboard.html)")
    parser.add_argument("--open", action="store_true", dest="open_browser", help="Open the finished file in your browser")
    parser.add_argument("--quiet", action="store_true", help="Hide progress")
    args = parser.parse_args(argv)
    if bool(args.source) == args.demo:
        parser.error("provide an export path OR --demo")
    if args.demo and args.sources:
        parser.error("--source applies to real exports, not --demo")
    from pathlib import Path
    from healthai.dashboard import build_dashboard_data, demo_data, parse_month, write_dashboard

    def progress(message):
        if not args.quiet:
            print(message, file=sys.stderr, flush=True)

    try:
        if args.month:
            parse_month(args.month)
        if Path(args.out).expanduser().exists():
            raise ValueError("Output already exists. Choose a new --out file to keep your previous report.")
        data = demo_data(args.month) if args.demo else build_dashboard_data(args.source, args.month, args.sources, progress)
        output = write_dashboard(data, args.out, args.template)
    except ModuleNotFoundError as error:
        print(f"Dashboard dependency missing: {error.name}. Install healthai's dependencies, then retry. The --demo command works without them.", file=sys.stderr)
        return 1
    except (OSError, ValueError, EOFError, ET.ParseError, zipfile.BadZipFile, RuntimeError) as error:
        print(f"Dashboard failed: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Dashboard cancelled.", file=sys.stderr)
        return 130
    print(f"Saved {'fictional demo' if data['demo'] else 'private dashboard'}: {output}")
    print(f"{data['month']} · data through {data['through']}")
    print(f"Open: {output.as_uri()}")
    for warning in data["warnings"]:
        print(f"Warning: {warning}", file=sys.stderr)
    if args.open_browser:
        import webbrowser
        try:
            if not webbrowser.open(output.as_uri()):
                print("Browser did not open automatically. Open the HTML file manually.", file=sys.stderr)
        except webbrowser.Error as error:
            print(f"Browser could not open: {error}. Open the HTML file manually.", file=sys.stderr)
    return 0
