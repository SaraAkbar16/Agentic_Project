"""Tool for generating images via local ComfyUI API.

This tool handles loading a workflow JSON, injecting prompts, submitting the
job to ComfyUI, polling for completion, and downloading the result.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Configuration Constants
PROMPT_NODE_ID = os.getenv("COMFY_PROMPT_NODE_ID", "6")
NEGATIVE_PROMPT_NODE_ID = os.getenv("COMFY_NEGATIVE_PROMPT_NODE_ID", "7")
COMFY_URL = os.getenv("COMFY_URL", "http://127.0.0.1:8188")
POLL_INTERVAL = 2
TIMEOUT = 120

# Paths
BASE_DIR = Path(__file__).parent.parent.parent.parent
WORKFLOW_PATH = BASE_DIR / "mcp/tools/vision_tools/comfy_workflows/wan2_t2i_api.json"
OUTPUT_DIR = BASE_DIR / "data/outputs/video/phase3/frames"

logger = logging.getLogger("phase3.image_gen")


def generate_image(
    prompt: str,
    scene_id: str,
    negative_prompt: str = "blurry, low quality, distorted, deformed",
    comfy_url: str = COMFY_URL
) -> str:
    """
    Generate an image using ComfyUI API.

    Args:
        prompt: The positive text prompt.
        scene_id: The ID of the scene (used for filename).
        negative_prompt: The negative text prompt.
        comfy_url: Base URL of the ComfyUI instance.

    Returns:
        The path to the saved image file.

    Raises:
        RuntimeError: If generation fails, times out, or workflow is missing.
    """
    if not WORKFLOW_PATH.exists():
        logger.error(f"Workflow file not found at {WORKFLOW_PATH}")
        raise RuntimeError(f"Workflow file missing: {WORKFLOW_PATH}")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load workflow
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        workflow = json.load(f)

    # Inject prompts
    if PROMPT_NODE_ID in workflow:
        logger.debug(f"Injecting prompt into node {PROMPT_NODE_ID}")
        # Assuming the standard 'text' field in the prompt node
        # Some workflows might use different keys, but we default to what's common
        node = workflow[PROMPT_NODE_ID]
        if "inputs" in node and "text" in node["inputs"]:
            node["inputs"]["text"] = prompt
        elif "inputs" in node and "string" in node["inputs"]:
             node["inputs"]["string"] = prompt
    else:
        logger.warning(f"Prompt node ID {PROMPT_NODE_ID} not found in workflow")

    if NEGATIVE_PROMPT_NODE_ID in workflow:
        node = workflow[NEGATIVE_PROMPT_NODE_ID]
        if "inputs" in node and "text" in node["inputs"]:
            node["inputs"]["text"] = negative_prompt
        elif "inputs" in node and "string" in node["inputs"]:
             node["inputs"]["string"] = negative_prompt

    logger.info(f"Submitting prompt to ComfyUI for scene {scene_id}")
    
    payload = {"prompt": workflow}
    try:
        response = requests.post(f"{comfy_url}/prompt", json=payload)
        response.raise_for_status()
        prompt_id = response.json()["prompt_id"]
    except Exception as e:
        logger.error(f"Failed to submit prompt to ComfyUI: {e}")
        raise RuntimeError(f"ComfyUI submission error: {e}")

    # Polling
    start_time = time.time()
    logger.info(f"Polling status for prompt_id: {prompt_id}")
    
    filename = ""
    while time.time() - start_time < TIMEOUT:
        try:
            history_resp = requests.get(f"{comfy_url}/history/{prompt_id}")
            history_resp.raise_for_status()
            history = history_resp.json()
            
            if prompt_id in history:
                # Job completed
                outputs = history[prompt_id].get("outputs", {})
                for node_id, node_output in outputs.items():
                    if "images" in node_output:
                        filename = node_output["images"][0]["filename"]
                        break
                if filename:
                    break
                else:
                    logger.error(f"No image found in ComfyUI history output for prompt {prompt_id}. Available outputs: {list(outputs.keys())}")
                    logger.debug(f"Full history for {prompt_id}: {json.dumps(history[prompt_id], indent=2)}")
                    raise RuntimeError("Image output missing from ComfyUI history")
            
            time.sleep(POLL_INTERVAL)
        except Exception as e:
            logger.error(f"Error polling ComfyUI: {e}")
            raise RuntimeError(f"ComfyUI polling error: {e}")
    else:
        logger.error(f"Timed out waiting for ComfyUI after {TIMEOUT} seconds")
        raise RuntimeError(f"ComfyUI generation timed out ({TIMEOUT}s)")

    # Download image
    logger.info(f"Downloading generated image: {filename}")
    image_url = f"{comfy_url}/view?filename={filename}&subfolder=&type=output"
    save_path = OUTPUT_DIR / f"scene_{scene_id}.png"
    
    try:
        img_resp = requests.get(image_url)
        img_resp.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(img_resp.content)
        logger.info(f"Image saved to {save_path}")
    except Exception as e:
        logger.error(f"Failed to download image from {image_url}: {e}")
        raise RuntimeError(f"Image download error: {e}")

    return str(save_path)
