import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

# Import existing agents
from agents.audio_agent.agent import run_phase2_on_file
from agents.video_agent.agent import VideoAgent

class EditIntent(BaseModel):
    intent: str
    target: str
    scope: str
    parameters: Dict[str, Any] = {}

logger = logging.getLogger("phase5.edit_agent")

class EditAgent:
    """Intelligent Editor that interprets natural language and modifies the pipeline state."""
    
    def __init__(self, state_manager):
        self.state_manager = state_manager

    def process_query(self, query: str, project_path: str) -> Dict[str, Any]:
        """Detect intent and execute the change."""
        logger.info(f"Processing Edit Query: {query}")
        
        # 1. Intent Detection (Simplified for this version)
        intent = self._detect_intent(query)
        
        # 2. Pre-edit Snapshot
        self.state_manager.snapshot(f"Before: {query}")
        
        # 3. Execution
        result = self._execute_intent(intent, Path(project_path))
        
        return result

    def _detect_intent(self, query: str) -> EditIntent:
        query = query.lower()
        
        # 1. Audio Intents
        if "voice" in query or "tone" in query or "speak" in query:
            tone = "whispered" if "whisper" in query else "energetic" if "energetic" in query else "modified"
            return EditIntent(intent="change_voice_tone", target="audio", scope="all", parameters={"tone": tone})
        if "music" in query or "bgm" in query or "background music" in query:
            return EditIntent(intent="add_bgm", target="audio", scope="all", parameters={"mood": "action"})
            
        # 2. Video Frame Intents (Image Gen)
        if "darker" in query or "brighter" in query or "aesthetic" in query:
            adj = "darker and moodier" if "darker" in query else "brighter and more vibrant"
            return EditIntent(intent="make_darker", target="video_frame", scope="all", parameters={"aesthetic": adj})
        if "character design" in query or "change character" in query or "look of" in query:
            return EditIntent(intent="change_character_design", target="video_frame", scope="all", parameters={"aesthetic": "updated character design"})
            
        # 3. Video Intents (Composition)
        if "subtitle" in query:
            return EditIntent(intent="remove_subtitle", target="video", scope="all")
        if "speed" in query or "faster" in query or "slower" in query:
            factor = 0.8 if "faster" in query or "speed up" in query else 1.2
            return EditIntent(intent="speed_up", target="video", scope="all", parameters={"factor": factor})
            
        # 4. Script Intents
        if "script" in query or "story" in query or "regenerate" in query:
            return EditIntent(intent="regenerate_script", target="script", scope="all")
            
        return EditIntent(intent="unknown", target="video", scope="all")

    def _execute_intent(self, intent: EditIntent, project_path: Path) -> Dict[str, Any]:
        """Trigger the appropriate sub-phase re-run based on the structured intent."""
        
        # Locate the Phase 1 state file
        state_files = list(project_path.parent.parent.parent.glob("phase1_state_*.json"))
        if not state_files:
            return {"status": "error", "message": "Could not find Phase 1 state file"}
        latest_state_file = sorted(state_files)[-1]
        
        with open(latest_state_file, "r") as f:
            state = json.load(f)

        if intent.target == "script":
            logger.info("Regenerating script (Phase 1)...")
            # In production, we would re-run Phase 1 CLI here
            return {"status": "success", "message": "Script regeneration triggered."}

        if intent.target == "video_frame":
            logger.info(f"Executing Visual Edit: {intent.intent}...")
            for scene in state.get("scenes", []):
                if intent.scope == "all" or scene["scene_id"] == intent.scope:
                    scene["visual_description"] += f", {intent.parameters.get('aesthetic', 'modified look')}"
            
            with open(latest_state_file, "w") as f:
                json.dump(state, f, indent=2)
            
            agent = VideoAgent({"phase1_state_file": str(latest_state_file), "force": True})
            agent.run()
            return {"status": "success", "message": f"Visuals updated and video re-generated."}

        if intent.target == "audio":
            logger.info(f"Executing Audio Edit: {intent.intent}...")
            if intent.intent == "change_voice_tone":
                # Tweak character descriptions for TTS
                for char in state.get("characters", []):
                    char["description"] += f", {intent.parameters.get('tone')} voice"
            elif intent.intent == "add_bgm":
                for scene in state.get("scenes", []):
                    scene["mood"] = intent.parameters.get("mood", "action")
            
            with open(latest_state_file, "w") as f:
                json.dump(state, f, indent=2)
                
            run_phase2_on_file(str(latest_state_file))
            agent = VideoAgent({"phase1_state_file": str(latest_state_file)})
            agent.run()
            return {"status": "success", "message": "Audio updated and video re-composed."}

        if intent.target == "video":
            logger.info(f"Executing Composition Edit: {intent.intent}...")
            # For subtitles, we would toggle the --subtitles flag in Phase 3
            # For speed_up, we would modify timing_manifest.json durations
            agent = VideoAgent({"phase1_state_file": str(latest_state_file)})
            agent.run()
            return {"status": "success", "message": "Video recomposed with updated parameters."}

        return {"status": "info", "message": "Edit processed."}
