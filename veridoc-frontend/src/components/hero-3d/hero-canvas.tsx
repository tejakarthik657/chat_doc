"use client";

import { useEffect, useRef } from 'react';
import { SceneEngine, Phase } from '@/lib/three/scene-engine';

interface HeroCanvasProps {
    onPhaseChange?: (phase: Phase) => void;
}

export default function HeroCanvas({ onPhaseChange }: HeroCanvasProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const engineRef = useRef<SceneEngine | null>(null);

    useEffect(() => {
        if (typeof window === 'undefined' || !canvasRef.current) return;

        // Initialize the engine
        const engine = new SceneEngine(canvasRef.current, onPhaseChange);
        engineRef.current = engine;

        return () => {
            engine.destroy();
        };
    }, [onPhaseChange]);

    return (
        <canvas
            ref={canvasRef}
            className="absolute inset-0 w-full h-full block"
        />
    );
}
