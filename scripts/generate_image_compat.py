#!/usr/bin/env python3

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path

SUPPORTED_ASPECT_RATIOS = [
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9",
]
DEFAULT_MODEL = "gemini-3.1-flash-image-preview"
DEFAULT_BASE_URL = "https://yunwu.ai"


def get_api_key(provided_key: str | None) -> str | None:
    return provided_key or os.environ.get("XHS_IMAGE_API_KEY")


def get_model_name(provided_model: str | None) -> str:
    return provided_model or os.environ.get("XHS_IMAGE_MODEL") or DEFAULT_MODEL


def get_base_url(provided_base_url: str | None) -> str:
    return (provided_base_url or os.environ.get("XHS_IMAGE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def build_auth_headers(api_key: str, base_url: str) -> dict:
    if "generativelanguage.googleapis.com" in base_url:
        return {"Content-Type": "application/json", "x-goog-api-key": api_key}
    return {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}


def auto_detect_resolution(max_input_dim: int) -> str:
    if max_input_dim >= 3000:
        return "4K"
    if max_input_dim >= 1500:
        return "2K"
    return "1K"


def choose_output_resolution(requested_resolution: str | None, max_input_dim: int, has_input_images: bool) -> tuple[str, bool]:
    if requested_resolution is not None:
        return requested_resolution, False
    if has_input_images and max_input_dim > 0:
        return auto_detect_resolution(max_input_dim), True
    return "1K", False


def main():
    parser = argparse.ArgumentParser(description="Yunwu-first image generator for XHS SOP")
    parser.add_argument("--prompt", "-p", required=True)
    parser.add_argument("--filename", "-f", required=True)
    parser.add_argument("--input-image", "-i", action="append", dest="input_images", default=[])
    parser.add_argument("--resolution", "-r", choices=["1K", "2K", "4K"], default=None)
    parser.add_argument("--aspect-ratio", "-a", choices=SUPPORTED_ASPECT_RATIOS, default=None)
    parser.add_argument("--api-key", "-k")
    parser.add_argument("--model", "-m", default=None)
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()

    api_key = get_api_key(args.api_key)
    model_name = get_model_name(args.model)
    base_url = get_base_url(args.base_url)
    if not api_key:
        print("Error: No XHS image API key provided (expected XHS_IMAGE_API_KEY or --api-key).", file=sys.stderr)
        sys.exit(1)

    from PIL import Image as PILImage

    output_path = Path(args.filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

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
                max_input_dim = max(max_input_dim, width, height)
                print(f"Loaded input image: {img_path}")
            except Exception as e:
                print(f"Error loading input image '{img_path}': {e}", file=sys.stderr)
                sys.exit(1)

    output_resolution, auto_detected = choose_output_resolution(args.resolution, max_input_dim, bool(input_images))
    if auto_detected:
        print(f"Auto-detected resolution: {output_resolution} (from max input dimension {max_input_dim})")

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
            parts.append({
                "inlineData": {
                    "mimeType": "image/png",
                    "data": base64.b64encode(buf.getvalue()).decode("ascii"),
                }
            })
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

    try:
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
                    if image.mode == "RGBA":
                        rgb_image = PILImage.new("RGB", image.size, (255, 255, 255))
                        rgb_image.paste(image, mask=image.split()[3])
                        rgb_image.save(str(output_path), "PNG")
                    elif image.mode == "RGB":
                        image.save(str(output_path), "PNG")
                    else:
                        image.convert("RGB").save(str(output_path), "PNG")
                    image_saved = True
                    break
            if image_saved:
                break

        if not image_saved:
            finish_reason = candidates[0].get("finishReason") if candidates else None
            print(f"Error: No image was generated in the response. finish_reason={finish_reason} raw_keys={list(response.keys())}", file=sys.stderr)
            sys.exit(1)

        full_path = output_path.resolve()
        print(f"Image saved: {full_path}")
        print(f"MEDIA:{full_path}")
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
