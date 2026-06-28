"use client";

import {
  useCallback,
  useEffect,
  useState,
  type FormEvent,
  type SetStateAction,
} from "react";
import { ChatSidebar, type RetryStatus } from "@/components/ChatSidebar";
import { KanbanBoard } from "@/components/KanbanBoard";
import {
  fetchBoardById,
  createCard,
  deleteCard as apiDeleteCard,
  sendChat,
  setApiToken,
  toBoardData,
  updateCard,
  updateColumn,
  login,
  register,
  listBoards,
  createBoard,
  deleteBoard as apiDeleteBoard,
  type ChatMessage,
  type BoardSummary,
} from "@/lib/api";
import { findCardLocation, fromCardId, fromColumnId, type BoardData } from "@/lib/kanban";

const TOKEN_KEY = "pm_auth_token";
const USERNAME_KEY = "pm_auth_username";
const BOARD_KEY = "pm_current_board";

function getStoredAuth(): { token: string; username: string } | null {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem(TOKEN_KEY);
  const username = localStorage.getItem(USERNAME_KEY);
  if (token && username) {
    return { token, username };
  }
  return null;
}

function setStoredAuth(token: string, username: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USERNAME_KEY, username);
}

function clearStoredAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USERNAME_KEY);
  localStorage.removeItem(BOARD_KEY);
}

function isUnauthorizedError(err: unknown): boolean {
  return err instanceof Error && err.message.includes("401");
}

function getStoredBoardId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(BOARD_KEY);
}

function setStoredBoardId(boardId: string): void {
  localStorage.setItem(BOARD_KEY, boardId);
}

export default function Home() {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [currentBoardId, setCurrentBoardId] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [boardError, setBoardError] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatError, setChatError] = useState<string | null>(null);
  const [chatRetryStatus, setChatRetryStatus] = useState<RetryStatus>(null);
  const [isChatSending, setIsChatSending] = useState(false);
  const [isRegisterMode, setIsRegisterMode] = useState(false);

  // Check for stored auth on mount
  useEffect(() => {
    const storedAuth = getStoredAuth();
    if (storedAuth) {
      setApiToken(storedAuth.token);
      setAuthToken(storedAuth.token);
      setUsername(storedAuth.username);
      setIsAuthenticated(true);
      const storedBoardId = getStoredBoardId();
      if (storedBoardId) {
        setCurrentBoardId(storedBoardId);
      }
    }
    setIsLoading(false);
  }, []);

  const handleSessionExpired = useCallback(() => {
    clearStoredAuth();
    setApiToken(undefined);
    setIsAuthenticated(false);
    setAuthToken(null);
    setUsername("");
    setError("Session expired. Please sign in again.");
    setIsLoading(false);
  }, []);

  const refreshBoardsList = useCallback(async () => {
    if (!authToken) return;
    try {
      const response = await listBoards();
      setBoards(response.boards);
      return response.boards;
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      if (isUnauthorizedError(err)) {
        handleSessionExpired();
      }
      return [];
    }
  }, [authToken, handleSessionExpired]);

  const loadBoard = useCallback(async (boardId: string) => {
    if (!authToken) return;
    setIsLoading(true);
    setBoardError(null);
    try {
      const payload = await fetchBoardById(boardId);
      setBoard(toBoardData(payload));
      setCurrentBoardId(boardId);
      setStoredBoardId(boardId);
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      if (isUnauthorizedError(err)) {
        handleSessionExpired();
      } else if (err instanceof Error && err.message.includes("404")) {
        localStorage.removeItem(BOARD_KEY);
        setCurrentBoardId(null);
        setBoardError("Board not found.");
      } else {
        setBoardError("Unable to load the board from the server.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [authToken, handleSessionExpired]);

  const refreshBoard = useCallback(async () => {
    if (!authToken || !currentBoardId) return;
    await loadBoard(currentBoardId);
  }, [authToken, currentBoardId, loadBoard]);

  // Load boards list when authenticated
  useEffect(() => {
    if (isAuthenticated && authToken) {
      refreshBoardsList().then((boardsList) => {
        if (boardsList && boardsList.length > 0) {
          // If we have a stored board ID, use it if it still exists
          const storedId = getStoredBoardId();
          const storedExists = storedId && boardsList.some((b) => b.id === storedId);
          if (storedExists) {
            loadBoard(storedId);
          } else {
            // Load the first board
            loadBoard(boardsList[0].id);
          }
        } else if (boardsList && boardsList.length === 0) {
          // No boards, create a default one
          createBoard("My First Board", true).then((response) => {
            refreshBoardsList().then(() => {
              loadBoard(response.id);
            });
          });
        }
      });
    }
  }, [isAuthenticated, authToken, refreshBoardsList, loadBoard]);

  const handleBoardChange = useCallback(
    (updater: SetStateAction<BoardData>) => {
      setBoard((prev) => {
        if (!prev) {
          return prev;
        }
        return typeof updater === "function" ? updater(prev) : updater;
      });
    },
    []
  );

  const handleSelectBoard = async (boardId: string) => {
    await loadBoard(boardId);
    // Clear chat when switching boards
    setChatMessages([]);
    setChatError(null);
  };

  const handleCreateBoard = async (title: string) => {
    if (!authToken) return;
    try {
      const response = await createBoard(title, true);
      await refreshBoardsList();
      await loadBoard(response.id);
      setChatMessages([]);
      setChatError(null);
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      setBoardError("Failed to create board.");
    }
  };

  const handleDeleteBoard = async (boardId: string) => {
    if (!authToken) return;
    try {
      await apiDeleteBoard(boardId);
      const updatedBoards = await refreshBoardsList();
      if (updatedBoards && updatedBoards.length > 0) {
        // If we deleted the current board, load another one
        if (boardId === currentBoardId) {
          await loadBoard(updatedBoards[0].id);
          setChatMessages([]);
          setChatError(null);
        }
      } else {
        // No boards left, create a default one
        const response = await createBoard("My Board", true);
        await refreshBoardsList();
        await loadBoard(response.id);
      }
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      setBoardError("Failed to delete board.");
    }
  };

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    const formData = new FormData(event.currentTarget);
    const formUsername = String(formData.get("username") || "").trim();
    const password = String(formData.get("password") || "").trim();

    if (!formUsername || !password) {
      setError("Please enter both username and password.");
      return;
    }

    try {
      const response = await login(formUsername, password);
      setStoredAuth(response.token, response.username);
      setApiToken(response.token);
      setAuthToken(response.token);
      setUsername(response.username);
      setIsAuthenticated(true);
      event.currentTarget.reset();
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      setError("Invalid username or password.");
    }
  };

  const handleRegister = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    const formData = new FormData(event.currentTarget);
    const formUsername = String(formData.get("username") || "").trim();
    const password = String(formData.get("password") || "").trim();
    const confirmPassword = String(formData.get("confirmPassword") || "").trim();

    if (!formUsername || !password) {
      setError("Please enter both username and password.");
      return;
    }

    if (formUsername.length < 3) {
      setError("Username must be at least 3 characters.");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    try {
      const response = await register(formUsername, password);
      setStoredAuth(response.token, response.username);
      setApiToken(response.token);
      setAuthToken(response.token);
      setUsername(response.username);
      setIsAuthenticated(true);
      event.currentTarget.reset();
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      if (err instanceof Error && err.message.includes("already taken")) {
        setError("Username already taken. Please choose another.");
      } else {
        setError("Registration failed. Please try again.");
      }
    }
  };

  const handleLogout = () => {
    clearStoredAuth();
    setApiToken(undefined);
    setIsAuthenticated(false);
    setAuthToken(null);
    setUsername("");
    setBoard(null);
    setBoards([]);
    setCurrentBoardId(null);
    setBoardError(null);
    setChatMessages([]);
    setChatError(null);
  };

  const handleRenameColumn = async (columnId: string, title: string) => {
    const columnIdNumber = Number(fromColumnId(columnId));
    if (Number.isNaN(columnIdNumber)) {
      setBoardError("Unable to save column changes.");
      return;
    }
    try {
      await updateColumn(columnIdNumber, { title });
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      setBoardError("Unable to save column changes.");
      refreshBoard();
    }
  };

  const handleAddCard = async (columnId: string, title: string, details: string) => {
    const columnIdNumber = Number(fromColumnId(columnId));
    if (Number.isNaN(columnIdNumber)) {
      setBoardError("Unable to add the card.");
      return;
    }
    try {
      await createCard(
        {
          column_id: columnIdNumber,
          title,
          details: details || "No details yet.",
        },
        currentBoardId || undefined
      );
      refreshBoard();
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      setBoardError("Unable to add the card.");
      refreshBoard();
    }
  };

  const handleDeleteCard = async (columnId: string, cardId: string) => {
    const cardIdNumber = Number(fromCardId(cardId));
    if (Number.isNaN(cardIdNumber)) {
      return;
    }
    try {
      await apiDeleteCard(cardIdNumber, currentBoardId || undefined);
      refreshBoard();
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      setBoardError("Unable to remove the card.");
      refreshBoard();
    }
  };

  const handleMoveCard = async (
    activeId: string,
    _overId: string,
    nextColumns: BoardData["columns"]
  ) => {
    const location = findCardLocation(nextColumns, activeId);
    if (!location) {
      return;
    }
    const cardIdNumber = Number(fromCardId(activeId));
    const columnIdNumber = Number(fromColumnId(location.columnId));
    if (Number.isNaN(cardIdNumber) || Number.isNaN(columnIdNumber)) {
      return;
    }
    try {
      await updateCard(
        cardIdNumber,
        {
          column_id: columnIdNumber,
          position: location.index,
        },
        currentBoardId || undefined
      );
      refreshBoard();
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      setBoardError("Unable to move the card.");
      refreshBoard();
    }
  };

  const handleSendChat = async (message: string, model?: string) => {
    setChatError(null);
    setChatRetryStatus(null);
    setIsChatSending(true);
    const userMessage: ChatMessage = { role: "user", content: message };
    const history = [...chatMessages];
    setChatMessages((prev) => [...prev, userMessage]);

    const maxAttempts = 3;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        const response = await sendChat({
          message,
          history,
          apply_updates: true,
          model: model || undefined,
        });
        setChatRetryStatus(null);
        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", content: response.response },
        ]);
        if (response.board) {
          setBoard(toBoardData(response.board));
        }
        setIsChatSending(false);
        return;
      } catch (err) {
        if (process.env.NODE_ENV === "development") console.error(err);

        if (err instanceof Error && err.message.startsWith("429")) {
          if (attempt < maxAttempts) {
            let retryAfter = 10;
            try {
              const body = JSON.parse(err.message.slice(4).trim());
              retryAfter = Math.max(1, Math.min(body.detail?.retry_after ?? 10, 30));
            } catch {}
            for (let t = retryAfter; t > 0; t--) {
              setChatRetryStatus({ attempt, maxAttempts, countdown: t });
              await new Promise<void>((resolve) => setTimeout(resolve, 1000));
            }
            setChatRetryStatus({ attempt, maxAttempts, countdown: 0 });
            continue;
          }
          setChatRetryStatus(null);
          setChatError("Model is rate-limited. Try a different model from the dropdown.");
        } else {
          setChatRetryStatus(null);
          let chatErrMsg = "Unable to reach the assistant right now.";
          if (err instanceof Error) {
            if (err.message.includes("404")) {
              chatErrMsg = "Model not found. Try a different model from the dropdown.";
            } else if (err.message.includes("500")) {
              chatErrMsg = "Server error. Check that OPENROUTER_API_KEY is configured.";
            } else if (err.message.includes("502") || err.message.includes("503")) {
              chatErrMsg = "AI provider is temporarily unavailable. Try a different model.";
            } else if (err.name === "AbortError") {
              chatErrMsg = "Request timed out. The model may be slow — try again.";
            }
          }
          setChatError(chatErrMsg);
        }

        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Something went wrong. Please try again." },
        ]);
        break;
      }
    }

    setChatRetryStatus(null);
    setIsChatSending(false);
  };

  // Show loading spinner on initial mount
  if (isLoading && !isAuthenticated) {
    return (
      <div className="relative min-h-screen overflow-hidden">
        <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
        <main className="relative mx-auto flex min-h-screen max-w-xl items-center px-6 py-16">
          <section className="w-full rounded-[32px] border border-[var(--stroke)] bg-white/90 p-8 text-center shadow-[var(--shadow)] backdrop-blur">
            <p className="text-sm text-[var(--gray-text)]">Loading...</p>
          </section>
        </main>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="relative min-h-screen overflow-hidden">
        <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
        <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

        <main className="relative mx-auto flex min-h-screen max-w-xl items-center px-6 py-16">
          <section className="w-full rounded-[32px] border border-[var(--stroke)] bg-white/90 p-8 shadow-[var(--shadow)] backdrop-blur">
            <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
              Project Management
            </p>
            <h1 className="mt-3 font-display text-3xl font-semibold text-[var(--navy-dark)]">
              {isRegisterMode ? "Create account" : "Welcome back"}
            </h1>
            <p className="mt-3 text-sm leading-6 text-[var(--gray-text)]">
              {isRegisterMode
                ? "Create a new account to start managing your projects."
                : "Sign in to continue to your Kanban boards."}
            </p>

            {isRegisterMode ? (
              <form onSubmit={handleRegister} className="mt-6 space-y-4">
                <div>
                  <label
                    htmlFor="username"
                    className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
                  >
                    Username
                  </label>
                  <input
                    id="username"
                    name="username"
                    placeholder="Choose a username"
                    aria-label="Username"
                    className="mt-2 w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-medium text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
                    required
                  />
                </div>
                <div>
                  <label
                    htmlFor="password"
                    className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
                  >
                    Password
                  </label>
                  <input
                    id="password"
                    name="password"
                    type="password"
                    placeholder="Create a password"
                    aria-label="Password"
                    className="mt-2 w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-medium text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
                    required
                  />
                </div>
                <div>
                  <label
                    htmlFor="confirmPassword"
                    className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
                  >
                    Confirm Password
                  </label>
                  <input
                    id="confirmPassword"
                    name="confirmPassword"
                    type="password"
                    placeholder="Confirm your password"
                    aria-label="Confirm Password"
                    className="mt-2 w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-medium text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
                    required
                  />
                </div>
                {error ? (
                  <p className="text-sm font-semibold text-[var(--secondary-purple)]">
                    {error}
                  </p>
                ) : null}
                <button
                  type="submit"
                  className="w-full rounded-full bg-[var(--secondary-purple)] px-4 py-3 text-xs font-semibold uppercase tracking-[0.25em] text-white transition hover:brightness-110"
                >
                  Create account
                </button>
                <p className="text-center text-sm text-[var(--gray-text)]">
                  Already have an account?{" "}
                  <button
                    type="button"
                    onClick={() => {
                      setIsRegisterMode(false);
                      setError(null);
                    }}
                    className="font-semibold text-[var(--primary-blue)] hover:underline"
                  >
                    Sign in
                  </button>
                </p>
              </form>
            ) : (
              <form onSubmit={handleLogin} className="mt-6 space-y-4">
                <div>
                  <label
                    htmlFor="username"
                    className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
                  >
                    Username
                  </label>
                  <input
                    id="username"
                    name="username"
                    placeholder="Enter your username"
                    aria-label="Username"
                    className="mt-2 w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-medium text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
                    required
                  />
                </div>
                <div>
                  <label
                    htmlFor="password"
                    className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
                  >
                    Password
                  </label>
                  <input
                    id="password"
                    name="password"
                    type="password"
                    placeholder="Enter your password"
                    aria-label="Password"
                    className="mt-2 w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-medium text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
                    required
                  />
                </div>
                {error ? (
                  <p className="text-sm font-semibold text-[var(--secondary-purple)]">
                    {error}
                  </p>
                ) : null}
                <button
                  type="submit"
                  className="w-full rounded-full bg-[var(--secondary-purple)] px-4 py-3 text-xs font-semibold uppercase tracking-[0.25em] text-white transition hover:brightness-110"
                >
                  Sign in
                </button>
                <p className="text-center text-sm text-[var(--gray-text)]">
                  Don&apos;t have an account?{" "}
                  <button
                    type="button"
                    onClick={() => {
                      setIsRegisterMode(true);
                      setError(null);
                    }}
                    className="font-semibold text-[var(--primary-blue)] hover:underline"
                  >
                    Create one
                  </button>
                </p>
              </form>
            )}
          </section>
        </main>
      </div>
    );
  }

  if (isLoading || !board) {
    return (
      <div className="relative min-h-screen overflow-hidden">
        <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
        <main className="relative mx-auto flex min-h-screen max-w-xl items-center px-6 py-16">
          <section className="w-full rounded-[32px] border border-[var(--stroke)] bg-white/90 p-8 text-center shadow-[var(--shadow)] backdrop-blur">
            {boardError && !isLoading ? (
              <>
                <h1 className="font-display text-2xl font-semibold text-[var(--navy-dark)]">
                  Unable to load board
                </h1>
                <p className="mt-3 text-sm text-[var(--secondary-purple)]">
                  {boardError}
                </p>
                <button
                  onClick={() => { setBoardError(null); refreshBoardsList().then((bl) => { if (bl && bl.length > 0) loadBoard(bl[0].id); else if (bl && bl.length === 0) createBoard("My Board", true).then((r) => loadBoard(r.id)); }); }}
                  className="mt-6 rounded-full bg-[var(--primary-blue)] px-6 py-2 text-xs font-semibold uppercase tracking-[0.25em] text-white transition hover:brightness-110"
                >
                  Retry
                </button>
              </>
            ) : (
              <>
                <h1 className="font-display text-2xl font-semibold text-[var(--navy-dark)]">
                  Loading your board
                </h1>
                <p className="mt-3 text-sm text-[var(--gray-text)]">
                  Fetching the latest updates from the server.
                </p>
              </>
            )}
          </section>
        </main>
      </div>
    );
  }

  return (
    <div>
      {boardError ? (
        <div className="mx-auto max-w-[1500px] px-6 pt-6">
          <div className="rounded-2xl border border-[var(--stroke)] bg-white/90 px-4 py-3 text-sm text-[var(--secondary-purple)] shadow-[var(--shadow)]">
            {boardError}
          </div>
        </div>
      ) : null}
      <KanbanBoard
        board={board}
        boardId={currentBoardId}
        boards={boards}
        username={username}
        onBoardChange={handleBoardChange}
        onSelectBoard={handleSelectBoard}
        onCreateBoard={handleCreateBoard}
        onDeleteBoard={handleDeleteBoard}
        onLogout={handleLogout}
        onRenameColumn={handleRenameColumn}
        onAddCard={handleAddCard}
        onDeleteCard={handleDeleteCard}
        onMoveCard={handleMoveCard}
        sidebar={(
          <ChatSidebar
            messages={chatMessages}
            onSend={(msg, model) => handleSendChat(msg, model)}
            isSending={isChatSending}
            error={chatError}
            retryStatus={chatRetryStatus}
          />
        )}
      />
    </div>
  );
}
