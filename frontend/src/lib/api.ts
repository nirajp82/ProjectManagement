import type { BoardData, Card, Column, Label, Priority } from "@/lib/kanban";
import { toCardId, toColumnId } from "@/lib/kanban";

type BoardResponse = {
    board: { id: string; title: string };
    columns: Array<Column & { position?: number } & { cardIds: string[] }>;
    cards: Record<string, Card>;
    labels?: Record<string, Label>;
};

type ApiOptions = {
    token?: string;
    username?: string; // Legacy support
};

export type ChatMessage = {
    role: "user" | "assistant";
    content: string;
};

type ChatAction = {
    type: "create_card" | "update_card" | "move_card" | "delete_card";
    [key: string]: unknown;
};

type ChatResponse = {
    response: string;
    actions: ChatAction[];
    board?: BoardResponse;
    model?: string | null;
};

export type AuthResponse = {
    token: string;
    username: string;
};

export type BoardSummary = {
    id: string;
    title: string;
    created_at: string;
    updated_at: string;
};

export type BoardListResponse = {
    boards: BoardSummary[];
};

const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "";
const DEFAULT_TIMEOUT = 30000;

const apiFetch = async <T>(
    path: string,
    options: RequestInit = {},
    apiOptions: ApiOptions = {}
): Promise<T> => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT);

    try {
        const headers = new Headers(options.headers);
        headers.set("Content-Type", "application/json");
        if (apiOptions.token) {
            headers.set("Authorization", `Bearer ${apiOptions.token}`);
        } else if (apiOptions.username) {
            // Legacy fallback
            headers.set("X-User", apiOptions.username);
        }

        const response = await fetch(`${apiBase}${path}`, {
            ...options,
            headers,
            signal: controller.signal,
        });

        if (!response.ok) {
            const message = await response.text();
            throw new Error(message || "Request failed");
        }

        if (response.status === 204) {
            return undefined as T;
        }

        return (await response.json()) as T;
    } finally {
        clearTimeout(timeoutId);
    }
};

export const toBoardData = (payload: BoardResponse): BoardData => {
    const cards: Record<string, Card> = Object.fromEntries(
        Object.entries(payload.cards).map(([id, card]) => [
            toCardId(id),
            { ...card, id: toCardId(card.id), labelIds: card.labelIds || [] },
        ])
    );

    const labels: Record<string, Label> = payload.labels || {};

    return {
        columns: payload.columns.map((column) => ({
            id: toColumnId(column.id),
            title: column.title,
            cardIds: column.cardIds.map((cardId) => toCardId(cardId)),
        })),
        cards,
        labels,
    };
};

// Auth endpoints
export const register = (username: string, password: string) =>
    apiFetch<AuthResponse>("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, password }),
    });

export const login = (username: string, password: string) =>
    apiFetch<AuthResponse>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
    });

// Board management endpoints
export const listBoards = (token?: string) =>
    apiFetch<BoardListResponse>("/api/boards", {}, { token });

export const createBoard = (title: string, withDefaultColumns: boolean = true, token?: string) =>
    apiFetch<{ id: string }>("/api/boards", {
        method: "POST",
        body: JSON.stringify({ title, with_default_columns: withDefaultColumns }),
    }, { token });

export const fetchBoardById = (boardId: string, token?: string) =>
    apiFetch<BoardResponse>(`/api/boards/${boardId}`, {}, { token });

export const updateBoardTitle = (boardId: string, title: string, token?: string) =>
    apiFetch(`/api/boards/${boardId}`, {
        method: "PATCH",
        body: JSON.stringify({ title }),
    }, { token });

export const deleteBoard = (boardId: string, token?: string) =>
    apiFetch(`/api/boards/${boardId}`, { method: "DELETE" }, { token });

// Legacy board endpoint (returns default board)
export const fetchBoard = (token?: string) =>
    apiFetch<BoardResponse>("/api/board", {}, { token });

export const updateColumn = (
    columnId: number,
    payload: { title?: string; position?: number },
    token?: string
) =>
    apiFetch(`/api/columns/${columnId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
    }, { token });

export const createCard = (
    payload: {
        column_id: number;
        title: string;
        details: string;
        position?: number;
        due_date?: string | null;
        priority?: Priority;
    },
    token?: string,
    boardId?: string
) => {
    const url = boardId ? `/api/cards?board_id=${boardId}` : "/api/cards";
    return apiFetch<{ id: string }>(url, {
        method: "POST",
        body: JSON.stringify(payload),
    }, { token });
};

export const updateCard = (
    cardId: number,
    payload: {
        title?: string;
        details?: string;
        column_id?: number;
        position?: number;
        due_date?: string | null;
        priority?: Priority;
    },
    token?: string,
    boardId?: string
) => {
    const url = boardId ? `/api/cards/${cardId}?board_id=${boardId}` : `/api/cards/${cardId}`;
    return apiFetch(url, {
        method: "PATCH",
        body: JSON.stringify(payload),
    }, { token });
};

export const deleteCard = (cardId: number, token?: string, boardId?: string) => {
    const url = boardId ? `/api/cards/${cardId}?board_id=${boardId}` : `/api/cards/${cardId}`;
    return apiFetch(url, { method: "DELETE" }, { token });
};

export const sendChat = (
    payload: { message: string; history: ChatMessage[]; apply_updates: boolean },
    token?: string
) =>
    apiFetch<ChatResponse>("/api/chat", {
        method: "POST",
        body: JSON.stringify(payload),
    }, { token });
