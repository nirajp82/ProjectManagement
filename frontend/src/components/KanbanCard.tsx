import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card, Label, Priority } from "@/lib/kanban";

const CalendarIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    className="h-3.5 w-3.5"
  >
    <path
      fillRule="evenodd"
      d="M5.75 2a.75.75 0 01.75.75V4h7V2.75a.75.75 0 011.5 0V4h.25A2.75 2.75 0 0118 6.75v8.5A2.75 2.75 0 0115.25 18H4.75A2.75 2.75 0 012 15.25v-8.5A2.75 2.75 0 014.75 4H5V2.75A.75.75 0 015.75 2zm-1 5.5c-.69 0-1.25.56-1.25 1.25v6.5c0 .69.56 1.25 1.25 1.25h10.5c.69 0 1.25-.56 1.25-1.25v-6.5c0-.69-.56-1.25-1.25-1.25H4.75z"
      clipRule="evenodd"
    />
  </svg>
);

const priorityConfig: Record<Priority, { color: string; label: string }> = {
  none: { color: "", label: "" },
  low: { color: "bg-blue-400", label: "Low" },
  medium: { color: "bg-yellow-400", label: "Medium" },
  high: { color: "bg-red-500", label: "High" },
};

const formatDueDate = (dateStr: string | null): string | null => {
  if (!dateStr) return null;
  const date = new Date(dateStr + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffDays = Math.ceil((date.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return `Overdue`;
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Tomorrow";
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
};

const getDueDateStyle = (dateStr: string | null): string => {
  if (!dateStr) return "";
  const date = new Date(dateStr + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffDays = Math.ceil((date.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return "text-red-600";
  if (diffDays <= 1) return "text-orange-600";
  return "text-[var(--gray-text)]";
};

const TrashIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    className="h-4 w-4"
  >
    <path
      fillRule="evenodd"
      d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.519.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
      clipRule="evenodd"
    />
  </svg>
);

const GripIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    className="h-4 w-4"
  >
    <path
      fillRule="evenodd"
      d="M10 3a1.5 1.5 0 110 3 1.5 1.5 0 010-3zM10 8.5a1.5 1.5 0 110 3 1.5 1.5 0 010-3zM11.5 15.5a1.5 1.5 0 10-3 0 1.5 1.5 0 003 0z"
      clipRule="evenodd"
    />
    <path
      fillRule="evenodd"
      d="M5 3a1.5 1.5 0 110 3 1.5 1.5 0 010-3zM5 8.5a1.5 1.5 0 110 3 1.5 1.5 0 010-3zM6.5 15.5a1.5 1.5 0 10-3 0 1.5 1.5 0 003 0zM15 3a1.5 1.5 0 110 3 1.5 1.5 0 010-3zM15 8.5a1.5 1.5 0 110 3 1.5 1.5 0 010-3zM16.5 15.5a1.5 1.5 0 10-3 0 1.5 1.5 0 003 0z"
      clipRule="evenodd"
    />
  </svg>
);

type KanbanCardProps = {
  card: Card;
  columnId: string;
  labels: Record<string, Label>;
  onDelete: (cardId: string) => void;
};

export const KanbanCard = ({ card, columnId, labels, onDelete }: KanbanCardProps) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({
      id: card.id,
      data: { cardId: card.id, columnId },
    });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "group cursor-grab rounded-2xl border border-transparent bg-white px-4 py-3 shadow-[0_8px_16px_rgba(3,33,71,0.06)]",
        "transition-all duration-150",
        isDragging && "cursor-grabbing opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      <div className="flex items-start gap-2">
        <div className="mt-0.5 shrink-0 text-[var(--gray-text)] opacity-0 transition-opacity group-hover:opacity-60">
          <GripIcon />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            {card.priority && card.priority !== "none" && (
              <span
                className={clsx("h-2 w-2 rounded-full", priorityConfig[card.priority].color)}
                title={`${priorityConfig[card.priority].label} priority`}
              />
            )}
            <h4 className="font-display text-sm font-semibold leading-tight text-[var(--navy-dark)]">
              {card.title}
            </h4>
          </div>
          {card.details && (
            <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-[var(--gray-text)]">
              {card.details}
            </p>
          )}
          {card.labelIds && card.labelIds.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {card.labelIds.map((labelId) => {
                const label = labels[labelId];
                if (!label) return null;
                return (
                  <span
                    key={labelId}
                    className="rounded px-1.5 py-0.5 text-[10px] font-medium text-white"
                    style={{ backgroundColor: label.color }}
                    title={label.name}
                  >
                    {label.name}
                  </span>
                );
              })}
            </div>
          )}
          {card.due_date && (
            <div className={clsx("mt-2 flex items-center gap-1 text-xs", getDueDateStyle(card.due_date))}>
              <CalendarIcon />
              <span>{formatDueDate(card.due_date)}</span>
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={() => onDelete(card.id)}
          className="shrink-0 rounded-lg p-1.5 text-[var(--gray-text)] opacity-0 transition-all hover:bg-red-50 hover:text-red-500 group-hover:opacity-100"
          aria-label={`Delete ${card.title}`}
        >
          <TrashIcon />
        </button>
      </div>
    </article>
  );
};
