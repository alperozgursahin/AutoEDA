import { useState } from "react";
import { X, Settings } from "lucide-react";

// ── Modal configs per issue type ──────────────────────────────────────────────

const MODAL_CONFIGS = {
  DATE_FORMAT_INCONSISTENCY: {
    title: "Standardize Date Format",
    action: "standardize_date_format",
    description: "Choose which date format to use as the canonical standard for this column.",
    options: [
      {
        label: "YYYY-MM-DD",
        example: "e.g., 2023-03-15",
        description: "ISO 8601 — universally recognized, ideal for databases and APIs.",
        param: { target_format: "YYYY-MM-DD" },
        recommended: true,
      },
      {
        label: "DD/MM/YYYY",
        example: "e.g., 15/03/2023",
        description: "European / Turkish standard.",
        param: { target_format: "DD/MM/YYYY" },
      },
      {
        label: "MM/DD/YYYY",
        example: "e.g., 03/15/2023",
        description: "American standard.",
        param: { target_format: "MM/DD/YYYY" },
      },
    ],
    defaultIndex: 0,
  },

  TURKISH_CHARACTER_MISMATCH: {
    title: "Normalize Turkish Characters",
    action: "normalize_turkish_chars",
    description:
      "Values like 'şırnak' and 'sirnak' are treated as different entries. Choose how to unify them.",
    options: [
      {
        label: "ASCII / Latin characters",
        example: "şırnak → sirnak, İzmir → izmir",
        description:
          "Converts all Turkish diacritics to ASCII equivalents and lowercases everything. Fully resolves all mismatches.",
        param: { target: "ascii" },
        recommended: true,
      },
      {
        label: "Lowercase only",
        example: "Şırnak → şırnak, İZMİR → i̇zmir",
        description:
          "Keeps Turkish characters but normalizes case. May not fully merge ASCII-spelled variants.",
        param: { target: "lowercase" },
      },
    ],
    defaultIndex: 0,
  },

  NUMBER_FORMAT_INCONSISTENCY: {
    title: "Standardize Number Format",
    action: "standardize_number_format",
    description:
      "European (1.234,56) and American (1,234.56) number formats are mixed. Choose one standard.",
    options: [
      {
        label: "American  —  1,234.56",
        example: "dot as decimal separator",
        description: "Standard for most programming languages, databases, and international datasets.",
        param: { target: "american" },
        recommended: true,
      },
      {
        label: "European  —  1.234,56",
        example: "comma as decimal separator",
        description: "Use if data will be consumed in a European locale system.",
        param: { target: "european" },
      },
    ],
    defaultIndex: 0,
  },
};

function phoneConfig() {
  return {
    title: "Standardize Phone Format",
    action: "standardize_phone_format",
    description: "Multiple phone number formats detected. Choose a single target format.",
    options: [
      {
        label: "International  —  +90-XXXXXXXXXX",
        example: "e.g., +90-5001234567",
        description: "Full international format with country code. Recommended for global datasets.",
        param: { target_prefix: "international" },
        recommended: true,
      },
      {
        label: "Local  —  0XXXXXXXXXX",
        example: "e.g., 05001234567",
        description: "Turkish local format with leading zero.",
        param: { target_prefix: "local" },
      },
      {
        label: "Plain  —  5XXXXXXXXXX",
        example: "e.g., 5001234567",
        description: "Subscriber number only, no prefix.",
        param: { target_prefix: "plain" },
      },
    ],
    defaultIndex: 0,
  };
}

function getConfig(suggestion) {
  if (
    suggestion.issue_type === "CONTACT_FORMAT_ISSUES" &&
    suggestion.metrics?.contact_type === "phone"
  ) {
    return phoneConfig();
  }
  return MODAL_CONFIGS[suggestion.issue_type] ?? null;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ResolutionModal({ suggestion, onConfirm, onClose }) {
  const config = getConfig(suggestion);
  const [selectedIndex, setSelectedIndex] = useState(config?.defaultIndex ?? 0);

  if (!config) return null;

  function handleConfirm() {
    const selected = config.options[selectedIndex];
    onConfirm(config.action, selected.param);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-200">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Settings className="h-4 w-4 text-violet-600" />
            <h2 className="text-base font-semibold text-slate-800">{config.title}</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5">
          {/* Context card */}
          <div className="mb-5 rounded-xl border border-violet-100 bg-violet-50 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-violet-500 mb-1">
              Column: {suggestion.column}
            </p>
            <p className="text-sm text-slate-700">{suggestion.explanation || suggestion.reason}</p>
          </div>

          {/* Instruction */}
          <p className="mb-3 text-sm font-medium text-slate-700">{config.description}</p>

          {/* Options */}
          <div className="space-y-2">
            {config.options.map((opt, idx) => (
              <label
                key={idx}
                className={`flex cursor-pointer items-start gap-3 rounded-xl border px-4 py-3 transition-all ${
                  selectedIndex === idx
                    ? "border-violet-400 bg-violet-50 shadow-sm"
                    : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                <input
                  type="radio"
                  name="resolution"
                  className="mt-1 accent-violet-600"
                  checked={selectedIndex === idx}
                  onChange={() => setSelectedIndex(idx)}
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-slate-800">{opt.label}</span>
                    {opt.recommended && (
                      <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                        Recommended
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 text-xs text-slate-500 font-mono">{opt.example}</p>
                  <p className="mt-1 text-xs text-slate-500">{opt.description}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-slate-100 bg-slate-50/50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800 rounded-lg hover:bg-slate-100 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            className="px-5 py-2 text-sm font-semibold rounded-lg bg-violet-600 text-white hover:bg-violet-700 active:bg-violet-800 transition-colors shadow-sm"
          >
            Apply & Approve
          </button>
        </div>
      </div>
    </div>
  );
}
