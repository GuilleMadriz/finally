import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { PortfolioHeatmap } from "./PortfolioHeatmap";
import { usePortfolioStore } from "@/lib/portfolioStore";
import { usePriceStore } from "@/lib/priceStore";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: { getPortfolio: vi.fn() },
  streamUrl: (p: string) => p,
}));

const mockedApi = vi.mocked(api);

describe("PortfolioHeatmap", () => {
  beforeEach(() => {
    usePriceStore.getState().reset();
    mockedApi.getPortfolio.mockResolvedValue({
      cash_balance: 5000,
      total_value: 11000,
      total_unrealized_pnl: 100,
      positions: [
        {
          ticker: "AAPL",
          quantity: 10,
          avg_cost: 100,
          current_price: 110,
          market_value: 1100,
          unrealized_pnl: 100,
          unrealized_pnl_percent: 10,
        },
        {
          ticker: "MSFT",
          quantity: 20,
          avg_cost: 250,
          current_price: 245,
          market_value: 4900,
          unrealized_pnl: -100,
          unrealized_pnl_percent: -2,
        },
      ],
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    usePortfolioStore.setState({ portfolio: null, loading: false, error: null });
  });

  it("renders one tile per position plus a cash tile", async () => {
    render(<PortfolioHeatmap />);
    const tiles = await screen.findAllByTestId("heatmap-tile");
    const tickers = tiles.map((t) => t.getAttribute("data-ticker"));
    expect(tickers).toEqual(expect.arrayContaining(["AAPL", "MSFT", "CASH"]));
  });

  it("shows the empty state when there is no portfolio data", () => {
    usePortfolioStore.setState({ portfolio: null });
    mockedApi.getPortfolio.mockResolvedValue({
      cash_balance: 0,
      total_value: 0,
      total_unrealized_pnl: 0,
      positions: [],
    });
    render(<PortfolioHeatmap />);
    expect(screen.getByText(/No allocation data yet/i)).toBeInTheDocument();
  });
});
