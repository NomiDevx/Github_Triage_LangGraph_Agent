"use client";

import { useEffect, useState } from "react";
import {
  AlertCircle,
  Bug,
  CheckCircle2,
  Clock,
  Code2,
  Copy,
  ExternalLink,
  FileCode,
  FileText,
  FolderGit2,
  HelpCircle,
  Play,
  RotateCcw,
  Search,
  Sparkles,
  Terminal,
} from "lucide-react";

interface SampleIssue {
  id: string;
  label: string;
  category: string;
  codeDir: string;
  title: string;
  body: string;
}

interface TriageResponse {
  category: "bug" | "feature_request" | "question" | "docs" | null;
  confidence: number | null;
  reasoning: string | null;
  is_complete: boolean | null;
  missing_fields: string[] | null;
  draft_reply: string | null;
  likely_files: string[];
  summary: string;
}

interface EvalSample {
  id: number;
  title: string;
  expected_category: string;
  predicted_category: string;
  confidence: number;
  reasoning: string;
  is_complete: boolean | null;
  expected_is_complete: boolean | null;
  match: boolean;
}

interface EvalData {
  total_samples: number;
  correct_classifications: number;
  accuracy: number;
  total_time_seconds: number;
  categories: string[];
  confusion_matrix: Record<string, Record<string, number>>;
  samples: EvalSample[];
  completeness_accuracy: number | null;
}

export default function Home() {
  const [activeTab, setActiveTab] = useState<"workspace" | "evals">("workspace");

  // Form State
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [codeDir, setCodeDir] = useState("sample_repo");
  const [samples, setSamples] = useState<SampleIssue[]>([]);

  // Triage Execution State
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TriageResponse | null>(null);
  const [traceLog, setTraceLog] = useState<string | null>(null);
  const [copiedReply, setCopiedReply] = useState(false);
  const [rawView, setRawView] = useState<"visual" | "json" | "logs">("visual");

  // Evals Execution State
  const [evalLoading, setEvalLoading] = useState(false);
  const [evalData, setEvalData] = useState<EvalData | null>(null);
  const [evalError, setEvalError] = useState<string | null>(null);

  // Load sample issues on mount
  useEffect(() => {
    fetch("/api/samples")
      .then((res) => res.json())
      .then((data) => {
        if (data.samples && data.samples.length > 0) {
          setSamples(data.samples);
          // Default to the first sample (Complete Bug)
          setTitle(data.samples[0].title);
          setBody(data.samples[0].body);
          setCodeDir(data.samples[0].codeDir || "sample_repo");
        }
      })
      .catch((err) => console.error("Failed to load samples", err));
  }, []);

  const handleSelectSample = (sample: SampleIssue) => {
    setTitle(sample.title);
    setBody(sample.body);
    setCodeDir(sample.codeDir || "");
    setResult(null);
    setError(null);
  };

  const handleTriage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setTraceLog(null);

    try {
      const res = await fetch("/api/triage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title.trim(),
          body: body.trim(),
          codeDir: codeDir.trim() || undefined,
        }),
      });

      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.details || json.error || "Triage execution failed");
      }

      setResult(json.data);
      setTraceLog(json.trace_log);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleRunEvals = async () => {
    setEvalLoading(true);
    setEvalError(null);
    try {
      const res = await fetch("/api/evals", { method: "POST" });
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.details || json.error || "Eval run failed");
      }
      setEvalData(json.data);
    } catch (err: unknown) {
      setEvalError(err instanceof Error ? err.message : String(err));
    } finally {
      setEvalLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedReply(true);
    setTimeout(() => setCopiedReply(false), 2000);
  };

  const getCategoryBadge = (category: string | null) => {
    switch (category) {
      case "bug":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30">
            <Bug className="w-3.5 h-3.5" /> Bug
          </span>
        );
      case "feature_request":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-400 border border-purple-500/30">
            <Sparkles className="w-3.5 h-3.5" /> Feature Request
          </span>
        );
      case "question":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-sky-500/20 text-sky-400 border border-sky-500/30">
            <HelpCircle className="w-3.5 h-3.5" /> Question
          </span>
        );
      case "docs":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30">
            <FileText className="w-3.5 h-3.5" /> Documentation
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400">
            Unknown
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-900/50 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <FolderGit2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                GitHub Issue Triage
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  LangGraph Agent
                </span>
              </h1>
              <p className="text-xs text-slate-400">
                Powered by DeepSeek & Local Sandboxed Code Search
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab("workspace")}
              className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "workspace"
                  ? "bg-slate-800 text-white shadow-sm border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Triage Workspace
            </button>
            <button
              onClick={() => setActiveTab("evals")}
              className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === "evals"
                  ? "bg-slate-800 text-white shadow-sm border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Benchmark & Evals
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {activeTab === "workspace" ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Left Column: Issue Input Form */}
            <div className="lg:col-span-5 flex flex-col gap-5">
              <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-xl">
                <div className="mb-4">
                  <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2">
                    Quick Sample Presets
                  </label>
                  <div className="flex flex-wrap gap-1.5">
                    {samples.map((s) => (
                      <button
                        key={s.id}
                        type="button"
                        onClick={() => handleSelectSample(s)}
                        className={`text-xs px-2.5 py-1 rounded-md font-medium transition border ${
                          title === s.title
                            ? "bg-indigo-600/30 text-indigo-300 border-indigo-500/50"
                            : "bg-slate-800/60 text-slate-300 border-slate-700/60 hover:bg-slate-800 hover:text-white"
                        }`}
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                </div>

                <form onSubmit={handleTriage} className="space-y-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                      Issue Title <span className="text-rose-400">*</span>
                    </label>
                    <input
                      type="text"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="e.g. AttributeError when processing empty list"
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition"
                      required
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                      Issue Body
                    </label>
                    <textarea
                      value={body}
                      onChange={(e) => setBody(e.target.value)}
                      rows={8}
                      placeholder="Paste issue details, environment, stack trace, or reproduction steps..."
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3.5 text-sm text-slate-100 placeholder-slate-500 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition resize-y"
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-xs font-semibold text-slate-300">
                        Local Code Directory
                      </label>
                      <span className="text-[11px] text-slate-500">
                        Sandboxed search for bugs
                      </span>
                    </div>
                    <div className="relative">
                      <input
                        type="text"
                        value={codeDir}
                        onChange={(e) => setCodeDir(e.target.value)}
                        placeholder="e.g. sample_repo or path/to/project"
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 pl-9 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition font-mono text-xs"
                      />
                      <Code2 className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading || !title.trim()}
                    className="w-full mt-2 py-3 px-4 rounded-xl font-semibold text-sm bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-400 hover:to-indigo-500 text-white shadow-lg shadow-indigo-500/25 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Triaging with LangGraph Agent...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 fill-white" />
                        <span>Run Triage Graph</span>
                      </>
                    )}
                  </button>
                </form>
              </div>

              {/* Security info card */}
              <div className="rounded-xl border border-slate-800/60 bg-slate-900/30 p-4 text-xs text-slate-400 space-y-1.5">
                <div className="flex items-center gap-2 font-semibold text-slate-300">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  Read-Only & Sandboxed Safety Guarantees
                </div>
                <p>
                  The system <strong>only suggests</strong> and never writes to GitHub,
                  deletes files, or escapes the configured local folder. Traversal tricks
                  (<code className="text-slate-300">../</code>), symlinks, and sensitive files
                  (<code className="text-slate-300">.env</code>, <code className="text-slate-300">.git</code>)
                  are refused.
                </p>
              </div>
            </div>

            {/* Right Column: Interactive Results Card */}
            <div className="lg:col-span-7 flex flex-col gap-4">
              {error && (
                <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400 mt-0.5" />
                  <div>
                    <p className="font-semibold">Triage Execution Error</p>
                    <p className="text-xs text-rose-400 mt-1 whitespace-pre-wrap">{error}</p>
                  </div>
                </div>
              )}

              {loading && (
                <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-8 flex flex-col items-center justify-center text-center">
                  <div className="relative w-16 h-16 mb-4">
                    <div className="absolute inset-0 rounded-full border-4 border-indigo-500/20 animate-ping" />
                    <div className="w-16 h-16 rounded-full border-4 border-indigo-500/30 border-t-indigo-500 animate-spin flex items-center justify-center">
                      <FolderGit2 className="w-6 h-6 text-indigo-400 animate-pulse" />
                    </div>
                  </div>
                  <h3 className="text-base font-semibold text-slate-200">
                    Executing LangGraph Workflow
                  </h3>
                  <p className="text-xs text-slate-400 max-w-sm mt-1">
                    Classifying issue category, testing completeness, and initiating
                    read-only tool-calling code search agent if bug...
                  </p>
                </div>
              )}

              {!loading && !result && !error && (
                <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/20 p-12 flex flex-col items-center justify-center text-center">
                  <div className="w-12 h-12 rounded-2xl bg-slate-800/80 flex items-center justify-center text-slate-400 mb-3">
                    <Search className="w-6 h-6" />
                  </div>
                  <h3 className="text-sm font-semibold text-slate-300">
                    No Triage Result Yet
                  </h3>
                  <p className="text-xs text-slate-500 max-w-xs mt-1">
                    Select a preset or enter an issue title and click &quot;Run Triage
                    Graph&quot; to inspect the suggestion.
                  </p>
                </div>
              )}

              {result && (
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
                  {/* Result Header Bar */}
                  <div className="border-b border-slate-800 px-6 py-4 flex items-center justify-between bg-slate-900/90">
                    <div className="flex items-center gap-3">
                      {getCategoryBadge(result.category)}
                      {result.confidence !== null && (
                        <span className="text-xs font-mono text-slate-400">
                          {(result.confidence * 100).toFixed(0)}% confidence
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
                      <button
                        onClick={() => setRawView("visual")}
                        className={`px-2.5 py-1 text-xs rounded-md font-medium transition ${
                          rawView === "visual"
                            ? "bg-slate-800 text-white"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        Visual
                      </button>
                      <button
                        onClick={() => setRawView("json")}
                        className={`px-2.5 py-1 text-xs rounded-md font-medium transition ${
                          rawView === "json"
                            ? "bg-slate-800 text-white"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        JSON
                      </button>
                      {traceLog && (
                        <button
                          onClick={() => setRawView("logs")}
                          className={`px-2.5 py-1 text-xs rounded-md font-medium transition ${
                            rawView === "logs"
                              ? "bg-slate-800 text-white"
                              : "text-slate-400 hover:text-slate-200"
                          }`}
                        >
                          Trace
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Body Content */}
                  <div className="p-6 space-y-6">
                    {rawView === "visual" && (
                      <>
                        {/* Reasoning */}
                        <div>
                          <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-1.5">
                            Classification Reasoning
                          </label>
                          <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 text-sm text-slate-200 leading-relaxed">
                            {result.reasoning || "No reasoning provided."}
                          </div>
                        </div>

                        {/* Completeness Section (Bugs) */}
                        {result.is_complete !== null && (
                          <div>
                            <div className="flex items-center justify-between mb-2">
                              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                                Information Completeness Check
                              </label>
                              {result.is_complete ? (
                                <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-400">
                                  <CheckCircle2 className="w-3.5 h-3.5" /> All required info present
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-xs font-semibold text-amber-400">
                                  <AlertCircle className="w-3.5 h-3.5" /> Missing critical information
                                </span>
                              )}
                            </div>

                            {/* Missing Fields list */}
                            {result.missing_fields && result.missing_fields.length > 0 && (
                              <div className="flex items-center gap-2 mb-3">
                                <span className="text-xs text-slate-400">Missing fields:</span>
                                {result.missing_fields.map((field) => (
                                  <span
                                    key={field}
                                    className="px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-mono"
                                  >
                                    {field}
                                  </span>
                                ))}
                              </div>
                            )}

                            {/* Draft Reply */}
                            {result.draft_reply && (
                              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                                <div className="flex items-center justify-between mb-2">
                                  <span className="text-xs font-semibold text-slate-300">
                                    Suggested Polite Reply
                                  </span>
                                  <button
                                    onClick={() => copyToClipboard(result.draft_reply!)}
                                    className="inline-flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-medium transition"
                                  >
                                    {copiedReply ? (
                                      <>
                                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                                        <span className="text-emerald-400">Copied!</span>
                                      </>
                                    ) : (
                                      <>
                                        <Copy className="w-3.5 h-3.5" />
                                        <span>Copy Reply</span>
                                      </>
                                    )}
                                  </button>
                                </div>
                                <p className="text-xs text-slate-300 leading-relaxed italic bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                                  &ldquo;{result.draft_reply}&rdquo;
                                </p>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Code Search Findings (Bugs) */}
                        {result.category === "bug" && (
                          <div>
                            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-2">
                              Agent Code Search Findings
                            </label>

                            {result.likely_files && result.likely_files.length > 0 ? (
                              <div className="space-y-3">
                                <div className="space-y-1.5">
                                  {result.likely_files.map((file) => (
                                    <div
                                      key={file}
                                      className="flex items-center gap-2.5 p-2.5 rounded-xl bg-slate-950/80 border border-slate-800 font-mono text-xs text-indigo-300"
                                    >
                                      <FileCode className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                                      <span className="truncate">{file}</span>
                                    </div>
                                  ))}
                                </div>

                                {result.summary && (
                                  <div className="p-3.5 rounded-xl bg-indigo-950/20 border border-indigo-800/30 text-xs text-indigo-200/90 leading-relaxed">
                                    <p className="font-semibold text-indigo-300 mb-1">
                                      Bug Root-Cause Analysis:
                                    </p>
                                    {result.summary}
                                  </div>
                                )}
                              </div>
                            ) : (
                              <div className="p-3.5 rounded-xl bg-slate-950/40 border border-slate-800/60 text-xs text-slate-400">
                                {result.summary || "No specific files identified."}
                              </div>
                            )}
                          </div>
                        )}
                      </>
                    )}

                    {rawView === "json" && (
                      <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-emerald-400 font-mono text-xs overflow-x-auto max-h-96">
                        {JSON.stringify(result, null, 2)}
                      </pre>
                    )}

                    {rawView === "logs" && (
                      <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-slate-400 font-mono text-xs overflow-x-auto max-h-96 whitespace-pre-wrap">
                        {traceLog || "No logs recorded."}
                      </pre>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Evaluation / Benchmark Tab */
          <div className="space-y-6">
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  Dataset Benchmark & Confusion Matrix
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Evaluates 10 ground-truth issues across bug, feature_request, question,
                  and docs.
                </p>
              </div>

              <button
                onClick={handleRunEvals}
                disabled={evalLoading}
                className="py-2.5 px-4 rounded-xl font-semibold text-xs bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/25 transition disabled:opacity-50 flex items-center gap-2"
              >
                {evalLoading ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Running Evals Suite...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 fill-white" />
                    <span>Run Evaluation Suite</span>
                  </>
                )}
              </button>
            </div>

            {evalError && (
              <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                {evalError}
              </div>
            )}

            {evalData && (
              <div className="space-y-6">
                {/* Metric Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
                      Overall Accuracy
                    </span>
                    <span className="text-2xl font-bold text-emerald-400 mt-1 block">
                      {evalData.accuracy}%
                    </span>
                    <span className="text-xs text-slate-500">
                      {evalData.correct_classifications} of {evalData.total_samples} correct
                    </span>
                  </div>

                  <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
                      Completeness Check
                    </span>
                    <span className="text-2xl font-bold text-indigo-400 mt-1 block">
                      {evalData.completeness_accuracy ?? 100}%
                    </span>
                    <span className="text-xs text-slate-500">Bug completeness precision</span>
                  </div>

                  <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
                      Total Latency
                    </span>
                    <span className="text-2xl font-bold text-white mt-1 block">
                      {evalData.total_time_seconds}s
                    </span>
                    <span className="text-xs text-slate-500">
                      {(evalData.total_time_seconds / evalData.total_samples).toFixed(2)}s / sample
                    </span>
                  </div>

                  <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
                      Categories
                    </span>
                    <span className="text-2xl font-bold text-cyan-400 mt-1 block">
                      {evalData.categories.length}
                    </span>
                    <span className="text-xs text-slate-500">4-way classification</span>
                  </div>
                </div>

                {/* Confusion Matrix Table */}
                <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5">
                  <h3 className="text-sm font-semibold text-slate-200 mb-3">
                    Confusion Matrix (Rows: Expected, Columns: Predicted)
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs font-mono text-left">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400">
                          <th className="py-2.5 px-3">Expected \ Pred</th>
                          {evalData.categories.map((c) => (
                            <th key={c} className="py-2.5 px-3 text-center">
                              {c}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {evalData.categories.map((actual) => (
                          <tr key={actual} className="border-b border-slate-800/60">
                            <td className="py-2.5 px-3 font-semibold text-slate-300">
                              {actual}
                            </td>
                            {evalData.categories.map((pred) => {
                              const count = evalData.confusion_matrix[actual]?.[pred] ?? 0;
                              const isDiagonal = actual === pred;
                              return (
                                <td
                                  key={pred}
                                  className={`py-2.5 px-3 text-center font-bold ${
                                    isDiagonal && count > 0
                                      ? "bg-emerald-500/10 text-emerald-400"
                                      : count > 0
                                      ? "bg-rose-500/10 text-rose-400"
                                      : "text-slate-600"
                                  }`}
                                >
                                  {count}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Detailed Sample Results */}
                <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5">
                  <h3 className="text-sm font-semibold text-slate-200 mb-3">
                    Evaluated Dataset Samples
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400 font-mono">
                          <th className="py-2 px-3">ID</th>
                          <th className="py-2 px-3">Match</th>
                          <th className="py-2 px-3">Expected</th>
                          <th className="py-2 px-3">Predicted</th>
                          <th className="py-2 px-3">Conf</th>
                          <th className="py-2 px-3">Title</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/50">
                        {evalData.samples.map((s) => (
                          <tr key={s.id} className="hover:bg-slate-800/30 transition">
                            <td className="py-2.5 px-3 font-mono text-slate-500">{s.id}</td>
                            <td className="py-2.5 px-3">
                              {s.match ? (
                                <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                                  PASS
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-[11px] font-bold text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded">
                                  FAIL
                                </span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 font-mono text-slate-400">
                              {s.expected_category}
                            </td>
                            <td className="py-2.5 px-3 font-mono font-semibold text-slate-200">
                              {s.predicted_category}
                            </td>
                            <td className="py-2.5 px-3 font-mono text-slate-400">
                              {(s.confidence * 100).toFixed(0)}%
                            </td>
                            <td className="py-2.5 px-3 text-slate-300 max-w-xs truncate">
                              {s.title}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
