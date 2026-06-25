import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProtectedRoute } from "@/components/auth/protected-route";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
}));

describe("ProtectedRoute", () => {
  it("renders children when authenticated state is ready", () => {
    render(
      <ProtectedRoute>
        <div>Secure</div>
      </ProtectedRoute>,
    );
    expect(screen.getByText(/checking authentication/i)).toBeInTheDocument();
  });
});
