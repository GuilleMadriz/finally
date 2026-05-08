import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { PnlChart } from "./PnlChart";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: { getPortfolioHistory: vi.fn() },
  streamUrl: (p: string) => p,
}));

const mockedApi = vi.mocked(api);

describe("PnlChart", () => {
  beforeEach(() => {
    mockedApi.getPortfolioHistory.mockResolvedValue({
      points: [
        { recorded_at: "2026-01-01T00:00:00Z", total_value: 10000 },
        { recorded_at: "2026-01-01T00:00:30Z", total_value: 10250 },
        { recorded_at: "2026-01-01T00:01:00Z", total_value: 10500 },
      ],
    });
  });

  afterEach(() => vi.clearAllMocks());

  it("renders the latest value and a positive change pill", async () => {
    render(<PnlChart />);
    await waitFor(() =>
      expect(screen.getByText("$10,500.00")).toBeInTheDocument(),
    );
    expect(screen.getByText("+5.00%")).toBeInTheDocument();
  });

  it("shows a placeholder when there is no history yet", async () => {
    mockedApi.getPortfolioHistory.mockResolvedValueOnce({ points: [] });
    render(<PnlChart />);
    expect(await screen.findByText(/No history yet/i)).toBeInTheDocument();
  });
});
