# src/docgen/cli.py
#
# Command-line interface for the documentation generator.

import argparse
from .core import generate_documentation, DEFAULT_MODEL_NAME


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate internal documentation from a project JSON using a local DeepSeek model (Ollama)."
    )
    parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to the project JSON configuration file.",
    )
    parser.add_argument(
        "--model",
        "-m",
        default=DEFAULT_MODEL_NAME,
        help=f"Ollama model name to use (default: {DEFAULT_MODEL_NAME}).",
    )
    parser.add_argument(
        "--out",
        "-o",
        default=None,
        help=(
            "Output Markdown file path. If not provided, a name will be "
            "generated based on the project_name inside the JSON."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print(f"Using model: {args.model}")
    print(f"Config file: {args.config}")

    if args.out is not None:
        print(f"Output file (requested): {args.out}")
    else:
        print("Output file: will be derived from project_name under 'reports/'")

    print("\nGenerating documentation...\n")

    output_path = generate_documentation(
        config_path=args.config,
        model_name=args.model,
        out_path=args.out,
    )

    print("Done. Markdown documentation saved to:")
    print(output_path)
