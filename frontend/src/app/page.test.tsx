import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import Home from "@/app/page";

const mockBoard = {
    board: { id: "1", title: "My Board" },
    columns: [
        { id: "1", title: "Backlog", position: 0, cardIds: [] },
    ],
    cards: {},
    labels: {},
};

const mockBoardWithCard = {
    board: { id: "1", title: "My Board" },
    columns: [
        { id: "1", title: "Backlog", position: 0, cardIds: ["9"] },
    ],
    cards: {
        "9": {
            id: "9",
            title: "AI created",
            details: "From chat",
            due_date: null,
            priority: "none",
            labelIds: [],
        },
    },
    labels: {},
};

const mockAuthResponse = { token: "test-token", username: "user" };
const mockBoardsList = { boards: [{ id: "1", title: "My Board", created_at: "2024-01-01", updated_at: "2024-01-01" }] };

describe("Home page", () => {
    beforeEach(() => {
        localStorage.clear();
    });

    it("shows the login screen by default", () => {
        render(<Home />);
        expect(screen.getByText("Welcome back")).toBeInTheDocument();
        expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
    });

    it("allows signing in with demo credentials", async () => {
        vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
            const url = String(input);
            if (url.includes("/api/auth/login")) {
                return {
                    ok: true,
                    status: 200,
                    json: async () => mockAuthResponse,
                    text: async () => "",
                } as Response;
            }
            if (url.includes("/api/boards/1")) {
                return {
                    ok: true,
                    status: 200,
                    json: async () => mockBoard,
                    text: async () => "",
                } as Response;
            }
            if (url.includes("/api/boards")) {
                return {
                    ok: true,
                    status: 200,
                    json: async () => mockBoardsList,
                    text: async () => "",
                } as Response;
            }
            return {
                ok: false,
                status: 500,
                text: async () => "Unexpected",
            } as Response;
        });

        render(<Home />);
        await userEvent.type(screen.getByPlaceholderText(/enter your username/i), "user");
        await userEvent.type(screen.getByPlaceholderText(/enter your password/i), "password");
        await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

        expect(await screen.findByText("Kanban Studio")).toBeInTheDocument();
        vi.restoreAllMocks();
    });

    it("applies chat updates to the board", async () => {
        vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
            const url = String(input);
            if (url.includes("/api/auth/login")) {
                return {
                    ok: true,
                    status: 200,
                    json: async () => mockAuthResponse,
                    text: async () => "",
                } as Response;
            }
            if (url.includes("/api/boards/1")) {
                return {
                    ok: true,
                    status: 200,
                    json: async () => mockBoard,
                    text: async () => "",
                } as Response;
            }
            if (url.includes("/api/boards")) {
                return {
                    ok: true,
                    status: 200,
                    json: async () => mockBoardsList,
                    text: async () => "",
                } as Response;
            }
            if (url.includes("/api/chat")) {
                return {
                    ok: true,
                    status: 200,
                    json: async () => ({
                        response: "Created a card.",
                        actions: [{ type: "create_card" }],
                        board: mockBoardWithCard,
                    }),
                    text: async () => "",
                } as Response;
            }
            return {
                ok: false,
                status: 500,
                text: async () => "Unexpected",
            } as Response;
        });

        render(<Home />);
        await userEvent.type(screen.getByPlaceholderText(/enter your username/i), "user");
        await userEvent.type(screen.getByPlaceholderText(/enter your password/i), "password");
        await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

        expect(await screen.findByText("Kanban Studio")).toBeInTheDocument();

        await userEvent.type(screen.getByLabelText("Chat message"), "Add a card");
        await userEvent.click(screen.getByRole("button", { name: /send/i }));

        expect(await screen.findByText("AI created")).toBeInTheDocument();
        vi.restoreAllMocks();
    });
});
