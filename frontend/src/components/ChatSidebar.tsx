"use client";

import { useEffect, useState, type FormEvent } from "react";
import type { ChatMessage } from "@/lib/api";

const SendIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    className="h-4 w-4"
  >
    <path d="M3.105 2.289a.75.75 0 00-.826.95l1.414 4.925A1.5 1.5 0 005.135 9.25h6.115a.75.75 0 010 1.5H5.135a1.5 1.5 0 00-1.442 1.086l-1.414 4.926a.75.75 0 00.826.95 28.896 28.896 0 0015.293-7.154.75.75 0 000-1.115A28.897 28.897 0 003.105 2.289z" />
  </svg>
);

const SparklesIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    className="h-4 w-4"
  >
    <path d="M15.98 1.804a1 1 0 00-1.96 0l-.24 1.192a1 1 0 01-.784.785l-1.192.238a1 1 0 000 1.962l1.192.238a1 1 0 01.785.785l.238 1.192a1 1 0 001.962 0l.238-1.192a1 1 0 01.785-.785l1.192-.238a1 1 0 000-1.962l-1.192-.238a1 1 0 01-.785-.785l-.238-1.192zM6.949 5.684a1 1 0 00-1.898 0l-.683 2.051a1 1 0 01-.633.633l-2.051.683a1 1 0 000 1.898l2.051.684a1 1 0 01.633.632l.683 2.051a1 1 0 001.898 0l.683-2.051a1 1 0 01.633-.633l2.051-.683a1 1 0 000-1.898l-2.051-.683a1 1 0 01-.633-.633L6.95 5.684zM13.949 13.684a1 1 0 00-1.898 0l-.184.551a1 1 0 01-.632.633l-.551.183a1 1 0 000 1.898l.551.183a1 1 0 01.633.633l.183.551a1 1 0 001.898 0l.184-.551a1 1 0 01.632-.633l.551-.183a1 1 0 000-1.898l-.551-.184a1 1 0 01-.633-.632l-.183-.551z" />
  </svg>
);

const FREE_MODELS = [
  { id: "openai/gpt-oss-120b:free", label: "GPT-OSS 120B (OpenAI)" },
  { id: "openai/gpt-oss-20b:free", label: "GPT-OSS 20B (OpenAI)" },
  { id: "meta-llama/llama-3.3-70b-instruct:free", label: "Llama 3.3 70B (Meta)" },
  { id: "meta-llama/llama-3.2-3b-instruct:free", label: "Llama 3.2 3B (Meta)" },
  { id: "nvidia/nemotron-3-super-120b-a12b:free", label: "Nemotron Super 120B (NVIDIA)" },
  { id: "qwen/qwen3-coder:free", label: "Qwen3 Coder" },
  { id: "nousresearch/hermes-3-llama-3.1-405b:free", label: "Hermes 3 405B" },
];

const MODEL_STORAGE_KEY = "pm_chat_model";
const DEFAULT_MODEL = FREE_MODELS[0].id;

function getStoredModel(): { preset: string; custom: string } {
  if (typeof window === "undefined") return { preset: DEFAULT_MODEL, custom: "" };
  const stored = localStorage.getItem(MODEL_STORAGE_KEY);
  if (!stored) return { preset: DEFAULT_MODEL, custom: "" };
  const isPreset = FREE_MODELS.some((m) => m.id === stored);
  return isPreset ? { preset: stored, custom: "" } : { preset: "other", custom: stored };
}

export type RetryStatus = {
  attempt: number;
  maxAttempts: number;
  countdown: number;
} | null;

type ChatSidebarProps = {
  messages: ChatMessage[];
  onSend: (message: string, model: string) => void;
  isSending?: boolean;
  error?: string | null;
  retryStatus?: RetryStatus;
};

export const ChatSidebar = ({
  messages,
  onSend,
  isSending = false,
  error,
  retryStatus,
}: ChatSidebarProps) => {
  const [message, setMessage] = useState("");
  const [selectedPreset, setSelectedPreset] = useState<string>(DEFAULT_MODEL);
  const [customModel, setCustomModel] = useState<string>("");

  useEffect(() => {
    const stored = getStoredModel();
    setSelectedPreset(stored.preset);
    setCustomModel(stored.custom);
  }, []);

  const effectiveModel =
    selectedPreset === "other" ? customModel.trim() || DEFAULT_MODEL : selectedPreset;

  const handlePresetChange = (value: string) => {
    setSelectedPreset(value);
    if (value !== "other") {
      localStorage.setItem(MODEL_STORAGE_KEY, value);
    }
  };

  const handleCustomModelBlur = () => {
    const trimmed = customModel.trim();
    if (trimmed) {
      localStorage.setItem(MODEL_STORAGE_KEY, trimmed);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || isSending) {
      return;
    }
    onSend(trimmed, effectiveModel);
    setMessage("");
  };

  return (
    <aside className="flex max-h-[calc(100vh-120px)] flex-col overflow-hidden rounded-2xl border border-[var(--stroke)] bg-white/95 shadow-sm backdrop-blur">
      <div className="flex items-center justify-between gap-3 border-b border-[var(--stroke)] px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--secondary-purple)] text-white">
            <SparklesIcon />
          </div>
          <div>
            <h2 className="font-display text-sm font-semibold text-[var(--navy-dark)]">
              AI Assistant
            </h2>
            <p className="text-[10px] text-[var(--gray-text)]">
              Manage your cards
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-[10px] font-medium text-green-600">
          <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
          Online
        </div>
      </div>

      <div className="border-b border-[var(--stroke)] bg-[var(--surface)] px-4 py-2.5">
        <label className="mb-1 block text-[10px] font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)]">
          Model
        </label>
        <select
          value={selectedPreset}
          onChange={(e) => handlePresetChange(e.target.value)}
          className="w-full rounded-lg border border-[var(--stroke)] bg-white px-2 py-1.5 text-[11px] text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
        >
          {FREE_MODELS.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label}
            </option>
          ))}
          <option value="other">Other (enter model ID)...</option>
        </select>
        {selectedPreset === "other" && (
          <input
            type="text"
            value={customModel}
            onChange={(e) => setCustomModel(e.target.value)}
            onBlur={handleCustomModelBlur}
            placeholder="e.g. openai/gpt-4o-mini"
            className="mt-2 w-full rounded-lg border border-[var(--stroke)] bg-white px-2 py-1.5 text-[11px] text-[var(--navy-dark)] outline-none transition placeholder:text-[var(--gray-text)] focus:border-[var(--primary-blue)]"
          />
        )}
      </div>

      <div className="flex flex-1 flex-col gap-2 overflow-y-auto bg-[var(--surface)] p-3">
        {messages.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center">
            <div className="rounded-full bg-[var(--stroke)] p-3 text-[var(--gray-text)]">
              <SparklesIcon />
            </div>
            <p className="text-xs text-[var(--gray-text)]">
              Ask the assistant to create, move, or update cards
            </p>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div
              key={`${msg.role}-${index}`}
              className={
                msg.role === "user"
                  ? "ml-6 self-end rounded-2xl rounded-br-md bg-[var(--primary-blue)] px-3 py-2 text-xs text-white"
                  : "mr-6 self-start rounded-2xl rounded-bl-md border border-[var(--stroke)] bg-white px-3 py-2 text-xs text-[var(--navy-dark)]"
              }
            >
              {msg.content}
            </div>
          ))
        )}
      </div>

      {retryStatus ? (
        <div className="flex items-center gap-2 border-t border-amber-100 bg-amber-50 px-3 py-2 text-[10px] font-medium text-amber-700">
          <div className="h-3 w-3 shrink-0 animate-spin rounded-full border-2 border-amber-300 border-t-amber-600" />
          {retryStatus.countdown > 0
            ? `Rate limited — retrying in ${retryStatus.countdown}s (attempt ${retryStatus.attempt} of ${retryStatus.maxAttempts})`
            : `Retrying… (attempt ${retryStatus.attempt} of ${retryStatus.maxAttempts})`}
        </div>
      ) : error ? (
        <p className="border-t border-red-100 bg-red-50 px-3 py-2 text-[10px] font-medium text-red-600">
          {error}
        </p>
      ) : null}

      <form onSubmit={handleSubmit} className="flex items-end gap-2 border-t border-[var(--stroke)] bg-white p-3">
        <textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
          placeholder="Ask the assistant..."
          rows={2}
          className="flex-1 resize-none rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-xs text-[var(--navy-dark)] outline-none transition placeholder:text-[var(--gray-text)] focus:border-[var(--primary-blue)]"
          aria-label="Chat message"
        />
        <button
          type="submit"
          disabled={isSending}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[var(--secondary-purple)] text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
          aria-label={isSending ? "Sending message" : "Send message"}
        >
          {isSending ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
          ) : (
            <SendIcon />
          )}
        </button>
      </form>
    </aside>
  );
};
