"use client";

import Link from "next/link";
import Image from "next/image";

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-black text-white font-sans selection:bg-primary selection:text-black">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-[100] px-8 py-6 flex items-center justify-between backdrop-blur-md bg-black/50 border-b border-white/10">
        <Link href="/" className="flex items-center gap-4 group">
          <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(255,212,112,0.3)] group-hover:scale-110 transition-transform">
            <div className="w-5 h-5 bg-black rounded-sm rotate-45" />
          </div>
          <span className="font-black tracking-tighter text-2xl uppercase text-white italic">
            PixFrame <span className="text-primary">AI</span>
          </span>
        </Link>
        <Link 
          href="/dashboard"
          className="px-8 py-3 bg-white text-black text-xs font-black uppercase rounded-full hover:bg-primary transition-all active:scale-95 shadow-xl"
        >
          Launch App
        </Link>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-40 pb-20 px-8 overflow-hidden">
        <div className="max-w-7xl mx-auto relative z-10">
          <div className="flex flex-col items-center text-center">
            <div className="inline-block px-4 py-1.5 mb-8 bg-white/5 border border-white/10 rounded-full">
              <span className="text-[10px] font-black uppercase tracking-[0.3em] text-primary italic">
                Autonomous Video Production
              </span>
            </div>
            
            <h1 className="text-7xl md:text-9xl font-black italic uppercase tracking-tighter leading-[0.9] mb-8">
              Cinematic Vision <br />
              <span className="text-primary">Evolved.</span>
            </h1>
            
            <p className="max-w-2xl text-lg md:text-xl text-gray-400 font-medium mb-12 leading-relaxed">
              Transform scripts into professional-grade cinematic masterpieces. 
              Powered by advanced agentic AI, PixFrame handles everything from 
              scene generation to final render.
            </p>

            <div className="flex flex-col sm:flex-row gap-6">
              <Link 
                href="/dashboard"
                className="px-12 py-6 bg-primary text-black font-black text-xl uppercase italic rounded-2xl hover:bg-white transition-all active:scale-95 shadow-[0_0_50px_rgba(255,212,112,0.3)]"
              >
                Try It Out Now
              </Link>
              <button className="px-12 py-6 bg-white/5 border border-white/10 text-white font-black text-xl uppercase italic rounded-2xl hover:bg-white/10 transition-all active:scale-95">
                Watch Demo
              </button>
            </div>
          </div>
        </div>

        {/* Cinematic Backdrop Image */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full opacity-30 pointer-events-none">
          <div className="absolute inset-0 bg-gradient-to-b from-black via-transparent to-black z-10" />
          <Image 
            src="/hero.png" 
            alt="Cinematic Hero" 
            fill 
            className="object-cover scale-110 blur-sm"
            priority
          />
        </div>
      </section>

      {/* Bento Features Section */}
      <section className="py-32 px-8 bg-background-site text-black">
        <div className="max-w-7xl mx-auto">
          <div className="mb-20">
            <h2 className="text-5xl md:text-7xl font-black italic uppercase tracking-tighter mb-4">
              Production <span className="text-primary bg-black px-4">Engine</span>
            </h2>
            <p className="text-gray-500 font-bold uppercase tracking-widest text-xs">
              Precision Autonomous Workflow
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
            {/* Large Card: Scene Generation */}
            <div className="md:col-span-8 premium-card p-12 bg-white border border-gray-100 shadow-2xl relative overflow-hidden group hover:border-primary transition-all rounded-[3rem]">
              <div className="relative z-10">
                <div className="w-16 h-16 bg-black text-primary rounded-2xl flex items-center justify-center text-3xl font-black mb-8">
                  01
                </div>
                <h3 className="text-4xl font-black italic uppercase tracking-tighter mb-6">Scene Intelligence</h3>
                <p className="text-lg text-gray-600 max-w-md leading-relaxed font-medium">
                  Our agents analyze your script to create detailed visual blueprints, 
                  ensuring every frame aligns with your creative intent.
                </p>
              </div>
              <div className="absolute right-0 bottom-0 w-1/2 h-full bg-gray-50 opacity-50 -skew-x-12 translate-x-20 group-hover:translate-x-10 transition-all duration-700" />
            </div>

            {/* Small Card: Audio */}
            <div className="md:col-span-4 premium-card p-10 bg-black text-white rounded-[3rem] shadow-2xl border border-primary/20 flex flex-col justify-between group hover:shadow-primary/20 transition-all">
              <div className="w-12 h-12 bg-primary rounded-xl flex items-center justify-center text-xl font-black text-black">
                02
              </div>
              <div>
                <h3 className="text-2xl font-black italic uppercase tracking-tighter mb-4 text-primary">Sonic Synthesis</h3>
                <p className="text-sm text-gray-400 font-medium leading-relaxed">
                  High-fidelity audio generation with character voice profiles 
                  and immersive soundscapes.
                </p>
              </div>
            </div>

            {/* Small Card: Real-time */}
            <div className="md:col-span-4 premium-card p-10 bg-white border border-gray-100 rounded-[3rem] shadow-xl flex flex-col justify-between group hover:border-primary transition-all">
              <div className="w-12 h-12 bg-black text-white rounded-xl flex items-center justify-center text-xl font-black">
                03
              </div>
              <div>
                <h3 className="text-2xl font-black italic uppercase tracking-tighter mb-4">Live Insights</h3>
                <p className="text-sm text-gray-500 font-medium leading-relaxed">
                  Watch the AI think in real-time with our Project DNA stream 
                  and live status updates.
                </p>
              </div>
            </div>

            {/* Large Card: Editing */}
            <div className="md:col-span-8 premium-card p-12 bg-primary text-black rounded-[3rem] shadow-2xl relative overflow-hidden group transition-all">
              <div className="relative z-10 flex flex-col h-full justify-between">
                <div>
                  <div className="w-16 h-16 bg-black text-primary rounded-2xl flex items-center justify-center text-3xl font-black mb-8 shadow-xl">
                    04
                  </div>
                  <h3 className="text-4xl font-black italic uppercase tracking-tighter mb-6">Dynamic Editor</h3>
                  <p className="text-lg text-black/70 max-w-lg leading-relaxed font-bold italic">
                    "Change the mood to Cyberpunk." <br />
                    Just ask. Our AI refines your production on the fly.
                  </p>
                </div>
              </div>
              <div className="absolute -right-20 -bottom-20 w-80 h-80 bg-black/5 rounded-full blur-3xl" />
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-40 px-8 bg-black relative overflow-hidden">
        <div className="max-w-4xl mx-auto text-center relative z-10">
          <h2 className="text-6xl md:text-8xl font-black italic uppercase tracking-tighter mb-10">
            Ready to <span className="text-primary">Create?</span>
          </h2>
          <Link 
            href="/dashboard"
            className="inline-block px-16 py-8 bg-white text-black font-black text-2xl uppercase italic rounded-[2rem] hover:bg-primary transition-all active:scale-95 shadow-2xl"
          >
            Start Your First Project
          </Link>
          <p className="mt-8 text-gray-500 font-bold uppercase tracking-widest text-[10px]">
            No credit card required • Instant AI generation • Professional Export
          </p>
        </div>
        
        {/* Animated Background Elements */}
        <div className="absolute top-0 left-0 w-full h-full opacity-10 pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary rounded-full blur-[120px] animate-pulse" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-primary rounded-full blur-[120px] animate-pulse delay-700" />
        </div>
      </section>

      {/* Footer (Mirroring current) */}
      <footer className="bg-black py-12 px-8 border-t border-primary/20 text-center">
        <div className="flex flex-col items-center gap-6">
          <div className="w-12 h-12 bg-primary/10 rounded-2xl flex items-center justify-center border border-primary/20">
            <div className="w-4 h-4 bg-primary rounded-sm animate-spin-slow" />
          </div>
          <div className="space-y-2">
            <p className="text-white font-black uppercase text-xl italic tracking-tighter">PIXFRAME <span className="text-primary">AI</span></p>
            <p className="text-gray-500 text-[10px] font-bold uppercase tracking-[0.3em]">Precision Autonomous Production Engine</p>
          </div>
          <p className="text-gray-700 text-[8px] font-black uppercase tracking-widest mt-8">© 2026 Deepmind Agentic Systems — All Rights Reserved</p>
        </div>
      </footer>
    </main>
  );
}
