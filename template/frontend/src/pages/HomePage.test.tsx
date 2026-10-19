import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { HomePage } from "./HomePage";

function renderWithProviders() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("HomePage", () => {
  it("renders the heading", () => {
    renderWithProviders();

    expect(screen.getByText("Stackkit App")).toBeInTheDocument();
  });

  // stackkit:begin api
  it("renders the form", () => {
    renderWithProviders();

    expect(
      screen.getByPlaceholderText("Type something..."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Submit" })).toBeInTheDocument();
  });

  it("submit button is enabled by default", () => {
    renderWithProviders();

    expect(screen.getByRole("button", { name: "Submit" })).toBeEnabled();
  });
  // stackkit:end api
});
