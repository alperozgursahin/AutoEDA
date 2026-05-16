import { lazy, Suspense, useMemo, useRef, useState } from "react";
import { AlertTriangle, Bot, CloudUpload, FileText, Gauge, RefreshCcw, Sparkles, Type, Copy } from "lucide-react";
import { executeCleaning, fetchReportHtml, fetchVisualizations, uploadDataset, fetchDetect } from "./api";
import { ResolutionModal } from "./components/ResolutionModal";

const MAX_FILE_SIZE_MB = 50;
const MAX_FILE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
const DataVisualization = lazy(() => import("./components/DataVisualization"));

function VisualizationFallback() {
  return (
    <section className="rounded-3xl border border-white/60 bg-white/70 p-6 shadow-lg backdrop-blur-xl">
      <div className="mb-4 h-5 w-56 animate-pulse rounded bg-slate-200" />
      <div className="grid gap-3 md:grid-cols-3">
        <div className="h-28 animate-pulse rounded-xl bg-slate-200" />
        <div className="h-28 animate-pulse rounded-xl bg-slate-200" />
        <div className="h-28 animate-pulse rounded-xl bg-slate-200" />
      </div>
    </section>
  );
}

// NOTE: Previous client-side mock — kept for fallback reference, not called anymore.
// Replaced by real backend integration (uploadDataset → fetchDetect).
/*
function generateMockSuggestionsFromCsv(csvText) {
  const lines = csvText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length < 2) {
    return [];
  }

  const headers = lines[0].split(",").map((h) => h.trim());
  const rows = lines.slice(1).map((line) => line.split(",").map((cell) => cell.trim()));
  const suggestions = [];

  headers.forEach((column, index) => {
    const values = rows.map((row) => row[index] ?? "");
    const nonEmptyValues = values.filter((value) => value !== "");
    const missingCount = values.filter((value) => value === "").length;
    const missingRatio = rows.length ? missingCount / rows.length : 0;
    const numericValues = values.filter((value) => value !== "" && !Number.isNaN(Number(value)));
    const numericRatio = values.length ? numericValues.length / values.length : 0;
    const trimmedValues = nonEmptyValues.map((value) => value.trim());
    const normalizedValues = trimmedValues.map((value) => value.toLowerCase());
    const uniqueTrimmed = new Set(trimmedValues).size;
    const uniqueNormalized = new Set(normalizedValues).size;

    if (missingRatio >= 0.6) {
      suggestions.push({
        id: `${column}-drop-column`,
        action: "drop_column",
        column,
        reason: `Missing ratio is ${(missingRatio * 100).toFixed(0)}%, so dropping this column is recommended.`,
        type: "missing_values",
        category: "missing_values",
        actionOptions: ["drop_column"],
      });
      return;
    }

    if (missingCount > 0 && numericRatio >= 0.6) {
      suggestions.push({
        id: `${column}-fill-median`,
        action: "fill_median",
        column,
        reason: `${missingCount} missing values detected. Median imputation is recommended for this numeric column.`,
        type: "missing_values",
        category: "missing_values",
        actionOptions: ["fill_mean", "fill_median", "fill_mode", "drop_missing_rows"],
      });
    } else if (missingCount > 0) {
      suggestions.push({
        id: `${column}-fill-mode`,
        action: "fill_mode",
        column,
        reason: `${missingCount} missing values detected. Mode imputation is recommended for this categorical column.`,
        type: "missing_values",
        category: "missing_values",
        actionOptions: ["fill_mean", "fill_median", "fill_mode", "drop_missing_rows"],
      });
    }

    if (numericRatio < 0.6 && nonEmptyValues.some((value) => value !== value.trim())) {
      suggestions.push({
        id: `${column}-trim-formatting`,
        action: "fill_mode",
        column,
        reason: "Detected extra whitespace and formatting inconsistencies. Normalize values before final execution.",
        type: "formatting_types",
        category: "formatting_types",
        actionOptions: ["fill_mode"],
      });
    }

    if (numericRatio < 0.5 && nonEmptyValues.length > 0 && values.length - numericValues.length > 0) {
      suggestions.push({
        id: `${column}-type-mismatch`,
        action: "fill_mode",
        column,
        reason: "Possible type mismatch detected in this column. Use a safe override before execution.",
        type: "formatting_types",
        category: "formatting_types",
        actionOptions: ["fill_mode", "drop_missing_rows"],
      });
    }

    if (numericValues.length >= 4) {
      const sorted = [...numericValues].map(Number).sort((a, b) => a - b);
      const q1 = sorted[Math.floor((sorted.length - 1) * 0.25)];
      const q3 = sorted[Math.floor((sorted.length - 1) * 0.75)];
      const iqr = q3 - q1;
      const lower = Number((q1 - 1.5 * iqr).toFixed(4));
      const upper = Number((q3 + 1.5 * iqr).toFixed(4));
      const hasOutlier = sorted.some((value) => value < lower || value > upper);
      if (hasOutlier) {
        suggestions.push({
          id: `${column}-outliers`,
          action: "clip_outliers",
          column,
          reason: `Potential outliers detected. Suggested bounds are ${lower} to ${upper}.`,
          type: "outliers",
          category: "outliers",
          lower_bound: lower,
          upper_bound: upper,
          actionOptions: ["clip_outliers", "drop_outliers"],
        });
      }
    }

    if (uniqueNormalized < uniqueTrimmed) {
      suggestions.push({
        id: `${column}-casing`,
        action: "fill_mode",
        column,
        reason: "Casing inconsistency detected (for example mixed upper/lower values).",
        type: "formatting_types",
        category: "formatting_types",
        actionOptions: ["fill_mode"],
      });
    }
  });

  const rowSignatures = rows.map((row) => row.join("||"));
  const uniqueSignatures = new Set(rowSignatures).size;
  if (uniqueSignatures < rowSignatures.length) {
    suggestions.push({
      id: "dataset-drop-duplicates",
      action: "drop_duplicates",
      column: "Dataset",
      reason: `Detected ${rowSignatures.length - uniqueSignatures} duplicate rows.`,
      type: "duplicates",
      category: "duplicates",
      actionOptions: ["drop_duplicates"],
    });
  }

  return suggestions;
}
*/

// Issue types that require the user to pick a standardization option before cleaning
const RESOLUTION_REQUIRED_TYPES = new Set([
  "DATE_FORMAT_INCONSISTENCY",
  "TURKISH_CHARACTER_MISMATCH",
  "NUMBER_FORMAT_INCONSISTENCY",
]);

function needsResolutionModal(item) {
  if (item.action !== "review_column") return false;
  if (RESOLUTION_REQUIRED_TYPES.has(item.issue_type)) return true;
  if (item.issue_type === "CONTACT_FORMAT_ISSUES" && item.metrics?.contact_type === "phone") return true;
  return false;
}

const ISSUE_TYPE_TO_CATEGORY = {
  missing_values: "missing_values",
  type_mismatch: "formatting_types",
  DUPLICATE_ROWS: "duplicates",
  CONSTANT_COLUMN: "formatting_types",
  ALL_NULL_COLUMN: "missing_values",
  HIGH_CARDINALITY: "formatting_types",
  MIXED_TYPES: "formatting_types",
  OUTLIERS_IQR: "outliers",
  SKEWED_DISTRIBUTION: "outliers",
  LOW_VARIANCE: "formatting_types",
  HIGH_CORRELATION: "formatting_types",
  DATE_FORMAT_INCONSISTENCY: "formatting_types",
  TURKISH_CHARACTER_MISMATCH: "formatting_types",
  WHITESPACE_ISSUES: "formatting_types",
  NUMBER_FORMAT_INCONSISTENCY: "formatting_types",
  CONTACT_FORMAT_ISSUES: "formatting_types",
  SEMANTIC_ENTITY_GROUPS: "semantic",
  UNIT_INCONSISTENCY: "semantic",
  MEANINGLESS_COLUMN_NAME: "formatting_types",
};

const ACTION_OPTIONS = {
  fill_median: ["fill_mean", "fill_median", "fill_mode", "drop_missing_rows"],
  fill_mean: ["fill_mean", "fill_median", "fill_mode", "drop_missing_rows"],
  drop_missing_rows: ["fill_mean", "fill_median", "fill_mode", "drop_missing_rows"],
  clip_outliers: ["clip_outliers", "drop_outliers"],
  drop_outliers: ["clip_outliers", "drop_outliers"],
};

function mapBackendSuggestion(s) {
  const action = s.suggested_action;
  return {
    id: s.suggestion_id,
    action,
    column: s.column || "Dataset",
    reason: s.explanation,
    issue_type: s.issue_type,
    type: s.issue_type,
    category: ISSUE_TYPE_TO_CATEGORY[s.issue_type] || "formatting_types",
    actionOptions: ACTION_OPTIONS[action] || [action],
    lower_bound: s.metrics?.lower_bound,
    upper_bound: s.metrics?.upper_bound,
    metrics: s.metrics || {},
    explanation: s.explanation,
  };
}

function parseReportStats(html) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");
  const scoreNodes = [...doc.querySelectorAll(".score")].map((node) => node.textContent ?? "");
  const preScore = scoreNodes[0] ?? "N/A";
  const postScore = scoreNodes[1] ?? "N/A";
  const statTexts = [...doc.querySelectorAll(".stat-box")].map((node) => node.textContent?.replace(/\s+/g, " ").trim() ?? "");

  return {
    preScore,
    postScore,
    statTexts,
  };
}

function suggestionLabel(item) {
  if (item.action === "drop_column") return `Drop column: ${item.column}`;
  if (item.action === "fill_median") return `Fill median: ${item.column}`;
  if (item.action === "fill_mode") return `Fill mode: ${item.column}`;
  return `${item.action}: ${item.column}`;
}

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function App() {
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [decisionMap, setDecisionMap] = useState({});
  const [datasetId, setDatasetId] = useState(1);
  const [inputFilePath, setInputFilePath] = useState("");
  const [taskId, setTaskId] = useState("");
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionError, setExecutionError] = useState("");
  const [reportHtml, setReportHtml] = useState("");
  const [reportName, setReportName] = useState("");
  const [showReportModal, setShowReportModal] = useState(false);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [statusMessage, setStatusMessage] = useState("Ready");
  const [statusType, setStatusType] = useState("idle");
  const [selectedActionMap, setSelectedActionMap] = useState({});
  const [visualizationData, setVisualizationData] = useState(null);
  const [visualizationError, setVisualizationError] = useState("");
  const [isVisualizationLoading, setIsVisualizationLoading] = useState(false);
  const [isDetecting, setIsDetecting] = useState(false);
  const [llmInfo, setLlmInfo] = useState(null);
  const [modalSuggestion, setModalSuggestion] = useState(null);
  const [resolutionParamsMap, setResolutionParamsMap] = useState({});
  const dragCounterRef = useRef(0);

  const approvedActions = useMemo(
    () =>
      suggestions
        .filter((item) => decisionMap[item.id] === "approved")
        .map((item) => {
          // Use resolved action+params if user configured via modal
          const resolution = resolutionParamsMap[item.id];
          if (resolution) {
            return { action: resolution.action, column: item.column, params: resolution.params };
          }
          const chosenAction = selectedActionMap[item.id] ?? item.action;
          const payload = { action: chosenAction, column: item.column };
          if (chosenAction === "clip_outliers" || chosenAction === "drop_outliers") {
            return {
              ...payload,
              lower_bound: item.lower_bound ?? -1000000,
              upper_bound: item.upper_bound ?? 1000000,
            };
          }
          return payload;
        }),
    [decisionMap, selectedActionMap, suggestions, resolutionParamsMap],
  );

  async function buildSuggestionsFromFile(nextFile) {
    setIsDetecting(true);
    setStatusMessage("Uploading and analyzing dataset...");
    setStatusType("loading");
    try {
      const { dataset_id, file_path } = await uploadDataset(nextFile);
      setDatasetId(dataset_id);
      setInputFilePath(file_path);
      const detectResult = await fetchDetect(dataset_id, file_path);
      const { suggestions: raw, llm_used, llm_model } = detectResult;
      setLlmInfo({ used: llm_used, model: llm_model });
      const mapped = raw.map(mapBackendSuggestion);
      setSuggestions(mapped);
      setDecisionMap(mapped.reduce((acc, item) => { acc[item.id] = "approved"; return acc; }, {}));
      setSelectedActionMap(mapped.reduce((acc, item) => { acc[item.id] = item.action; return acc; }, {}));
      setStatusMessage("Ready");
      setStatusType("idle");
      await loadVisualizations(dataset_id, file_path);
    } catch (error) {
      const detail = error?.response?.data?.detail;
      setExecutionError(detail || "Failed to upload or analyze dataset.");
      setStatusMessage("Error occurred.");
      setStatusType("error");
    } finally {
      setIsDetecting(false);
    }
  }

  async function loadVisualizations(nextDatasetId, nextInputPath) {
    if (!nextInputPath) return;
    setIsVisualizationLoading(true);
    setVisualizationError("");
    try {
      const data = await fetchVisualizations(nextDatasetId, nextInputPath);
      setVisualizationData(data);
    } catch (error) {
      const detail = error?.response?.data?.detail;
      setVisualizationError(detail || "Failed to load visualization data.");
    } finally {
      setIsVisualizationLoading(false);
    }
  }

  async function handleSelectedFile(selectedFile) {
    setExecutionError("");
    setDashboardStats(null);
    setReportHtml("");
    setTaskId("");
    setStatusMessage("Ready");
    setStatusType("idle");
    setVisualizationData(null);
    setVisualizationError("");
    setShowReportModal(false);

    if (!selectedFile) return;
    if (!selectedFile.name.toLowerCase().endsWith(".csv")) {
      setFile(null);
      setFileError("Only CSV files are supported.");
      return;
    }
    if (selectedFile.size > MAX_FILE_BYTES) {
      setFile(null);
      setFileError(`File size exceeds the ${MAX_FILE_SIZE_MB}MB limit.`);
      return;
    }

    setFile(selectedFile);
    setFileError("");
    await buildSuggestionsFromFile(selectedFile);
  }

  async function handleDrop(event) {
    event.stopPropagation();
    event.preventDefault();
    dragCounterRef.current = 0;
    setIsDragging(false);
    const droppedFile = event.dataTransfer.files?.[0];
    await handleSelectedFile(droppedFile);
  }

  function handleDragEnter(event) {
    event.preventDefault();
    event.stopPropagation();
    dragCounterRef.current += 1;
    setIsDragging(true);
  }

  function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    if (!isDragging) setIsDragging(true);
  }

  function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();
    dragCounterRef.current -= 1;
    if (dragCounterRef.current <= 0) {
      dragCounterRef.current = 0;
      setIsDragging(false);
    }
  }

  function handleStartOver() {
    dragCounterRef.current = 0;
    setFile(null);
    setFileError("");
    setIsDragging(false);
    setSuggestions([]);
    setDecisionMap({});
    setSelectedActionMap({});
    setInputFilePath("");
    setTaskId("");
    setIsExecuting(false);
    setExecutionError("");
    setReportHtml("");
    setReportName("");
    setShowReportModal(false);
    setDashboardStats(null);
    setStatusMessage("Ready");
    setStatusType("idle");
    setVisualizationData(null);
    setVisualizationError("");
    setIsVisualizationLoading(false);
    setLlmInfo(null);
    setModalSuggestion(null);
    setResolutionParamsMap({});
  }

  async function waitForReport(derivedReportName) {
    for (let attempt = 0; attempt < 30; attempt += 1) {
      try {
        setStatusMessage(`Waiting for report... attempt ${attempt + 1}/30`);
        setStatusType("loading");
        const html = await fetchReportHtml(derivedReportName);
        setStatusMessage("Report found.");
        setStatusType("success");
        return html;
      } catch {
        await sleep(2000);
      }
    }
    throw new Error("Report generation timed out.");
  }

  async function handleStartCleaning() {
    if (!inputFilePath.trim()) {
      setExecutionError("input_file_path is required.");
      setStatusType("error");
      return;
    }
    if (approvedActions.length === 0) {
      setExecutionError("Approve at least one suggestion before starting cleaning.");
      setStatusType("error");
      return;
    }

    setExecutionError("");
    setIsExecuting(true);
    setDashboardStats(null);
    setReportHtml("");
    setStatusMessage("Starting cleaning task...");
    setStatusType("loading");

    try {
      const response = await executeCleaning(datasetId, {
        input_file_path: inputFilePath.trim(),
        approved_actions: approvedActions,
      });

      setTaskId(response.task_id ?? "");
      setStatusMessage("Task created. Waiting for report...");
      setStatusType("loading");

      const datasetName = inputFilePath.replace(/^.*[\\/]/, "").replace(/\.[^/.]+$/, "");
      const nextReportName = `${datasetName}_report.html`;
      setReportName(nextReportName);

      const html = await waitForReport(nextReportName);
      const stats = parseReportStats(html);
      setDashboardStats(stats);
      setReportHtml(html);
      setStatusMessage("Success: cleaning completed.");
      setStatusType("success");
      await loadVisualizations(datasetId, inputFilePath.trim());
    } catch (error) {
      const detail = error?.response?.data?.detail;
      setExecutionError(detail || error.message || "Failed to start cleaning.");
      setStatusMessage("Error occurred.");
      setStatusType("error");
    } finally {
      setIsExecuting(false);
    }
  }

  const statusClasses =
    statusType === "success"
      ? "border-emerald-100 bg-emerald-50 text-emerald-800"
      : statusType === "error"
        ? "border-rose-100 bg-rose-50 text-rose-800"
        : statusType === "loading"
          ? "border-blue-100 bg-blue-50 text-blue-800"
          : "border-slate-200 bg-slate-50 text-slate-700";

  const groupedSuggestions = useMemo(() => {
    const groups = {
      missing_values: [],
      outliers: [],
      formatting_types: [],
      duplicates: [],
      semantic: [],
    };
    suggestions.forEach((item) => {
      const key = item.category || "missing_values";
      if (!groups[key]) groups[key] = [];
      groups[key].push(item);
    });
    return groups;
  }, [suggestions]);

  const suggestionGroupMeta = [
    { key: "missing_values", title: "Missing Values", icon: CloudUpload, tone: "text-blue-700" },
    { key: "outliers", title: "Outliers", icon: AlertTriangle, tone: "text-rose-700" },
    { key: "formatting_types", title: "Formatting & Types", icon: Type, tone: "text-violet-700" },
    { key: "duplicates", title: "Duplicates", icon: Copy, tone: "text-emerald-700" },
    { key: "semantic", title: "Semantic Issues", icon: Sparkles, tone: "text-amber-700" },
  ];

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-100 via-blue-50 to-slate-100 px-4 py-8">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <header className="rounded-3xl border border-white/60 bg-white/70 p-6 shadow-lg backdrop-blur-xl">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">AutoEDA Dashboard</p>
          <h1 className="mt-1 text-3xl font-bold text-slate-900">Intelligent Data Quality Analyzer</h1>
          <p className="mt-2 text-sm text-slate-600">
            Upload a CSV file, review AI cleaning suggestions, approve the right actions, and execute cleaning safely.
          </p>
        </header>

        <section className="grid gap-6 lg:grid-cols-3">
          <div className="rounded-3xl border border-white/60 bg-white/70 p-6 shadow-lg backdrop-blur-xl transition duration-300 hover:-translate-y-0.5 hover:shadow-xl lg:col-span-2">
            <div className="flex items-center gap-2">
              <CloudUpload className="h-5 w-5 text-blue-600" />
              <h2 className="text-lg font-semibold text-slate-800">1) Drag-and-Drop Upload Zone</h2>
            </div>
            <p className="mt-1 text-sm text-slate-500">CSV format only. Maximum file size: 50MB.</p>

            <div
              className={`mt-4 rounded-2xl border-2 border-dashed p-10 text-center transition duration-300 ${
                isDragging ? "border-blue-500 bg-blue-50/80" : "border-slate-300 bg-slate-50/70"
              }`}
              onDragEnter={handleDragEnter}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <p className="text-sm font-medium text-slate-700">Drag and drop your CSV file here, or choose a file</p>
              <input
                className="mx-auto mt-4 block rounded-lg text-sm"
                type="file"
                accept=".csv"
                onChange={async (event) => {
                  const selected = event.target.files?.[0];
                  await handleSelectedFile(selected);
                }}
              />
              {file && (
                <p className="mt-3 inline-flex rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">
                  Selected file: {file.name}
                </p>
              )}
              {isDetecting && (
                <p className="mt-3 flex items-center justify-center gap-2 text-sm font-medium text-blue-600">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
                  Uploading and analyzing...
                </p>
              )}
              {fileError && <p className="mt-3 text-sm font-medium text-rose-600">{fileError}</p>}
            </div>
          </div>

          <div className="rounded-3xl border border-white/60 bg-white/70 p-6 shadow-lg backdrop-blur-xl">
            <h2 className="text-lg font-semibold text-slate-800">Review Summary</h2>
            <div className="mt-4 space-y-3">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs text-slate-500">Total Suggestions</p>
                <p className="text-2xl font-bold text-slate-900">{suggestions.length}</p>
              </div>
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3">
                <p className="text-xs text-emerald-700">Approve</p>
                <p className="text-2xl font-bold text-emerald-900">{approvedActions.length}</p>
              </div>
              <div className="rounded-xl border border-rose-200 bg-rose-50 p-3">
                <p className="text-xs text-rose-700">Rejected</p>
                <p className="text-2xl font-bold text-rose-900">{Math.max(suggestions.length - approvedActions.length, 0)}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleStartOver}
              className="mt-4 inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              <RefreshCcw className="h-4 w-4" />
              Start Over / Upload New CSV
            </button>
          </div>
        </section>

        <section className="rounded-3xl border border-white/60 bg-white/70 p-6 shadow-lg backdrop-blur-xl transition duration-300 hover:shadow-xl">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-start gap-2">
              <Bot className="mt-0.5 h-5 w-5 text-violet-600" />
              <div>
                <h2 className="text-lg font-semibold text-slate-800">2) AI Suggestion Review Panel</h2>
                <p className="mt-1 text-sm text-slate-500">Review each mock AI action, choose Approve/Reject, then optionally override the action type.</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {llmInfo?.used ? (
                <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                  AI-powered · {llmInfo.model}
                </span>
              ) : llmInfo !== null ? (
                <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
                  Rule-based · AI unavailable
                </span>
              ) : null}
              <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
                Only approved actions are sent to the backend
              </span>
            </div>
          </div>

          <div className="mt-4 space-y-4">
            {suggestions.length === 0 && (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                Upload a CSV file to generate AI suggestions.
              </div>
            )}

            {suggestionGroupMeta.map((group) => {
              const items = groupedSuggestions[group.key] || [];
              const GroupIcon = group.icon;
              if (items.length === 0) return null;
              return (
                <section key={group.key} className="rounded-2xl border border-slate-200 bg-white/70 p-4">
                  <div className="mb-3 flex items-center gap-2">
                    <GroupIcon className={`h-4 w-4 ${group.tone}`} />
                    <h3 className="text-sm font-semibold text-slate-800">{group.title}</h3>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{items.length}</span>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    {items.map((item) => {
                      const state = decisionMap[item.id] ?? "approved";
                      return (
                        <article
                          key={item.id}
                          className={`rounded-2xl border p-4 transition duration-300 hover:scale-[1.01] hover:shadow-lg ${
                            state === "approved" ? "border-emerald-200 bg-emerald-50/60" : "border-rose-200 bg-rose-50/60"
                          }`}
                        >
                          <p className="text-sm font-semibold text-slate-900">{suggestionLabel(item)}</p>
                          <p className="mt-1 text-sm text-slate-600">{item.reason}</p>
                          <label className="mt-3 block text-xs font-semibold uppercase tracking-wide text-slate-500">
                            Action Override
                            <select
                              value={selectedActionMap[item.id] ?? item.action}
                              onChange={(event) =>
                                setSelectedActionMap((prev) => ({
                                  ...prev,
                                  [item.id]: event.target.value,
                                }))
                              }
                              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm text-slate-700"
                            >
                              {(item.actionOptions || [item.action]).map((option) => (
                                <option key={option} value={option}>
                                  {option}
                                </option>
                              ))}
                            </select>
                          </label>
                          <div className="mt-4 flex gap-2">
                            {needsResolutionModal(item) ? (
                              <button
                                type="button"
                                onClick={() => setModalSuggestion(item)}
                                className={`rounded-lg px-3 py-2 text-xs font-semibold transition-colors ${
                                  resolutionParamsMap[item.id]
                                    ? "bg-emerald-600 text-white"
                                    : "bg-violet-600 text-white hover:bg-violet-700"
                                }`}
                              >
                                {resolutionParamsMap[item.id] ? "✓ Configured" : "Configure →"}
                              </button>
                            ) : (
                              <button
                                type="button"
                                onClick={() => setDecisionMap((prev) => ({ ...prev, [item.id]: "approved" }))}
                                className={`rounded-lg px-3 py-2 text-xs font-semibold ${
                                  state === "approved"
                                    ? "bg-emerald-600 text-white"
                                    : "bg-white text-emerald-700 ring-1 ring-emerald-300"
                                }`}
                              >
                                Approve
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() => setDecisionMap((prev) => ({ ...prev, [item.id]: "rejected" }))}
                              className={`rounded-lg px-3 py-2 text-xs font-semibold ${
                                state === "rejected" ? "bg-rose-600 text-white" : "bg-white text-rose-700 ring-1 ring-rose-300"
                              }`}
                            >
                              Reject
                            </button>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                </section>
              );
            })}
          </div>
        </section>

        <section className="rounded-3xl border border-white/60 bg-white/70 p-6 shadow-lg backdrop-blur-xl transition duration-300 hover:shadow-xl">
          <div className="flex items-center gap-2">
            <Gauge className="h-5 w-5 text-indigo-600" />
            <h2 className="text-lg font-semibold text-slate-800">3) Interactive Dashboard</h2>
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="text-sm font-medium text-slate-700">
              Dataset ID
              <input
                type="number"
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                value={datasetId}
                onChange={(e) => setDatasetId(Number(e.target.value) || 1)}
              />
            </label>
            <label className="text-sm font-medium text-slate-700">
              input_file_path
              <input
                type="text"
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                value={inputFilePath}
                onChange={(e) => setInputFilePath(e.target.value)}
                placeholder="test.csv"
              />
            </label>
          </div>

          <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-semibold text-slate-500">PAYLOAD PREVIEW</p>
            <p className="mt-1 font-mono text-xs text-slate-700">{JSON.stringify(approvedActions)}</p>
          </div>
          <div className={`mt-3 rounded-lg border p-3 text-sm ${statusClasses}`}>Status: {statusMessage}</div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              disabled={isExecuting || approvedActions.length === 0}
              onClick={handleStartCleaning}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isExecuting && <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />}
              Start Cleaning
            </button>
            {taskId && <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700">Task ID: {taskId}</span>}
          </div>

          {executionError && <p className="mt-3 text-sm font-medium text-rose-600">{executionError}</p>}
          {isExecuting && (
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="h-16 animate-pulse rounded-xl bg-slate-200" />
              <div className="h-16 animate-pulse rounded-xl bg-slate-200" />
              <div className="h-16 animate-pulse rounded-xl bg-slate-200" />
            </div>
          )}

          {dashboardStats && (
            <div className="mt-5 grid gap-4 md:grid-cols-3">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs text-slate-500">Pre-Cleaning Score</p>
                <p className="mt-1 text-xl font-bold text-slate-900">{dashboardStats.preScore}</p>
              </div>
              <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
                <p className="text-xs text-blue-700">Post-Cleaning Score</p>
                <p className="mt-1 text-xl font-bold text-blue-900">{dashboardStats.postScore}</p>
              </div>
              <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-4">
                <div className="flex items-center gap-2 text-xs text-indigo-700">
                  <FileText className="h-4 w-4" />
                  Report
                </div>
                <button
                  type="button"
                  onClick={() => setShowReportModal(true)}
                  className="mt-2 rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white"
                >
                  View Full Report ({reportName})
                </button>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4 md:col-span-3">
                <p className="mb-2 text-sm font-semibold text-slate-700">Profiling Statistics</p>
                <ul className="grid gap-2 text-sm text-slate-700 md:grid-cols-2">
                  {dashboardStats.statTexts.map((text) => (
                    <li key={text} className="rounded-lg bg-slate-50 p-2">
                      {text}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </section>

        <Suspense fallback={<VisualizationFallback />}>
          <DataVisualization
            visualizationData={visualizationData}
            isLoading={isVisualizationLoading}
            error={visualizationError}
          />
        </Suspense>
      </div>

      {showReportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="flex h-[85vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-white/50 bg-white shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-blue-600" />
                <h3 className="font-semibold text-slate-900">Full HTML Report</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowReportModal(false)}
                className="rounded-md bg-slate-100 px-3 py-1 text-sm text-slate-700"
              >
                Close
              </button>
            </div>
            <iframe title="AutoEDA Report" className="h-full w-full" srcDoc={reportHtml} />
          </div>
        </div>
      )}

      {modalSuggestion && (
        <ResolutionModal
          suggestion={modalSuggestion}
          onConfirm={(action, params) => {
            setResolutionParamsMap((prev) => ({
              ...prev,
              [modalSuggestion.id]: { action, params },
            }));
            setDecisionMap((prev) => ({ ...prev, [modalSuggestion.id]: "approved" }));
            setModalSuggestion(null);
          }}
          onClose={() => setModalSuggestion(null)}
        />
      )}
    </main>
  );
}

export default App;
