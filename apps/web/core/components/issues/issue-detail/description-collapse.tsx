/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef, useState } from "react";
import { cn } from "@plane/utils";

type Props = {
  children: React.ReactNode;
  collapsedMaxPx?: number;
};

export function DescriptionCollapse(props: Props) {
  const { children, collapsedMaxPx = 200 } = props;
  const innerRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [overflowing, setOverflowing] = useState(false);
  const [isFocused, setIsFocused] = useState(false);

  useEffect(() => {
    const node = innerRef.current;
    if (!node || typeof ResizeObserver === "undefined") return;
    const update = () => setOverflowing(node.scrollHeight > collapsedMaxPx + 8);
    update();
    const ro = new ResizeObserver(update);
    ro.observe(node);
    return () => ro.disconnect();
  }, [collapsedMaxPx]);

  const shouldClamp = overflowing && !expanded && !isFocused;

  return (
    <div
      ref={wrapperRef}
      onFocusCapture={() => setIsFocused(true)}
      onBlurCapture={(e) => {
        if (!wrapperRef.current?.contains(e.relatedTarget as Node | null)) {
          setIsFocused(false);
        }
      }}
    >
      <div
        className={cn("relative", {
          "max-h-[var(--desc-collapse-max)] overflow-hidden": shouldClamp,
        })}
        style={
          shouldClamp
            ? ({ ["--desc-collapse-max" as string]: `${collapsedMaxPx}px` } as React.CSSProperties)
            : undefined
        }
      >
        <div ref={innerRef}>{children}</div>
        {shouldClamp && (
          <div
            aria-hidden
            className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-b from-transparent to-surface-1"
          />
        )}
      </div>
      {overflowing && !isFocused && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-1 text-body-xs-medium text-primary hover:underline"
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
}
