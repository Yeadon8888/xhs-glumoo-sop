#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai>=1.0.0",
#     "pillow>=10.0.0",
# ]
# ///
"""
Generate images using Google's Nano Banana Pro (Gemini 3 Pro Image) API.

Usage:
    uv run generate_image.py --prompt "your image description" --filename "output.png" [--resolution 1K|2K|4K] [--api-key KEY]

Multi-image editing (up to 14 images):
    uv run generate_image.py --prompt "combine these images" --filename "output.png" -i img1.png -i img2.png -i img3.png
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

SUPPORTED_ASPECT_RATIOS = [
    "1:1",
    "2:3",
    "3:2",
    "3:4",
    "4:3",
    "4:5",
    "5:4",
    "9:16",
    "16:9",
    "21:9",
]


DEFAULT_MODEL = "gemini-3-pro-image-preview"
DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com"


def get_api_key(provided_key: str | None) -> str | None:
    """Get API key from argument first, then environment."""
    if provided_key:
        return provided_key
    return (
        os.environ.get("XHS_IMAGE_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
    )


def get_model_name(provided_model: str | None) -> str:
    return (
        provided_model
        or os.environ.get("XHS_IMAGE_MODEL")
        or os.environ.get("GEMINI_IMAGE_MODEL")
        or os.environ.get("GEMINI_MODEL")
        or DEFAULT_MODEL
    )


def get_base_url(provided_base_url: str | None) -> str:
    base_url = (
        provided_base_url
        or os.environ.get("XHS_IMAGE_BASE_URL")
        or os.environ.get("GEMINI_BASE_URL")
        or os.environ.get("GOOGLE_GENAI_BASE_URL")
        or DEFAULT_BASE_URL
    )
    return base_url.rstrip("/")


def build_auth_headers(api_key: str, base_url: str) -> dict:
    if "generativelanguage.googleapis.com" in base_url:
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        }
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }


def auto_detect_resolution(max_input_dim: int) -> str:
    """Infer output resolution from the largest input image dimension."""
    if max_input_dim >= 3000:
        return "4K"
    if max_input_dim >= 1500:
        return "2K"
    return "1K"


def choose_output_resolution(
    requested_resolution: str | None,
    max_input_dim: int,
    has_input_images: bool,
) -> tuple[str, bool]:
    """Choose final resolution and whether it was auto-detected.

    Auto-detection is only applied when the user did not pass --resolution.
    """
    if requested_resolution is not None:
        return requested_resolution, False

    if has_input_images and max_input_dim > 0:
        return auto_detect_resolution(max_input_dim), True

    return "1K", False


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using Nano Banana Pro (Gemini 3 Pro Image)"
    )
    parser.add_argument(
        "--prompt", "-p",
        required=True,
        help="Image description/prompt"
    )
    parser.add_argument(
        "--filename", "-f",
        required=True,
        help="Output filename (e.g., sunset-mountains.png)"
    )
    parser.add_argument(
        "--input-image", "-i",
        action="append",
        dest="input_images",
        metavar="IMAGE",
        help="Input image path(s) for editing/composition. Can be specified multiple times (up to 14 images)."
    )
    parser.add_argument(
        "--resolution", "-r",
        choices=["1K", "2K", "4K"],
        default=None,
        help="Output resolution: 1K, 2K, or 4K. If omitted with input images, auto-detect from largest image dimension."
    )
    parser.add_argument(
        "--aspect-ratio", "-a",
        choices=SUPPORTED_ASPECT_RATIOS,
        default=None,
        help=f"Output aspect ratio (default: model decides). Options: {', '.join(SUPPORTED_ASPECT_RATIOS)}"
    )
    parser.add_argument(
        "--api-key", "-k",
        help="Gemini API key (overrides GEMINI_API_KEY / GOOGLE_API_KEY env var)"
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help="Model name. Defaults to GEMINI_IMAGE_MODEL / GEMINI_MODEL / gemini-3-pro-image-preview"
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Gemini-compatible API base URL, e.g. https://yunwu.ai"
    )

    args = parser.parse_args()

    # Get API key
    api_key = get_api_key(args.api_key)
    model_name = get_model_name(args.model)
    base_url = get_base_url(args.base_url)
    if not api_key:
        print("Error: No API key provided.", file=sys.stderr)
        print("Please either:", file=sys.stderr)
        print("  1. Provide --api-key argument", file=sys.stderr)
        print("  2. Set GEMINI_API_KEY environment variable", file=sys.stderr)
        print("  3. Set GOOGLE_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    # Import here after checking API key to avoid slow import on error
    from PIL import Image as PILImage

    # Set up output path
    output_path = Path(args.filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load input images if provided (up to 14 supported by Nano Banana Pro)
    input_images = []
    max_input_dim = 0
    if args.input_images:
        if len(args.input_images) > 14:
            print(f"Error: Too many input images ({len(args.input_images)}). Maximum is 14.", file=sys.stderr)
            sys.exit(1)

        for img_path in args.input_images:
            try:
                with PILImage.open(img_path) as img:
                    copied = img.copy()
                    width, height = copied.size
                input_images.append(copied)
                print(f"Loaded input image: {img_path}")

                # Track largest dimension for auto-resolution
                max_input_dim = max(max_input_dim, width, height)
            except Exception as e:
                print(f"Error loading input image '{img_path}': {e}", file=sys.stderr)
                sys.exit(1)

    output_resolution, auto_detected = choose_output_resolution(
        requested_resolution=args.resolution,
        max_input_dim=max_input_dim,
        has_input_images=bool(input_images),
    )
    if auto_detected:
        print(
            f"Auto-detected resolution: {output_resolution} "
            f"(from max input dimension {max_input_dim})"
        )

    # Build contents (images first if editing, prompt only if generating)
    if input_images:
        contents = [*input_images, args.prompt]
        img_count = len(input_images)
        print(f"Processing {img_count} image{'s' if img_count > 1 else ''} with resolution {output_resolution}...")
    else:
        contents = args.prompt
        print(f"Generating image with resolution {output_resolution}...")

    try:
        from io import BytesIO

        print(f"Using model: {model_name}")
        print(f"Using base URL: {base_url}")

        image_config = {"imageSize": output_resolution}
        if args.aspect_ratio:
            image_config["aspectRatio"] = args.aspect_ratio

        parts = []
        if input_images:
            for img in input_images:
                buf = BytesIO()
                img.save(buf, format="PNG")
                parts.append(
                    {
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": base64.b64encode(buf.getvalue()).decode("ascii"),
                        }
                    }
                )
            parts.append({"text": args.prompt})
        else:
            parts.append({"text": args.prompt})

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": image_config,
            },
        }

        endpoint = f"{base_url}/v1beta/models/{model_name}:generateContent"
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=build_auth_headers(api_key, base_url),
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=300) as resp:
            response = json.loads(resp.read().decode("utf-8"))

        image_saved = False
        candidates = response.get("candidates", [])
        for candidate in candidates:
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                if "text" in part:
                    print(f"Model response: {part['text']}")
                inline_data = part.get("inlineData") or part.get("inline_data")
                if inline_data and inline_data.get("data"):
                    image_data = base64.b64decode(inline_data["data"])
                    image = PILImage.open(BytesIO(image_data))

                    if image.mode == 'RGBA':
                        rgb_image = PILImage.new('RGB', image.size, (255, 255, 255))
                        rgb_image.paste(image, mask=image.split()[3])
                        rgb_image.save(str(output_path), 'PNG')
                    elif image.mode == 'RGB':
                        image.save(str(output_path), 'PNG')
                    else:
                        image.convert('RGB').save(str(output_path), 'PNG')
                    image_saved = True
                    break
            if image_saved:
                break

        if image_saved:
            full_path = output_path.resolve()
            print(f"\nImage saved: {full_path}")
            print(f"MEDIA:{full_path}")
        else:
            finish_reason = None
            if candidates:
                finish_reason = candidates[0].get("finishReason") or candidates[0].get("finish_reason")
            print(
                f"Error: No image was generated in the response. finish_reason={finish_reason} raw_keys={list(response.keys())}",
                file=sys.stderr,
            )
            sys.exit(1)

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP error generating image: {e.code} {e.reason}", file=sys.stderr)
        print(body, file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network error generating image: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error generating image: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
