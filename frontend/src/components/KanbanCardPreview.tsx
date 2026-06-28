import type { Card } from "@/lib/kanban";

type KanbanCardPreviewProps = {
  card: Card;
};

export const KanbanCardPreview = ({ card }: KanbanCardPreviewProps) => (
  <article className="rotate-2 rounded-2xl border border-[var(--accent-yellow)] bg-white px-4 py-3 shadow-[0_18px_32px_rgba(3,33,71,0.2)]">
    <h4 className="font-display text-sm font-semibold leading-tight text-[var(--navy-dark)]">
      {card.title}
    </h4>
    {card.details && (
      <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-[var(--gray-text)]">
        {card.details}
      </p>
    )}
  </article>
);
