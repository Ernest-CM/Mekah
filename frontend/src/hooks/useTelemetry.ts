import { useCallback, useEffect, useRef, useState } from 'react';
import type { SessionBehavior } from '../types';

const ZERO: SessionBehavior = {
  click_latency_ms: 0,
  error_count: 0,
  scroll_depth: 0,
  task_stage: 0,
  total_steps: 1,
};

interface ClickSample {
  ts: number;
}

export function useTelemetry(totalSteps: number) {
  const [behavior, setBehavior] = useState<SessionBehavior>({ ...ZERO, total_steps: totalSteps });
  const lastClickRef = useRef<ClickSample | null>(null);
  const latenciesRef = useRef<number[]>([]);

  useEffect(() => {
    setBehavior((b) => ({ ...b, total_steps: totalSteps }));
  }, [totalSteps]);

  useEffect(() => {
    function onScroll() {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      const depth = max > 0 ? Math.min(1, window.scrollY / max) : 0;
      setBehavior((b) => (Math.abs(b.scroll_depth - depth) > 0.05 ? { ...b, scroll_depth: depth } : b));
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const recordClick = useCallback(() => {
    const now = performance.now();
    if (lastClickRef.current) {
      const dt = now - lastClickRef.current.ts;
      latenciesRef.current.push(dt);
      if (latenciesRef.current.length > 12) latenciesRef.current.shift();
      const avg =
        latenciesRef.current.reduce((s, v) => s + v, 0) / latenciesRef.current.length;
      setBehavior((b) => ({ ...b, click_latency_ms: avg }));
    }
    lastClickRef.current = { ts: now };
  }, []);

  const recordError = useCallback(() => {
    setBehavior((b) => ({ ...b, error_count: b.error_count + 1 }));
  }, []);

  const advanceStage = useCallback((delta = 1) => {
    setBehavior((b) => ({ ...b, task_stage: Math.min(b.total_steps, b.task_stage + delta) }));
  }, []);

  const reset = useCallback(() => {
    latenciesRef.current = [];
    lastClickRef.current = null;
    setBehavior({ ...ZERO, total_steps: totalSteps });
  }, [totalSteps]);

  return { behavior, recordClick, recordError, advanceStage, reset };
}
