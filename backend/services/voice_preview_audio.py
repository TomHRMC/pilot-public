"""
Voice Preview Audio Generator — one-time S3 upload of persona preview MP3s.

Called via CLI/deployment script: python -m services.voice_preview_audio
NOT invoked at runtime; preview audio is static CDN-served content.

S3 output paths:
  s3://pilot-static/voice-preview/conservative.mp3
  s3://pilot-static/voice-preview/balanced.mp3
  s3://pilot-static/voice-preview/playful.mp3

CDN (CloudFront) serves these at:
  https://cdn.pilotfortrades.com/voice-preview/{tone}.mp3

Tom action required before production:
  1. Create pilot-static S3 bucket with public-read on voice-preview/* prefix.
  2. Configure CloudFront at cdn.pilotfortrades.com pointing to pilot-static.
  3. Run: python -m services.voice_preview_audio --overwrite
  4. Verify URLs are reachable.

TTS provider (G3 resolution): gTTS (free) used for one-time generation.
Can be swapped for OpenAI TTS by setting TTS_PROVIDER=openai in .env.
"""

import logging
import os
import tempfile

logger = logging.getLogger(__name__)

# Preview script sample text per tone (short, representative sample)
PREVIEW_SAMPLE_TEXT: dict[str, str] = {
    "conservative": (
        "Quote number one-two-three created for Johnson Electric. "
        "Total: four thousand, two hundred dollars."
    ),
    "balanced": (
        "Got it! I've created Quote 123 for Johnson Electric — "
        "total is $4,200. Want to add any line items?"
    ),
    "playful": (
        "Quote 123 is live for Johnson Electric! Total comes to $4,200. "
        "Let's get those line items in — what's next? 🎙️"
    ),
}


def _generate_mp3_gtts(text: str, output_path: str) -> None:
    """Generate an MP3 file from text using gTTS (free, no API key required)."""
    try:
        from gtts import gTTS  # type: ignore[import]
    except ImportError:
        raise ImportError(
            "gTTS is required for preview audio generation. "
            "Install it: pip install gTTS"
        )

    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(output_path)
    logger.info("Generated MP3 via gTTS: %s", output_path)


def _generate_mp3_openai(text: str, output_path: str) -> None:
    """Generate an MP3 file from text using OpenAI TTS API."""
    try:
        import openai  # type: ignore[import]
    except ImportError:
        raise ImportError(
            "openai package is required for OpenAI TTS. Install it: pip install openai"
        )

    from core.config import settings

    client = openai.OpenAI(api_key=getattr(settings, "OPENAI_API_KEY", None))
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text,
    )
    response.stream_to_file(output_path)
    logger.info("Generated MP3 via OpenAI TTS: %s", output_path)


def generate_and_upload_preview_audio(
    tones: list[str] = ("conservative", "balanced", "playful"),
    s3_bucket: str = "pilot-static",
    s3_prefix: str = "voice-preview",
    overwrite: bool = False,
    tts_provider: str = "gtts",
) -> dict[str, str]:
    """
    Generate preview audio files for each tone and upload to S3.

    This is a one-time deployment script — not called at runtime.

    Args:
        tones:        Tones to generate previews for.
        s3_bucket:    Target S3 bucket name.
        s3_prefix:    S3 key prefix (no trailing slash).
        overwrite:    If False, skip tones that already have an S3 object.
        tts_provider: "gtts" (free default) | "openai" (higher quality, ~$0.05 total).

    Returns:
        Dict mapping tone → S3 URI of uploaded object.
    """
    try:
        import boto3  # type: ignore[import]
    except ImportError:
        raise ImportError(
            "boto3 is required for S3 upload. Install it: pip install boto3"
        )

    s3 = boto3.client("s3")
    result: dict[str, str] = {}

    for tone in tones:
        s3_key = f"{s3_prefix}/{tone}.mp3"
        s3_uri = f"s3://{s3_bucket}/{s3_key}"

        # Check if already exists (skip unless overwrite=True)
        if not overwrite:
            try:
                s3.head_object(Bucket=s3_bucket, Key=s3_key)
                logger.info("Preview audio already exists for '%s', skipping.", tone)
                result[tone] = s3_uri
                continue
            except s3.exceptions.ClientError:
                pass  # Does not exist — proceed

        sample_text = PREVIEW_SAMPLE_TEXT.get(tone, PREVIEW_SAMPLE_TEXT["balanced"])

        # Generate MP3 to a temp file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            if tts_provider == "openai":
                _generate_mp3_openai(sample_text, tmp_path)
            else:
                _generate_mp3_gtts(sample_text, tmp_path)

            # Upload to S3 with public-read ACL
            s3.upload_file(
                tmp_path,
                s3_bucket,
                s3_key,
                ExtraArgs={"ContentType": "audio/mpeg"},
            )
            logger.info("Uploaded preview audio: %s", s3_uri)
            result[tone] = s3_uri

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    return result


if __name__ == "__main__":
    import argparse
    import sys

    # Ensure the backend directory is on the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    parser = argparse.ArgumentParser(
        description="Generate and upload voice persona preview audio files to S3."
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing S3 objects (default: skip if exists)",
    )
    parser.add_argument(
        "--tts-provider",
        choices=["gtts", "openai"],
        default="gtts",
        help="TTS provider to use (default: gtts)",
    )
    parser.add_argument(
        "--bucket",
        default="pilot-static",
        help="S3 bucket name (default: pilot-static)",
    )
    parser.add_argument(
        "--tones",
        nargs="+",
        default=["conservative", "balanced", "playful"],
        help="Tones to generate (default: all three)",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    uploaded = generate_and_upload_preview_audio(
        tones=args.tones,
        s3_bucket=args.bucket,
        overwrite=args.overwrite,
        tts_provider=args.tts_provider,
    )

    print("\nUploaded preview audio:")
    for tone, uri in uploaded.items():
        print(f"  {tone}: {uri}")
