"use client";

import { useState, type FormEvent } from "react";
import type { BoardSummary } from "@/lib/api";

type BoardSelectorProps = {
  boards: BoardSummary[];
  currentBoardId: string | null;
  onSelectBoard: (boardId: string) => void;
  onCreateBoard: (title: string) => void;
  onDeleteBoard: (boardId: string) => void;
};

export const BoardSelector = ({
  boards,
  currentBoardId,
  onSelectBoard,
  onCreateBoard,
  onDeleteBoard,
}: BoardSelectorProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newBoardTitle, setNewBoardTitle] = useState("");

  const handleCreateSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (newBoardTitle.trim()) {
      onCreateBoard(newBoardTitle.trim());
      setNewBoardTitle("");
      setIsCreating(false);
    }
  };

  const currentBoard = boards.find((b) => b.id === currentBoardId);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 rounded-lg border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-medium text-[var(--navy-dark)] transition hover:border-[var(--primary-blue)]"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="h-4 w-4 text-[var(--gray-text)]"
        >
          <path d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" />
        </svg>
        <span className="max-w-[150px] truncate">
          {currentBoard?.title || "Select Board"}
        </span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className={`h-4 w-4 transition ${isOpen ? "rotate-180" : ""}`}
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute left-0 top-full z-50 mt-2 w-64 rounded-xl border border-[var(--stroke)] bg-white p-2 shadow-lg">
          <div className="max-h-60 overflow-y-auto">
            {boards.map((board) => (
              <div
                key={board.id}
                className={`group flex items-center justify-between rounded-lg px-3 py-2 ${
                  board.id === currentBoardId
                    ? "bg-[var(--primary-blue)]/10 text-[var(--primary-blue)]"
                    : "hover:bg-[var(--surface)]"
                }`}
              >
                <button
                  type="button"
                  onClick={() => {
                    onSelectBoard(board.id);
                    setIsOpen(false);
                  }}
                  className="flex-1 text-left text-sm font-medium"
                >
                  {board.title}
                </button>
                {boards.length > 1 && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm(`Delete "${board.title}"?`)) {
                        onDeleteBoard(board.id);
                      }
                    }}
                    className="ml-2 rounded p-1 text-[var(--gray-text)] opacity-0 transition hover:bg-red-50 hover:text-red-500 group-hover:opacity-100"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      className="h-4 w-4"
                    >
                      <path
                        fillRule="evenodd"
                        d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className="mt-2 border-t border-[var(--stroke)] pt-2">
            {isCreating ? (
              <form onSubmit={handleCreateSubmit} className="flex gap-2">
                <input
                  type="text"
                  value={newBoardTitle}
                  onChange={(e) => setNewBoardTitle(e.target.value)}
                  placeholder="Board name"
                  className="flex-1 rounded-lg border border-[var(--stroke)] px-2 py-1 text-sm outline-none focus:border-[var(--primary-blue)]"
                  autoFocus
                />
                <button
                  type="submit"
                  className="rounded-lg bg-[var(--primary-blue)] px-3 py-1 text-xs font-medium text-white"
                >
                  Add
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsCreating(false);
                    setNewBoardTitle("");
                  }}
                  className="rounded-lg border border-[var(--stroke)] px-2 py-1 text-xs"
                >
                  Cancel
                </button>
              </form>
            ) : (
              <button
                type="button"
                onClick={() => setIsCreating(true)}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-[var(--primary-blue)] hover:bg-[var(--surface)]"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-4 w-4"
                >
                  <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
                </svg>
                New Board
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
