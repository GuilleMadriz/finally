import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WatchlistPanel } from "./WatchlistPanel";
import { usePriceStore } from "@/lib/priceStore";
import { useSelectionStore } from "@/lib/selectionStore";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    getWatchlist: vi.fn(),
    addToWatchlist: vi.fn(),
    removeFromWatchlist: vi.fn(),
  },
  streamUrl: (p: string) => p,
}));

const mockedApi = vi.mocked(api);

const findRow = async (ticker: string) => {
  const rows = await screen.findAllByTestId("watchlist-row");
  const match = rows.find((r) => r.getAttribute("data-ticker") === ticker);
  if (!match) throw new Error(`row ${ticker} not found`);
  return match;
};

describe("WatchlistPanel", () => {
  beforeEach(() => {
    usePriceStore.getState().reset();
    useSelectionStore.setState({ selected: null });
    const blank = (ticker: string) => ({
      ticker,
      price: null,
      previous_price: null,
      change: null,
      change_percent: null,
      direction: "flat" as const,
    });
    mockedApi.getWatchlist.mockResolvedValue({
      entries: [blank("AAPL"), blank("GOOGL")],
    });
    mockedApi.addToWatchlist.mockResolvedValue({ ticker: "TSLA", added: true });
    mockedApi.removeFromWatchlist.mockResolvedValue({
      ticker: "AAPL",
      removed: true,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders watchlist rows from the API", async () => {
    render(<WatchlistPanel />);
    expect(await findRow("AAPL")).toBeInTheDocument();
    expect(await findRow("GOOGL")).toBeInTheDocument();
  });

  it("flashes a row green on an uptick", async () => {
    render(<WatchlistPanel />);
    await findRow("AAPL");

    act(() => {
      usePriceStore.getState().applyUpdate({
        ticker: "AAPL",
        price: 100,
        previous_price: 98,
        timestamp: 1_700_000_000,
        change: 2,
        change_percent: 2.04,
        direction: "up",
      });
    });

    const row = await findRow("AAPL");
    await waitFor(() => expect(row.className).toContain("price-flash-up"));
    await waitFor(() => expect(row.dataset.flash).toBe("up"));
  });

  it("calls addToWatchlist when the form is submitted", async () => {
    const user = userEvent.setup();
    render(<WatchlistPanel />);
    await findRow("AAPL");

    const input = screen.getByTestId("watchlist-add-input");
    await user.type(input, "tsla");
    await user.click(screen.getByTestId("watchlist-add-submit"));

    expect(mockedApi.addToWatchlist).toHaveBeenCalledWith("TSLA");
  });

  it("calls removeFromWatchlist when the row remove button is clicked", async () => {
    const user = userEvent.setup();
    render(<WatchlistPanel />);
    await findRow("AAPL");

    await user.click(screen.getByLabelText("Remove AAPL"));
    expect(mockedApi.removeFromWatchlist).toHaveBeenCalledWith("AAPL");
  });

  it("selects the clicked ticker", async () => {
    const user = userEvent.setup();
    render(<WatchlistPanel />);
    const row = await findRow("GOOGL");
    await user.click(row);
    expect(useSelectionStore.getState().selected).toBe("GOOGL");
  });
});
