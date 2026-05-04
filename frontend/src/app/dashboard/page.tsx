"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";

type PhaseStatus = "idle" | "running" | "completed" | "failed";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface Phase {
  id: number;
  name: string;
  status: PhaseStatus;
  logs: string[];
  progress: number;
}

interface HistoryItem {
  id: string;
  url: string;
  timestamp: string;
  data?: any;
}

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [projectId, setProjectId] = useState<string | null>(null);
  const [phases, setPhases] = useState<Phase[]>([
    { id: 1, name: "Scene Generation", status: "idle", logs: [], progress: 0 },
    { id: 2, name: "Audio Generation", status: "idle", logs: [], progress: 0 },
    { id: 3, name: "Video Generation", status: "idle", logs: [], progress: 0 },
    { id: 4, name: "Final Output", status: "idle", logs: [], progress: 0 },
  ]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [outputUrl, setOutputUrl] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  // Metadata & History
  const [projectData, setProjectData] = useState<any>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  // Phase 5: Edit
  const [editQuery, setEditQuery] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [editHistory, setEditHistory] = useState<{ q: string, a: string }[]>([]);

  const logRefs = useRef<{ [key: number]: HTMLDivElement | null }>({});

  useEffect(() => {
    setMounted(true);
    fetchHistory();
  }, []);

  useEffect(() => {
    phases.forEach(p => {
      const ref = logRefs.current[p.id];
      if (ref) ref.scrollTop = ref.scrollHeight;
    });
  }, [phases]);

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/history`);
      const data = await res.json();
      setHistory(data);
    } catch (err) {
      console.error("Failed to fetch history", err);
    }
  };

  const startGeneration = async () => {
    if (!prompt) return;
    setIsGenerating(true);
    setOutputUrl(null);
    setProjectData(null);
    setPhases(prev => prev.map(p => ({ ...p, status: "idle", logs: [], progress: 0 })));

    try {
      const res = await fetch(`${API_BASE_URL}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const data = await res.json();
      setProjectId(data.project_id);
      connectToStream(data.project_id);
    } catch (err) {
      console.error("Failed to start generation", err);
      setIsGenerating(false);
    }
  };

  const connectToStream = (id: string) => {
    const eventSource = new EventSource(`${API_BASE_URL}/stream/${id}`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.status === "failed") {
        eventSource.close();
        setIsGenerating(false);
        return;
      }

      setPhases(prev => prev.map(p => {
        if (p.id === data.phase) {
          return {
            ...p,
            status: data.status as PhaseStatus,
            logs: data.log ? [...p.logs, data.log] : p.logs,
            progress: data.progress || p.progress
          };
        }
        if (p.id < data.phase) {
          return { ...p, status: "completed" };
        }
        return p;
      }));

      if (data.project_state) setProjectData(data.project_state);
      if (data.output_url) setOutputUrl(data.output_url);

      if (data.phase === 4 && data.status === "completed") {
        setIsGenerating(false);
        eventSource.close();
        fetchHistory(); // Refresh library
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      setIsGenerating(false);
    };
  };

  const handleEdit = async () => {
    if (!editQuery || !projectId) return;
    setIsEditing(true);
    try {
      const res = await fetch(`${API_BASE_URL}/edit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId, query: editQuery }),
      });
      const result = await res.json();
      setEditHistory(prev => [...prev, { q: editQuery, a: result.message }]);
      setEditQuery("");
    } catch (err) {
      console.error("Edit failed", err);
    } finally {
      setIsEditing(false);
    }
  };

  const loadFromHistory = (item: HistoryItem) => {
    setProjectId(item.id);
    setOutputUrl(item.url);
    setProjectData(item.data);
    setShowHistory(false);
    setPhases(prev => prev.map(p => ({ ...p, status: "completed" })));
  };

  const resetProject = () => {
    setPrompt("");
    setProjectId(null);
    setOutputUrl(null);
    setProjectData(null);
    setEditHistory([]);
    setPhases(prev => prev.map(p => ({ ...p, status: "idle", logs: [], progress: 0 })));
    setShowHistory(false);
  };

  const rerunPhase = async (phaseId: number) => {
    if (!projectId) return;
    setIsGenerating(true);
    // Reset phases from the selected one onwards
    setPhases(prev => prev.map(p => {
      if (p.id >= phaseId) {
        return { ...p, status: "idle", logs: [], progress: 0 };
      }
      return p;
    }));

    try {
      await fetch(`${API_BASE_URL}/rerun-phase`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId, phase: phaseId }),
      });
      connectToStream(projectId);
    } catch (err) {
      console.error("Rerun failed", err);
      setIsGenerating(false);
    }
  };

  if (!mounted) return null;

  return (
    <main className="min-h-screen bg-background-site flex flex-col font-sans text-contrast">
      {/* Top Navigation */}
      <nav className="fixed top-0 left-0 right-0 bg-black z-[100] px-8 py-4 flex items-center justify-between border-b border-primary/20">
        <Link href="/" className="flex items-center gap-4 group">
          <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(255,212,112,0.3)] group-hover:scale-110 transition-transform">
            <div className="w-5 h-5 bg-black rounded-sm rotate-45" />
          </div>
          <span className="font-black tracking-tighter text-2xl uppercase text-white italic">PixFrame <span className="text-primary">AI</span></span>
        </Link>
        <div className="flex items-center gap-8">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="text-xs font-black uppercase tracking-widest text-primary hover:text-white transition-all flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            Library
          </button>
          <button 
            onClick={resetProject}
            className="px-6 py-2 bg-white text-black text-[10px] font-black uppercase rounded-full hover:bg-primary transition-all active:scale-95 shadow-lg"
          >
            New Project
          </button>
        </div>
      </nav>

      {/* History Sidebar/Overlay */}
      {showHistory && (
        <div className="fixed inset-0 z-[110] flex justify-end">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowHistory(false)} />
          <div className="relative w-full max-w-md bg-black border-l border-primary/20 h-full p-8 overflow-y-auto animate-in slide-in-from-right duration-300">
            <div className="flex items-center justify-between mb-10">
              <h2 className="text-3xl font-black text-white italic uppercase tracking-tighter">Production <span className="text-primary">Library</span></h2>
              <button onClick={() => setShowHistory(false)} className="text-primary hover:text-white transition-all">
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="space-y-4">
              {history.map((item) => (
                <div
                  key={item.id}
                  onClick={() => loadFromHistory(item)}
                  className="p-6 rounded-2xl bg-white/5 border border-white/10 hover:border-primary group cursor-pointer transition-all"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-black text-primary uppercase italic">{item.timestamp}</span>
                    <div className="w-2 h-2 bg-green-500 rounded-full" />
                  </div>
                  <p className="text-sm font-black text-white uppercase tracking-tight group-hover:text-primary">{item.id}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Main Grid Layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-0 pt-20">

        {/* Left Column: Generation Flow */}
        <div className="lg:col-span-8 p-8 border-r border-gray-200">
          {/* Hero / Prompt Input */}
          <div className="mb-12">
            <h2 className="text-md font-black uppercase text-black mb-4 tracking-widest italic">Script</h2>
            <div className="relative group shadow-2xl rounded-3xl overflow-hidden bg-white p-2 border border-gray-100">
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe your vision or paste your full script here..."
                className="w-full px-8 py-8 text-2xl bg-white border-none outline-none text-contrast placeholder:text-gray-300 min-h-[200px] resize-none leading-relaxed font-medium"
                disabled={isGenerating}
              />
              <button
                onClick={startGeneration}
                disabled={isGenerating || !prompt}
                className="absolute right-4 bottom-4 px-10 py-6 rounded-2xl bg-black text-primary font-black text-lg hover:bg-primary hover:text-black active:scale-95 disabled:opacity-50 transition-all flex items-center italic shadow-2xl"
              >
                {isGenerating ? <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin mr-3" /> : null}
                {isGenerating ? "Processing" : "Initialize"}
              </button>
            </div>
          </div>

          {/* Final Video Render - Positioned above for immediate visibility */}
          {outputUrl && (
            <div className="mb-16 premium-card p-2 bg-black overflow-hidden shadow-2xl rounded-[2.5rem] border-4 border-primary/20 animate-in zoom-in-95 duration-500">
              <video src={`${API_BASE_URL}${outputUrl}`} controls className="w-full rounded-[2.2rem] aspect-video bg-black shadow-inner" />
              <div className="p-10 flex flex-col md:flex-row items-center justify-between gap-6">
                <div>
                  <h2 className="text-4xl font-black text-white tracking-tighter uppercase italic">Video <span className="text-primary">Ready</span></h2>
                  <p className="text-gray-500 font-bold uppercase tracking-widest text-[10px] mt-2">UUID: {projectId}</p>
                </div>
                <div className="flex gap-4">
                  <a href={`${API_BASE_URL}${outputUrl}`} download className="px-12 py-5 bg-primary text-black font-black rounded-2xl hover:bg-white active:scale-95 transition-all uppercase tracking-tighter text-lg italic shadow-[0_0_30px_rgba(255,212,112,0.3)]">
                    Export
                  </a>
                </div>
              </div>
            </div>
          )}

          {/* Phases */}
          <div className="space-y-8">
            {phases.map((phase, index) => (
              <div key={phase.id} className="premium-card p-8 border border-gray-100 transition-all hover:shadow-xl group">
                <div className="flex flex-col md:flex-row gap-8">
                  <div className={`w-14 h-14 rounded-2xl flex items-center justify-center shrink-0 font-black text-2xl transition-all shadow-md ${phase.status === 'completed' ? 'bg-primary text-black' :
                    phase.status === 'running' ? 'bg-black text-primary' :
                      'bg-gray-50 text-gray-300'
                    }`}>
                    {phase.id}
                  </div>

                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-4xl font-black text-contrast tracking-tighter uppercase italic">{phase.name}</h3>
                      <div className="flex items-center gap-3">
                        <span className={`text-[10px] tracking-widest font-black px-4 py-2 rounded-lg shadow-sm border ${phase.status === 'completed' ? 'bg-primary border-primary text-black' :
                          phase.status === 'running' ? 'bg-black text-primary animate-pulse border-black' :
                            'bg-gray-50 border-gray-100 text-gray-400'
                          }`}>
                          {phase.status.toUpperCase()}
                        </span>
                        {projectId && phase.status !== 'running' && (
                          <button
                            onClick={() => rerunPhase(phase.id)}
                            className="p-2 hover:bg-gray-100 rounded-lg transition-all text-muted hover:text-black group-hover:opacity-100 opacity-0"
                            title={`Redo ${phase.name}`}
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                          </button>
                        )}
                      </div>
                    </div>

                    {phase.status === 'running' && (
                      <div className="space-y-4 mb-6">
                        {phase.logs.length > 0 && (
                          <div className="bg-primary/5 border-l-4 border-primary p-6 rounded-r-2xl">
                            <p className="text-2xl font-black text-contrast italic">
                              "{phase.logs[phase.logs.length - 1]}"
                            </p>
                          </div>
                        )}
                        <div className="w-full h-4 bg-gray-50 rounded-full overflow-hidden border border-gray-100">
                          <div className="h-full bg-primary transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(255,212,112,0.5)]" style={{ width: `${phase.progress || 50}%` }} />
                        </div>
                      </div>
                    )}

                    <div
                      ref={(el) => { logRefs.current[phase.id] = el; }}
                      className={`p-6 bg-black text-[#666] rounded-2xl font-mono text-xs max-h-40 overflow-y-auto leading-relaxed border-t-4 border-primary transition-all ${phase.status === 'running' ? 'opacity-100 shadow-2xl' : 'opacity-30'}`}
                    >
                      {phase.logs.map((log, i) => (
                        <div key={i} className="mb-2 flex gap-3">
                          <span className="text-primary font-bold">{`>`}</span>
                          <span>{log}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Data Insights */}
        <div className="lg:col-span-4 bg-white/50 backdrop-blur-xl p-8 flex flex-col gap-8 min-h-screen border-l border-gray-100">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-black uppercase italic tracking-tighter">Project <span className="text-primary">DNA</span></h2>
            <div className="px-4 py-1 bg-primary text-black rounded-full text-[10px] font-black uppercase tracking-widest shadow-lg">Active Stream</div>
          </div>

          {/* Project State Panel */}
          <div className="flex-1 space-y-8 overflow-y-auto pr-2 custom-scrollbar pb-10">
            {!projectData ? (
              <div className="h-full flex flex-col items-center justify-center text-center opacity-30 p-10 grayscale">
                <div className="w-24 h-24 border-8 border-dashed border-gray-200 rounded-3xl mb-8 flex items-center justify-center rotate-45">
                  <div className="w-12 h-12 bg-gray-200 rounded-full animate-pulse -rotate-45" />
                </div>
                <p className="font-black uppercase tracking-widest text-xs">Awaiting Initialization...</p>
              </div>
            ) : (
              <>
                {/* Prompt Context */}
                <div className="premium-card p-8 bg-white shadow-xl border-l-8 border-primary">
                  <h4 className="text-[10px] font-black uppercase text-muted mb-4 tracking-widest italic">Core Narrative</h4>
                  <p className="text-base font-bold text-contrast italic leading-relaxed">"{projectData.meta?.user_prompt || projectData.prompt || prompt}"</p>
                </div>

                {/* Character Cast */}
                {projectData.characters && (
                  <div className="space-y-6">
                    <h4 className="text-[10px] font-black uppercase text-muted tracking-widest border-b border-gray-100 pb-2">Character Cast</h4>
                    <div className="grid grid-cols-1 gap-4">
                      {projectData.characters.map((char: any, i: number) => (
                        <div key={i} className="p-5 rounded-[1.5rem] bg-white border border-gray-100 flex items-center gap-6 shadow-sm hover:shadow-xl transition-all">
                          <div className="w-14 h-14 rounded-2xl bg-black text-primary flex items-center justify-center text-2xl font-black shadow-lg">
                            {char.name?.[0] || "?"}
                          </div>
                          <div>
                            <p className="font-black text-contrast uppercase text-sm tracking-tight">{char.name}</p>
                            <p className="text-[10px] text-muted font-bold tracking-tight mt-1 uppercase italic">{char.role || "Lead"}</p>
                          </div>
                          <div className="ml-auto px-4 py-1.5 bg-gray-50 text-muted text-[10px] font-black rounded-xl border border-gray-100">
                            {char.voice_profile?.gender || "SAPI5"}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Scene Breakdown */}
                {projectData.scenes && (
                  <div className="space-y-6">
                    <h4 className="text-[10px] font-black uppercase text-muted tracking-widest border-b border-gray-100 pb-2">Scene Blueprints</h4>
                    <div className="space-y-4">
                      {projectData.scenes.map((scene: any, i: number) => (
                        <div key={i} className="p-6 rounded-[1.5rem] bg-white border border-gray-100 group hover:border-primary transition-all shadow-sm">
                          <div className="flex items-center justify-between mb-4">
                            <span className="text-[10px] font-black text-muted uppercase italic">Act {i + 1}</span>
                            <span className="text-[10px] font-black uppercase text-primary bg-black px-3 py-1 rounded-lg italic">{scene.mood || "Standard"}</span>
                          </div>
                          <p className="text-xs font-bold text-contrast leading-relaxed mb-4 group-hover:text-black">
                            {scene.visual_description}
                          </p>
                          <div className="flex gap-2">
                            <div className="h-1.5 flex-1 bg-primary rounded-full" />
                            <div className="h-1.5 flex-1 bg-gray-100 rounded-full" />
                            <div className="h-1.5 flex-1 bg-gray-100 rounded-full" />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Footer-embedded AI intelligence */}
          {outputUrl && (
            <div className="mt-auto">
              <div className="premium-card p-8 bg-black rounded-[2rem] shadow-2xl border border-primary/20">
                <h3 className="text-primary font-black uppercase text-[10px] mb-5 italic tracking-widest flex items-center gap-2">
                  <span className="w-2 h-2 bg-primary rounded-full" />
                  Dynamic Editor
                </h3>
                <div className="relative">
                  <input
                    type="text"
                    value={editQuery}
                    onChange={(e) => setEditQuery(e.target.value)}
                    placeholder="Request modification..."
                    className="w-full p-5 pr-14 bg-white/5 rounded-2xl border-none outline-none text-white text-xs font-bold placeholder:text-gray-600 focus:ring-1 ring-primary transition-all"
                    onKeyDown={(e) => e.key === 'Enter' && handleEdit()}
                  />
                  <button
                    onClick={handleEdit}
                    disabled={isEditing || !editQuery}
                    className="absolute right-2 top-2 bottom-2 w-12 flex items-center justify-center bg-primary text-black rounded-xl hover:bg-white transition-all shadow-lg"
                  >
                    {isEditing ? "..." : "↵"}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Noir Footer */}
      <footer className="bg-black py-12 px-8 border-t border-primary/20 text-center">
        <div className="flex flex-col items-center gap-6">
          <div className="w-12 h-12 bg-primary/10 rounded-2xl flex items-center justify-center border border-primary/20">
            <div className="w-4 h-4 bg-primary rounded-sm animate-spin-slow" />
          </div>
          <div className="space-y-2">
            <p className="text-white font-black uppercase text-xl italic tracking-tighter">PIXFRAME <span className="text-primary">AI</span></p>
            <p className="text-gray-500 text-[10px] font-bold uppercase tracking-[0.3em]">Precision Autonomous Production Engine</p>
          </div>
          <div className="flex gap-8 mt-4">
            {['Documentation', 'API Reference', 'Status', 'Help'].map(link => (
              <a key={link} href="#" className="text-gray-500 hover:text-primary transition-all text-[10px] font-black uppercase tracking-widest">{link}</a>
            ))}
          </div>
          <p className="text-gray-700 text-[8px] font-black uppercase tracking-widest mt-8">© 2026 Deepmind Agentic Systems — All Rights Reserved</p>
        </div>
      </footer>
    </main>
  );
}
