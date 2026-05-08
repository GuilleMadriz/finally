"use client";

import { useMemo } from "react";
import type { PriceTick } from "@/lib/priceStore";

interface SparklineProps {
  points: PriceTick[];
  width?: number;
  height?: number;
  className?: string;
}

/**
 * Lightweight inline-SVG sparkline. Direction-colored: green if last >= first,
 * red otherwise. Renders nothing until at least 2 points are available.
 */
export function Sparkline({
  points,
  width = 96,
  height = 28,
  className,
}: SparklineProps) {
  const path = useMemo(() => {
    if (points.length < 2) return null;
    const prices = points.map((p) => p.price);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const range = max - min || 1;
    const stepX = width / (points.length - 1);
    const d = points
      .map((p, i) => {
        const x = i * stepX;
        const y = height - ((p.price - min) / range) * height;
        return `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(" ");
    const up = prices[prices.length - 1] >= prices[0];
    return { d, up };
  }, [points, width, height]);

  if (!path) {
    return (
      <svg
        width={width}
        height={height}
        className={className}
        aria-hidden="true"
      />
    );
  }

  const stroke = path.up ? "var(--color-up)" : "var(--color-down)";

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      role="img"
      aria-label="price sparkline"
    >
      <path
        d={path.d}
        fill="none"
        stroke={stroke}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
