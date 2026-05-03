import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from agents.story_agent.agent import generate_phase1_state
from agents.audio_agent.agent import run_phase2_on_file
from agents.video_agent.agent import VideoAgent
from agents.edit_agent.agent import EditAgent
from agents.edit_agent.state_manager import StateManager

app = FastAPI(title="Agentic AI Pipeline API")

# 1. CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Mount outputs
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")

# Global session storage
event_queues: Dict[str, asyncio.Queue] = {}
project_states: Dict[str, Dict[str, Any]] = {}

class GenerateRequest(BaseModel):
    prompt: str

class EditRequest(BaseModel):
    project_id: str
    query: str

class RerunRequest(BaseModel):
    project_id: str
    phase: int
    params: Optional[Dict[str, Any]] = {}

# Custom Logging Handler to pipe logs to SSE
class SSEHandler(logging.Handler):
    def __init__(self, project_id: str):
        super().__init__()
        self.project_id = project_id
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record):
        try:
            msg = self.format(record)
            if self.project_id in event_queues:
                loop = asyncio.get_event_loop()
                loop.call_soon_threadsafe(
                    lambda: event_queues[self.project_id].put_nowait({
                        "phase": active_phases.get(self.project_id, 1),
                        "status": "running", 
                        "log": msg
                    })
                )
        except Exception:
            pass

active_phases: Dict[str, int] = {}

async def log_to_stream(project_id: str, phase: int, status: str, log: str = None, progress: int = None):
    active_phases[project_id] = phase
    if project_id in event_queues:
        data = {"phase": phase, "status": status}
        if log: data["log"] = log
        if progress: data["progress"] = progress
        await event_queues[project_id].put(data)

@app.post("/generate")
async def generate(request: GenerateRequest, background_tasks: BackgroundTasks):
    project_id = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    event_queues[project_id] = asyncio.Queue()
    project_states[project_id] = {"prompt": request.prompt, "status": "started"}
    
    background_tasks.add_task(run_full_pipeline, project_id, request.prompt)
    return {"project_id": project_id}

async def run_full_pipeline(project_id: str, prompt: str):
    # Capture all internal agent logs and pipe to SSE
    handler = SSEHandler(project_id)
    logging.getLogger().addHandler(handler)
    
    try:
        # Phase 1: Story
        await log_to_stream(project_id, 1, "running", "Generating Story Script...")
        phase1_state = generate_phase1_state(prompt)
        # Ensure project_id is in metadata
        if "meta" not in phase1_state: phase1_state["meta"] = {}
        phase1_state["meta"]["project_id"] = project_id
        
        p1_path = (OUTPUT_DIR / f"phase1_state_{project_id}.json").resolve()
        with open(p1_path, "w") as f:
            json.dump(phase1_state, f, indent=2)
            
        await event_queues[project_id].put({
            "phase": 1, 
            "status": "completed", 
            "log": f"Script saved: {p1_path.name}",
            "project_state": phase1_state
        })

        # Phase 2: Audio
        await log_to_stream(project_id, 2, "running", "Generating Audio & BGM...")
        phase2_result = run_phase2_on_file(str(p1_path))
        
        # Resolve the project-specific manifest with an absolute path
        manifest_path = (OUTPUT_DIR / "audio" / "phase2" / project_id / "timing_manifest.json").resolve()
        
        await log_to_stream(project_id, 2, "completed", "Audio assets generated successfully.")

        # Phase 3: Video
        await log_to_stream(project_id, 3, "running", "Initializing Video Engine...")
        video_config = {
            "phase1_state_file": str(p1_path),
            "timing_manifest_file": str(manifest_path),
            "project_id": project_id,
            "data_dir": str(OUTPUT_DIR.resolve()),
            "subtitles": True
        }
        
        agent = VideoAgent(video_config)
        await asyncio.to_thread(agent.run)
        
        await log_to_stream(project_id, 3, "completed", "Video composition finished.", progress=100)
        
        # Small buffer for UI sync
        await asyncio.sleep(0.5)

        # Phase 4: Output
        # VideoAgent with subtitles=True outputs final_output_subtitled.mp4
        rel_path = f"video/phase3/{project_id}/final_output_subtitled.mp4"
        await event_queues[project_id].put({
            "phase": 4, 
            "status": "completed", 
            "log": "Your production is ready!", 
            "progress": 100,
            "output_url": f"/output/{rel_path}"
        })

    except Exception as e:
        logging.error(f"Pipeline Error: {e}", exc_info=True)
        await log_to_stream(project_id, active_phases.get(project_id, 1), "failed", f"Error: {str(e)}")
    finally:
        logging.getLogger().removeHandler(handler)

@app.get("/stream/{project_id}")
async def stream(project_id: str):
    async def event_generator():
        queue = event_queues.get(project_id)
        if not queue: yield f"data: {json.dumps({'error': 'Not found'})}\n\n"; return
        while True:
            data = await queue.get()
            yield f"data: {json.dumps(data)}\n\n"
            if data.get("phase") == 4 or data.get("status") == "failed": break
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/edit")
async def edit(request: EditRequest):
    project_path = OUTPUT_DIR / "video" / "phase3" / request.project_id
    manager = StateManager(str(project_path))
    agent = EditAgent(manager)
    
    result = agent.process_query(request.query, str(project_path))
    return result

@app.get("/history")
async def get_history():
    history = []
    video_root = OUTPUT_DIR / "video" / "phase3"
    if video_root.exists():
        for project_dir in video_root.iterdir():
            if project_dir.is_dir():
                # Check for subtitled or regular video
                video_file = project_dir / "final_output_subtitled.mp4"
                if not video_file.exists():
                    video_file = project_dir / "final_output.mp4"
                
                if video_file.exists():
                    # Load DNA (Phase 1 State) if it exists
                    project_dna = None
                    dna_file = OUTPUT_DIR / f"phase1_state_{project_dir.name}.json"
                    if dna_file.exists():
                        try:
                            with open(dna_file, "r", encoding="utf-8") as f:
                                project_dna = json.load(f)
                        except:
                            pass

                    history.append({
                        "id": project_dir.name,
                        "url": f"/output/video/phase3/{project_dir.name}/{video_file.name}",
                        "timestamp": datetime.fromtimestamp(project_dir.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "data": project_dna
                    })
    # Sort by latest
    history.sort(key=lambda x: x["timestamp"], reverse=True)
    return history

@app.post("/rerun-phase")
async def rerun_phase(request: RerunRequest):
    # Logic to trigger specific run based on phase index
    return {"status": "re-run triggered"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
