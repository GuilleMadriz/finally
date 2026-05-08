import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatPanel } from "./ChatPanel";
import { usePortfolioStore } from "@/lib/portfolioStore";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: { sendChat: vi.fn(), getPortfolio: vi.fn() },
  streamUrl: (p: string) => p,
}));

const mockedApi = vi.mocked(api);

describe("ChatPanel", () => {
  beforeEach(() => {
    usePortfolioStore.setState({ portfolio: null, loading: false, error: null });
    mockedApi.getPortfolio.mockResolvedValue({
      cash_balance: 0,
      total_value: 0,
      total_unrealized_pnl: 0,
      positions: [],
    });
  });

  afterEach(() => vi.clearAllMocks());

  it("renders the optimistic user bubble, then the assistant reply with action chips", async () => {
    mockedApi.sendChat.mockImplementation(async () => {
      await new Promise((r) => setTimeout(r, 20));
      return {
        message: "Bought 2 shares of AAPL.",
        actions: {
          trades: [
            { ticker: "AAPL", side: "buy", quantity: 2, price: 190 },
          ],
          watchlist_changes: [],
        },
      };
    });

    const user = userEvent.setup();
    render(<ChatPanel />);

    const input = screen.getByLabelText("Chat message");
    await user.type(input, "buy 2 aapl");
    await user.click(screen.getByLabelText("Send"));

    expect(screen.getByText("buy 2 aapl")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/Thinking/i);

    await waitFor(() =>
      expect(screen.getByText(/Bought 2 shares of AAPL/)).toBeInTheDocument(),
    );
    expect(screen.getByText(/BUY 2 AAPL/)).toBeInTheDocument();
    expect(mockedApi.getPortfolio).toHaveBeenCalled();
  });

  it("renders a watchlist chip when the assistant adds a ticker", async () => {
    mockedApi.sendChat.mockResolvedValue({
      message: "Added PYPL to your watchlist.",
      actions: {
        trades: [],
        watchlist_changes: [
          { ticker: "PYPL", action: "add", applied: true },
        ],
      },
    });
    const onWatchlistChanged = vi.fn();
    const user = userEvent.setup();
    render(<ChatPanel onWatchlistChanged={onWatchlistChanged} />);

    await user.type(screen.getByLabelText("Chat message"), "watch pypl");
    await user.click(screen.getByLabelText("Send"));

    expect(await screen.findByText(/ADD PYPL/)).toBeInTheDocument();
    await waitFor(() => expect(onWatchlistChanged).toHaveBeenCalled());
  });

  it("disables send when input is empty", () => {
    render(<ChatPanel />);
    expect(screen.getByLabelText("Send")).toBeDisabled();
  });
});
