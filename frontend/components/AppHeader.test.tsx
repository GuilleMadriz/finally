import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AppHeader } from "./AppHeader";
import { useConnectionStore } from "@/lib/connectionStore";
import { usePortfolioStore } from "@/lib/portfolioStore";

describe("AppHeader", () => {
  beforeEach(() => {
    usePortfolioStore.setState({ portfolio: null, loading: false, error: null });
    useConnectionStore.setState({ status: "connecting" });
  });

  afterEach(() => {
    useConnectionStore.setState({ status: "connecting" });
  });

  it("shows the live total value from the portfolio store", () => {
    usePortfolioStore.setState({
      portfolio: {
        cash_balance: 5000,
        total_value: 12345.67,
        total_unrealized_pnl: 250,
        positions: [],
      },
      loading: false,
      error: null,
    });
    render(<AppHeader />);
    expect(screen.getByText("$12,345.67")).toBeInTheDocument();
    expect(screen.getByText("$5,000.00")).toBeInTheDocument();
    expect(screen.getByText("+$250.00")).toBeInTheDocument();
  });

  it("colors the connection dot by SSE state", () => {
    useConnectionStore.setState({ status: "connected" });
    render(<AppHeader />);
    const status = screen.getByTestId("connection-status");
    expect(status.querySelector("span.bg-up")).not.toBeNull();
    expect(status).toHaveAttribute("aria-label", "SSE live");
  });

  it("shows the offline state when disconnected", () => {
    useConnectionStore.setState({ status: "disconnected" });
    render(<AppHeader />);
    expect(screen.getByTestId("connection-status")).toHaveAttribute(
      "aria-label",
      "SSE offline",
    );
  });
});
