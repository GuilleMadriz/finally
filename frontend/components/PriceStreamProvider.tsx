"use client";

import { useCallback, useEffect } from "react";
import { useSseStream } from "@/lib/useSseStream";
import { usePriceStore } from "@/lib/priceStore";
import { useConnectionStore } from "@/lib/connectionStore";
import { streamUrl } from "@/lib/api";
import type { PriceUpdate } from "@/lib/types";

interface PriceStreamProviderProps {
  children: React.ReactNode;
}

export function PriceStreamProvider({ children }: PriceStreamProviderProps) {
  const applyUpdate = usePriceStore((s) => s.applyUpdate);
  const setStatus = useConnectionStore((s) => s.setStatus);

  const onMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const payload = JSON.parse(event.data) as
          | PriceUpdate
          | PriceUpdate[]
          | Record<string, PriceUpdate>;
        const list: PriceUpdate[] = Array.isArray(payload)
          ? payload
          : "ticker" in (payload as PriceUpdate)
            ? [payload as PriceUpdate]
            : Object.values(payload as Record<string, PriceUpdate>);
        for (const u of list) applyUpdate(u);
      } catch {
        // Ignore malformed events; the next tick will replace state.
      }
    },
    [applyUpdate],
  );

  const status = useSseStream(streamUrl("/stream/prices"), { onMessage });

  useEffect(() => {
    setStatus(status);
  }, [status, setStatus]);

  return <>{children}</>;
}
