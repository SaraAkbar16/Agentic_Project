"""Tool for lip-syncing static images with audio using Wav2Lip."""

import logging
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Configuration
WAV2LIP_PATH = os.getenv("WAV2LIP_PATH", "C:\\Wav2Lip")
WAV2LIP_CHECKPOINT = os.getenv("WAV2LIP_CHECKPOINT", "checkpoints/wav2lip_gan.pth")
PYTHON_EXE = os.getenv("WAV2LIP_PYTHON", "python")

logger = logging.getLogger("phase3.wav2lip")

def sync_lips(
    image_path: str,
    audio_path: str,
    output_path: str
) -> str:
    """
    Run Wav2Lip inference to sync an image with audio.
    """
    if not os.path.exists(WAV2LIP_PATH):
        logger.error(f"Wav2Lip not found at {WAV2LIP_PATH}")
        raise RuntimeError(f"Wav2Lip directory missing: {WAV2LIP_PATH}")

    inference_script = str(Path(WAV2LIP_PATH) / "inference.py")
    checkpoint_path = str(Path(WAV2LIP_PATH) / WAV2LIP_CHECKPOINT)

    # Wav2Lip command
    cmd = [
        PYTHON_EXE, inference_script,
        "--checkpoint_path", checkpoint_path,
        "--face", str(Path(image_path).absolute()),
        "--audio", str(Path(audio_path).absolute()),
        "--outfile", str(Path(output_path).absolute())
    ]

    logger.info(f"Executing Wav2Lip: {' '.join(cmd)}")
    
    # Add FFmpeg to PATH for Wav2Lip's internal subprocess calls
    from mcp.tools.video_tools.ffmpeg_tool import FFMPEG_EXE
    env = os.environ.copy()
    ffmpeg_dir = str(Path(FFMPEG_EXE).parent)
    env["PATH"] = ffmpeg_dir + os.pathsep + env.get("PATH", "")

    try:
        # Wav2Lip often needs to be run from its own directory due to imports
        subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=WAV2LIP_PATH, env=env)
        logger.info(f"Wav2Lip sync complete: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Wav2Lip failed: {e.stderr}")
        raise RuntimeError(f"Wav2Lip error: {e.stderr}")
    except FileNotFoundError:
        logger.error("Python or Wav2Lip script not found.")
        raise RuntimeError("Wav2Lip execution failed: Script or Python not found.")
