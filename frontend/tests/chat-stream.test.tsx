import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChatPanel } from "@/components/chat/chat-panel";

describe("ChatPanel", () => {
  it("renders the chat composer", () => {
    render(<ChatPanel repositoryId={1} />);
    expect(screen.getByText(/chat with citations/i)).toBeInTheDocument();
  });
});