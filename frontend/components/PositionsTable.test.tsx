import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { PositionsTable } from "./PositionsTable";
import { usePortfolioStore } from "@/lib/portfolioStore";
import { usePriceStore } from "@/lib/priceStore";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: { getPortfolio: vi.fn() },
  streamUrl: (p: string) => p,
}));

const mockedApi = vi.mocked(api);

describe("PositionsTable", () => {
  beforeEach(() => {
    usePriceStore.getState().reset();
    usePortfolioStore.setState({ portfolio: null, loading: false, error: null });
    mockedApi.getPortfolio.mockResolvedValue({
      cash_balance: 8000,
      total_value: 10000,
      total_unrealized_pnl: 0,
      positions: [
        {
          ticker: "AAPL",
          quantity: 10,
          avg_cost: 100,
          current_price: 100,
          market_value: 1000,
          unrealized_pnl: 0,
          unrealized_pnl_percent: 0,
        },
      ],
    });
  });

  afterEach(() => vi.clearAllMocks());

  it("reflects live prices from the priceStore", async () => {
    render(<PositionsTable />);
    const row = await screen.findByTestId("position-row");
    expect(row.getAttribute("data-ticker")).toBe("AAPL");

    act(() => {
      usePriceStore.getState().applyUpdate({
        ticker: "AAPL",
        price: 110,
        previous_price: 100,
        timestamp: 1_700_000_000,
        change: 10,
        change_percent: 10,
        direction: "up",
      });
    });

    expect(screen.getByTestId("position-pnl-pct")).toHaveTextContent(
      "+10.00%",
    );
  });
});
