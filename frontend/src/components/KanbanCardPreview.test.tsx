import { render, screen } from "@testing-library/react";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";

const card = {
    id: "card-1",
    title: "Preview title",
    details: "Preview details",
};

describe("KanbanCardPreview", () => {
    it("renders the card title and details", () => {
        render(<KanbanCardPreview card={card} />);

        expect(screen.getByText("Preview title")).toBeInTheDocument();
        expect(screen.getByText("Preview details")).toBeInTheDocument();
    });
});
