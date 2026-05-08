import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TradeBar } from "./TradeBar";
import { useSelectionStore } from "@/lib/selectionStore";
import { usePortfolioStore } from "@/lib/portfolioStore";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: { trade: vi.fn(), getPortfolio: vi.fn() },
  streamUrl: (p: string) => p,
}));

const mockedApi = vi.mocked(api);

describe("TradeBar", () => {
  beforeEach(() => {
    useSelectionStore.setState({ selected: null });
    usePortfolioStore.setState({ portfolio: null, loading: false, error: null });
    mockedApi.trade.mockResolvedValue({
      ticker: "AAPL",
      side: "buy",
      quantity: 10,
      price: 100,
      cash_balance: 9000,
      realized_pnl: 0,
      snapshot_total_value: 10000,
    });
    mockedApi.getPortfolio.mockResolvedValue({
      cash_balance: 9000,
      total_value: 10000,
      total_unrealized_pnl: 0,
      positions: [],
    });
  });

  afterEach(() => vi.clearAllMocks());

  it("submits a buy with the correct payload", async () => {
    const user = userEvent.setup();
    render(<TradeBar />);

    await user.type(screen.getByLabelText("Ticker"), "aapl");
    await user.type(screen.getByLabelText("Quantity"), "10");
    await user.click(screen.getByLabelText("Buy"));

    expect(mockedApi.trade).toHaveBeenCalledWith({
      ticker: "AAPL",
      side: "buy",
      quantity: 10,
    });
  });

  it("falls back to the selected ticker when ticker input is empty", async () => {
    useSelectionStore.setState({ selected: "TSLA" });
    const user = userEvent.setup();
    render(<TradeBar />);

    await user.type(screen.getByLabelText("Quantity"), "5");
    await user.click(screen.getByLabelText("Sell"));

    expect(mockedApi.trade).toHaveBeenCalledWith({
      ticker: "TSLA",
      side: "sell",
      quantity: 5,
    });
  });

  it("disables buttons when input is invalid", () => {
    render(<TradeBar />);
    expect(screen.getByLabelText("Buy")).toBeDisabled();
    expect(screen.getByLabelText("Sell")).toBeDisabled();
  });

  it("renders backend error text when the trade fails", async () => {
    mockedApi.trade.mockRejectedValueOnce(new Error("Insufficient cash"));
    const user = userEvent.setup();
    render(<TradeBar />);

    await user.type(screen.getByLabelText("Ticker"), "AAPL");
    await user.type(screen.getByLabelText("Quantity"), "1000");
    await user.click(screen.getByLabelText("Buy"));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /Insufficient cash/,
    );
  });
});
