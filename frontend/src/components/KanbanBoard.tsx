"use client";

import { useMemo, useRef, useState, type ReactNode } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  pointerWithin,
  rectIntersection,
  MeasuringStrategy,
  type CollisionDetection,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { BoardSelector } from "@/components/BoardSelector";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { createId, moveCard, type BoardData, type Column } from "@/lib/kanban";
import type { BoardSummary } from "@/lib/api";

type KanbanBoardProps = {
  board: BoardData;
  boardId: string | null;
  boards: BoardSummary[];
  username?: string;
  onBoardChange: React.Dispatch<React.SetStateAction<BoardData>>;
  onSelectBoard: (boardId: string) => void;
  onCreateBoard: (title: string) => void;
  onDeleteBoard: (boardId: string) => void;
  onLogout?: () => void;
  onRenameColumn?: (columnId: string, title: string) => void;
  onAddCard?: (columnId: string, title: string, details: string) => void;
  onDeleteCard?: (columnId: string, cardId: string) => void;
  onMoveCard?: (activeId: string, overId: string, nextColumns: Column[]) => void;
  sidebar?: ReactNode;
};

export const KanbanBoard = ({
  board,
  boardId,
  boards,
  username,
  onBoardChange,
  onSelectBoard,
  onCreateBoard,
  onDeleteBoard,
  onLogout,
  onRenameColumn,
  onAddCard,
  onDeleteCard,
  onMoveCard,
  sidebar,
}: KanbanBoardProps) => {
  const setBoard = onBoardChange;
  const [activeCardId, setActiveCardId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const cardsById = useMemo(() => board.cards, [board.cards]);
  const lastOverId = useRef<string | null>(null);

  const collisionDetection: CollisionDetection = useMemo(
    () => (args) => {
      const filtered = {
        ...args,
        droppableContainers: args.droppableContainers.filter(
          (container) => container.id !== args.active.id
        ),
      };
      const pointerCollisions = pointerWithin(filtered);
      if (pointerCollisions.length > 0) {
        return pointerCollisions;
      }
      const intersections = rectIntersection(filtered);
      if (intersections.length > 0) {
        return intersections;
      }
      return closestCorners(filtered);
    },
    []
  );

  const handleDragStart = (event: DragStartEvent) => {
    const activeId = event.active.data.current?.cardId as string | undefined;
    if (!activeId) {
      return;
    }
    setActiveCardId(activeId);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    const activeId = active.data.current?.cardId as string | undefined;
    const activeColumnId = active.data.current?.columnId as string | undefined;
    const overIdFromData = over?.data.current?.cardId as string | undefined;
    const overColumnFromData = over?.data.current?.columnId as string | undefined;
    const isCrossColumn =
      activeColumnId && overColumnFromData && activeColumnId !== overColumnFromData;
    const resolvedOverId =
      (overIdFromData && overIdFromData !== activeId && !isCrossColumn
        ? overIdFromData
        : undefined) ??
      overColumnFromData ??
      lastOverId.current;
    if (!activeId || !resolvedOverId || activeId === resolvedOverId) {
      lastOverId.current = null;
      return;
    }

    const overId = resolvedOverId;

    setBoard((prev) => {
      const nextColumns = moveCard(prev.columns, activeId, overId);
      onMoveCard?.(activeId, overId, nextColumns);
      return {
        ...prev,
        columns: nextColumns,
      };
    });

    lastOverId.current = null;
  };

  const handleDragOver = (event: { active: DragEndEvent["active"]; over: DragEndEvent["over"] }) => {
    if (event.over) {
      const activeColumnId = event.active.data.current?.columnId as string | undefined;
      const overCardId = event.over.data.current?.cardId as string | undefined;
      const overColumnId = event.over.data.current?.columnId as string | undefined;
      if (activeColumnId && overColumnId && activeColumnId !== overColumnId) {
        lastOverId.current = overColumnId;
        return;
      }
      lastOverId.current = overCardId ?? overColumnId ?? null;
    }
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    setBoard((prev) => ({
      ...prev,
      columns: prev.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    }));
    onRenameColumn?.(columnId, title);
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    if (onAddCard) {
      onAddCard(columnId, title, details);
      return;
    }
    const id = createId("card");
    setBoard((prev) => ({
      ...prev,
      cards: {
        ...prev.cards,
        [id]: { id, title, details: details || "No details yet.", due_date: null, priority: "none", labelIds: [] },
      },
      columns: prev.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    }));
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    setBoard((prev) => {
      return {
        ...prev,
        cards: Object.fromEntries(
          Object.entries(prev.cards).filter(([id]) => id !== cardId)
        ),
        columns: prev.columns.map((column) =>
          column.id === columnId
            ? {
              ...column,
              cardIds: column.cardIds.filter((id) => id !== cardId),
            }
            : column
        ),
      };
    });
    onDeleteCard?.(columnId, cardId);
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen w-full flex-col gap-8 px-4 pb-12 pt-8 lg:px-8">
        <header className="relative z-20 flex items-center justify-between gap-4 rounded-2xl border border-[var(--stroke)] bg-white/90 px-6 py-4 shadow-sm backdrop-blur">
          <div className="flex items-center gap-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent-yellow)]">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="white" className="h-5 w-5">
                <path fillRule="evenodd" d="M3.5 2A1.5 1.5 0 002 3.5V5c0 1.149.15 2.263.43 3.326a13.022 13.022 0 009.244 9.244c1.063.28 2.177.43 3.326.43h1.5a1.5 1.5 0 001.5-1.5v-1.148a1.5 1.5 0 00-1.175-1.465l-3.223-.716a1.5 1.5 0 00-1.767 1.052l-.267.933c-.117.41-.555.643-.95.48a11.542 11.542 0 01-6.254-6.254c-.163-.395.07-.833.48-.95l.933-.267a1.5 1.5 0 001.052-1.767l-.716-3.223A1.5 1.5 0 004.648 2H3.5zM5 12.94l.953.27a.75.75 0 01.532.865l-.203 1.034a13.003 13.003 0 01-2.77-2.77l1.034-.203a.75.75 0 01.865.532l.27.953.319-.319z" clipRule="evenodd"/>
              </svg>
            </div>
            <div>
              <h1 className="font-display text-xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="text-xs text-[var(--gray-text)]">
                Drag cards between columns to organize your workflow
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <BoardSelector
              boards={boards}
              currentBoardId={boardId}
              onSelectBoard={onSelectBoard}
              onCreateBoard={onCreateBoard}
              onDeleteBoard={onDeleteBoard}
            />
            {username ? (
              <span className="hidden text-sm font-medium text-[var(--navy-dark)] sm:block">
                {username}
              </span>
            ) : null}
            {onLogout ? (
              <button
                type="button"
                onClick={onLogout}
                className="flex items-center gap-1.5 rounded-lg border border-[var(--stroke)] px-3 py-1.5 text-xs font-medium text-[var(--gray-text)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)]"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                  <path fillRule="evenodd" d="M3 4.25A2.25 2.25 0 015.25 2h5.5A2.25 2.25 0 0113 4.25v2a.75.75 0 01-1.5 0v-2a.75.75 0 00-.75-.75h-5.5a.75.75 0 00-.75.75v11.5c0 .414.336.75.75.75h5.5a.75.75 0 00.75-.75v-2a.75.75 0 011.5 0v2A2.25 2.25 0 0110.75 18h-5.5A2.25 2.25 0 013 15.75V4.25z" clipRule="evenodd"/>
                  <path fillRule="evenodd" d="M19 10a.75.75 0 00-.75-.75H8.704l1.048-.943a.75.75 0 10-1.004-1.114l-2.5 2.25a.75.75 0 000 1.114l2.5 2.25a.75.75 0 101.004-1.114l-1.048-.943h9.546A.75.75 0 0019 10z" clipRule="evenodd"/>
                </svg>
                Log out
              </button>
            ) : null}
          </div>
        </header>

        <div className={sidebar ? "grid gap-6 lg:grid-cols-[1fr_320px]" : ""}>
          <DndContext
            sensors={sensors}
            measuring={{ droppable: { strategy: MeasuringStrategy.Always } }}
            collisionDetection={collisionDetection}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDragEnd={handleDragEnd}
          >
            <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
              {board.columns.map((column) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  cards={column.cardIds.map((cardId) => board.cards[cardId])}
                  labels={board.labels || {}}
                  onRename={handleRenameColumn}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                />
              ))}
            </section>
            <DragOverlay>
              {activeCard ? (
                <div className="w-[260px]">
                  <KanbanCardPreview card={activeCard} />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>
          {sidebar ? (
            <div className="lg:sticky lg:top-10 lg:self-start">
              {sidebar}
            </div>
          ) : null}
        </div>
      </main>
    </div>
  );
};
