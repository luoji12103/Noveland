import { createElement } from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusCards } from "@/features/dashboard/status-cards";
import { systemStatuses } from "@/lib/status";

describe("StatusCards", () => {
  it("renders the initial runnable skeleton statuses", () => {
    render(createElement(StatusCards, { statuses: systemStatuses }));

    expect(screen.getByText("API")).toBeInTheDocument();
    expect(screen.getByText("Health endpoint ready")).toBeInTheDocument();
    expect(screen.getByText("Worlds")).toBeInTheDocument();
    expect(screen.getByText("Domain logic pending")).toBeInTheDocument();
  });
});
