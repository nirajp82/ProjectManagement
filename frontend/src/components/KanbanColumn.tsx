import clsx from "clsx";
import { useDndContext, useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { Card, Column, Label } from "@/lib/kanban";
import { KanbanCard } from "@/components/KanbanCard";
import { NewCardForm } from "@/components/NewCardForm";

type KanbanColumnProps = {
  column: Column;
  cards: Card[];
  labels: Record<string, Label>;
  onRename: (columnId: string, title: string) => void;
  onAddCard: (columnId: string, title: string, details: string) => void;
  onDeleteCard: (columnId: string, cardId: string) => void;
};

export const KanbanColumn = ({
  column,
  cards,
  labels,
  onRename,
  onAddCard,
  onDeleteCard,
}: KanbanColumnProps) => {
  const { over } = useDndContext();
  const { setNodeRef, isOver } = useDroppable({
    id: `column-${column.id}`,
    data: { columnId: column.id },
  });
  const overColumnId = over?.data?.current?.columnId as string | undefined;
  const isColumnOver = isOver || overColumnId === column.id;

  return (
    <section
      ref={setNodeRef}
      className={clsx(
        "flex min-h-[480px] flex-col rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] p-3 transition",
        isColumnOver && "ring-2 ring-[var(--accent-yellow)]"
      )}
      data-testid={`column-${column.id}`}
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <div className="h-2 w-2 shrink-0 rounded-full bg-[var(--accent-yellow)]" />
          <input
            value={column.title}
            onChange={(event) => onRename(column.id, event.target.value)}
            className="min-w-0 flex-1 truncate bg-transparent font-display text-sm font-semibold text-[var(--navy-dark)] outline-none"
            aria-label="Column title"
          />
        </div>
        <span className="shrink-0 rounded-full bg-[var(--stroke)] px-2 py-0.5 text-[10px] font-semibold tabular-nums text-[var(--gray-text)]">
          {cards.length}
        </span>
      </div>
      <div className="flex flex-1 flex-col gap-2 overflow-y-auto">
        <SortableContext
          id={column.id}
          items={column.cardIds}
          strategy={verticalListSortingStrategy}
        >
          {cards.map((card) => (
            <KanbanCard
              key={card.id}
              card={card}
              columnId={column.id}
              labels={labels}
              onDelete={(cardId) => onDeleteCard(column.id, cardId)}
            />
          ))}
        </SortableContext>
        {cards.length === 0 && (
          <div className="flex flex-1 items-center justify-center rounded-xl border border-dashed border-[var(--stroke)] px-2 py-4 text-center text-[10px] font-medium uppercase tracking-wider text-[var(--gray-text)]">
            Drop here
          </div>
        )}
      </div>
      <NewCardForm
        onAdd={(title, details) => onAddCard(column.id, title, details)}
      />
    </section>
  );
};
