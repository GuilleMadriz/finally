import { beforeEach, describe, expect, it } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { MainChart } from "./MainChart";
import { usePriceStore } from "@/lib/priceStore";
import { useSelectionStore } from "@/lib/selectionStore";

describe("MainChart", () => {
  beforeEach(() => {
    usePriceStore.getState().reset();
    useSelectionStore.setState({ selected: null });
  });

  it("shows a placeholder when no ticker is selected", () => {
    render(<MainChart />);
    expect(screen.getByText(/Select a ticker/i)).toBeInTheDocument();
  });

  it("subscribes to the selected ticker and renders its price", () => {
    useSelectionStore.setState({ selected: "AAPL" });
    act(() => {
      usePriceStore.getState().applyUpdate({
        ticker: "AAPL",
        price: 191.23,
        previous_price: 190.0,
        timestamp: 1_700_000_000,
        change: 1.23,
        change_percent: 0.65,
        direction: "up",
      });
      usePriceStore.getState().applyUpdate({
        ticker: "AAPL",
        price: 192.5,
        previous_price: 191.23,
        timestamp: 1_700_000_001,
        change: 1.27,
        change_percent: 0.66,
        direction: "up",
      });
    });

    render(<MainChart />);
    expect(screen.getByRole("heading")).toHaveTextContent("AAPL");
    expect(screen.getAllByText("$192.50").length).toBeGreaterThan(0);
    expect(screen.getByRole("img", { name: /price chart/i })).toBeInTheDocument();
  });
});
