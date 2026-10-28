"use client";

import React, { useState, useEffect, useRef } from "react";
import { Mic, MicOff, Sparkles, Loader2, Radio } from "lucide-react";
import api from "@/lib/api";

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  onSendVoiceQuery?: (text: string) => void;
  isGenerating?: boolean;
}

export const VoiceInput: React.FC<VoiceInputProps> = ({
  onTranscript,
  onSendVoiceQuery,
  isGenerating = false,
}) => {
  const [isListening, setIsListening] = useState(false);
  const [isRecordingCloud, setIsRecordingCloud] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);
  const [autoSend, setAutoSend] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (!SpeechRecognition) {
        setSpeechSupported(false);
      }
    }
  }, []);

  // ── Fallback: Groq Cloud Whisper Audio Recorder ─────────────────────────
  const startCloudWhisperRecording = async () => {
    try {
      setStatusMessage("Connecting to microphone (Cloud Whisper)...");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/mp4";

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        setIsRecordingCloud(false);
        setIsTranscribing(true);
        setStatusMessage("Transcribing via Groq Whisper Turbo...");

        try {
          const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
          const formData = new FormData();
          formData.append("file", audioBlob, "voice-input.webm");

          const res = await api.post<{ transcript: string }>("/features/transcribe", formData, {
            headers: { "Content-Type": "multipart/form-data" },
            timeout: 20000,
          });

          const transcript = res.data?.transcript?.trim();
          if (transcript) {
            onTranscript(transcript);
            setStatusMessage(null);
            if (autoSend && onSendVoiceQuery) {
              onSendVoiceQuery(transcript);
            }
          } else {
            setStatusMessage("No audible speech detected. Please try again.");
            setTimeout(() => setStatusMessage(null), 3500);
          }
        } catch (err: any) {
          console.error("[VoiceInput] Cloud transcription error:", err);
          setStatusMessage("Whisper transcription failed. Please try again or type.");
          setTimeout(() => setStatusMessage(null), 4000);
        } finally {
          setIsTranscribing(false);
        }
      };

      mediaRecorder.start(250);
      setIsRecordingCloud(true);
      setStatusMessage("Listening... Speak clearly (Click mic to finish)");
    } catch (err: any) {
      console.error("[VoiceInput] Microphone access error:", err);
      setStatusMessage("Microphone access denied. Grant browser microphone permission.");
      setTimeout(() => setStatusMessage(null), 5000);
    }
  };

  const stopCloudWhisperRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
  };

  // ── Primary: Browser Web Speech API with Auto-Fallback ──────────────────
  const toggleListening = () => {
    setStatusMessage(null);

    // If currently transcribing, ignore
    if (isTranscribing) return;

    // If Cloud Whisper is recording, stop it
    if (isRecordingCloud) {
      stopCloudWhisperRecording();
      return;
    }

    // If Web Speech is listening, stop it
    if (isListening) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsListening(false);
      return;
    }

    // If Web Speech isn't supported, use Cloud Whisper directly
    if (!speechSupported) {
      startCloudWhisperRecording();
      return;
    }

    try {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognitionRef.current = recognition;
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      let finalCapturedText = "";

      recognition.onstart = () => {
        setIsListening(true);
        setStatusMessage("Listening (browser dictation)...");
      };

      recognition.onresult = (event: any) => {
        let currentTranscript = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          currentTranscript += event.results[i][0].transcript;
        }
        finalCapturedText = currentTranscript;
        onTranscript(currentTranscript);
        if (event.results[0].isFinal && autoSend && onSendVoiceQuery) {
          onSendVoiceQuery(currentTranscript);
        }
      };

      recognition.onerror = (event: any) => {
        setIsListening(false);
        const err = event?.error || "unknown";

        // CRITICAL: On network or service-not-allowed, seamlessly failover to Cloud Whisper!
        if (err === "network" || err === "service-not-allowed") {
          console.warn("[VoiceInput] Web Speech network error detected. Seamlessly failing over to Groq Cloud Whisper...");
          setStatusMessage("Switching to Groq Whisper Cloud...");
          setTimeout(() => {
            startCloudWhisperRecording();
          }, 300);
        } else if (err === "not-allowed" || err === "permission-denied") {
          setStatusMessage("Microphone access denied. Grant browser permission.");
          setTimeout(() => setStatusMessage(null), 5000);
        } else if (err !== "no-speech" && err !== "aborted") {
          setStatusMessage(`Speech note: ${err}`);
          setTimeout(() => setStatusMessage(null), 3000);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
        if (!finalCapturedText) {
          setStatusMessage(null);
        }
      };

      recognition.start();
    } catch (err: any) {
      console.warn("[VoiceInput] Failed to start native speech, using Groq Whisper:", err);
      startCloudWhisperRecording();
    }
  };

  const isActive = isListening || isRecordingCloud;

  return (
    <div className="relative flex items-center gap-1.5">
      <button
        type="button"
        onClick={toggleListening}
        disabled={isGenerating || isTranscribing}
        title={
          isTranscribing
            ? "Transcribing voice via Groq Whisper..."
            : isActive
            ? "Listening... Click to stop and finish"
            : "Speak to dictation (Groq Whisper Turbo)"
        }
        className={`p-1.5 rounded-lg transition-all duration-200 flex items-center justify-center relative ${
          isTranscribing
            ? "bg-amber-50 text-amber-600 border border-amber-300"
            : isActive
            ? "bg-rose-500 text-white animate-pulse shadow-md shadow-rose-200 border border-rose-600"
            : "bg-slate-100 hover:bg-slate-200 text-slate-600 hover:text-indigo-600 border border-slate-200"
        }`}
      >
        {isTranscribing ? (
          <Loader2 className="w-4 h-4 animate-spin text-amber-600" />
        ) : isActive ? (
          <div className="flex items-center gap-1">
            <Radio className="w-4 h-4 animate-ping text-white" />
          </div>
        ) : (
          <Mic className="w-4 h-4" />
        )}
      </button>

      <button
        type="button"
        onClick={() => setAutoSend(!autoSend)}
        title={autoSend ? "Auto-Send: ON (Submits query right after speech ends)" : "Auto-Send: OFF"}
        className={`p-1.5 rounded-lg text-xs flex items-center gap-1 border transition-all ${
          autoSend
            ? "bg-indigo-50 text-indigo-700 border-indigo-300 font-semibold"
            : "bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200"
        }`}
      >
        <Sparkles className="w-3 h-3 text-indigo-500" />
        <span className="text-[10px] font-medium hidden sm:inline text-slate-700">Auto-Send</span>
      </button>

      {/* Floating Status & Fallback Indicator */}
      {statusMessage && (
        <div className="absolute bottom-full left-0 mb-2 w-64 p-2 bg-slate-900/90 backdrop-blur-md text-white border border-slate-700 rounded-lg text-[11px] shadow-lg flex items-start gap-1.5 z-50 animate-in fade-in">
          {isTranscribing ? (
            <Loader2 className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5 animate-spin" />
          ) : isActive ? (
            <Radio className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5 animate-pulse" />
          ) : (
            <Sparkles className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5" />
          )}
          <div className="flex-1 font-mono text-[10px] leading-relaxed">{statusMessage}</div>
          <button
            type="button"
            onClick={() => setStatusMessage(null)}
            className="text-slate-400 hover:text-white text-xs font-bold leading-none px-1"
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
};
