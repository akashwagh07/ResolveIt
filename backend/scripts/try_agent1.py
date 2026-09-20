"""Developer CLI to invoke Agent 1 locally with text and multimodal media."""

import argparse
import json
import sys

from ..app.agents.agent1 import Agent1Input, run_agent1
from ..app.llm import LLMError, MediaError


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Try Agent 1 (Civic Classification) with text and multimodal inputs."
    )
    parser.add_argument(
        "--text",
        action="append",
        help="Complaint text content (repeatable, joined with newlines).",
    )
    parser.add_argument(
        "--image",
        action="append",
        default=[],
        help="Path to image file (jpg, jpeg, png, webp; repeatable).",
    )
    parser.add_argument(
        "--audio",
        action="append",
        default=[],
        help="Path to audio file (mp3, wav, ogg, m4a, aac, flac, webm; repeatable).",
    )
    parser.add_argument(
        "--video",
        action="append",
        default=[],
        help="Path to video file (mp4, mov, webm; repeatable).",
    )
    parser.add_argument(
        "--lat",
        type=float,
        default=None,
        help="Optional latitude coordinate from GPS.",
    )
    parser.add_argument(
        "--lng",
        type=float,
        default=None,
        help="Optional longitude coordinate from GPS.",
    )
    parser.add_argument(
        "--address",
        type=str,
        default=None,
        help="Optional address or location text provided by user.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass LLM response cache.",
    )

    args = parser.parse_args()

    # Combine text inputs if provided
    combined_text = "\n".join(args.text) if args.text else None

    # Collect media paths
    all_media = []
    all_media.extend(args.image)
    all_media.extend(args.audio)
    all_media.extend(args.video)

    try:
        inp = Agent1Input(
            text=combined_text,
            latitude=args.lat,
            longitude=args.lng,
            address_text=args.address,
            media_paths=all_media,
        )
    except Exception as e:
        print(f"Input validation error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = run_agent1(inp, use_cache=not args.no_cache)
    except (MediaError, LLMError) as err:
        print(f"Execution failed: {err}", file=sys.stderr)
        sys.exit(1)

    # Print output as formatted JSON
    print(json.dumps(result.model_dump(), indent=2))
    print(f"\nModel Used: {result.model_used}")
    print(f"Cached: {result.cached}")
    print(f"Latency: {result.latency_ms:.1f} ms")


if __name__ == "__main__":
    main()
