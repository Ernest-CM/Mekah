/**
 * useAxeValidation — runs axe-core against the live DOM after each adaptation.
 *
 * Two-stage validation architecture (revised.md §4.5):
 *   Stage 1 (pre-action)  : Python WCAG Safety Shield — simulated state check
 *   Stage 2 (post-action) : axe-core — real rendered DOM scan after execution
 *
 * axe-core is the industry-standard accessibility engine (Deque Systems) used
 * in CI pipelines and cited in WCAG tooling literature (Bercaru & Popescu, 2024).
 * It covers ~57% of WCAG 2.1 SCs automatically (per axe-core documentation),
 * complementing the hand-coded Python rules in wcag.py.
 */
import { useCallback, useRef, useState } from 'react';
import axe from 'axe-core';
import type { AxeResult, AxeViolation } from '../types';

const DEBOUNCE_MS = 300;

function extractSCRefs(tags: string[]): string[] {
  return tags
    .filter((t) => /^wcag\d+$/.test(t))
    .map((t) => {
      const digits = t.replace('wcag', '');
      // "1431" → "1.4.3.1", "143" → "1.4.3", "111" → "1.1.1"
      const parts: string[] = [];
      let rest = digits;
      while (rest.length > 0) {
        if (rest.length <= 1) {
          parts.push(rest);
          break;
        }
        parts.push(rest[0]);
        rest = rest.slice(1);
      }
      return `WCAG 2.1 SC ${parts.join('.')}`;
    });
}

export function useAxeValidation() {
  const [result, setResult] = useState<AxeResult | null>(null);
  const [scanning, setScanning] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const scan = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      setScanning(true);
      try {
        const axeResult = await axe.run(document, {
          runOnly: {
            type: 'tag',
            values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'],
          },
          resultTypes: ['violations', 'passes', 'incomplete'],
        });

        const violations: AxeViolation[] = axeResult.violations.map((v) => ({
          id: v.id,
          impact: (v.impact ?? 'minor') as AxeViolation['impact'],
          description: v.description,
          help: v.help,
          helpUrl: v.helpUrl,
          sc_references: extractSCRefs(v.tags),
          node_count: v.nodes.length,
        }));

        setResult({
          scanned_at: new Date().toISOString(),
          violations,
          passes: axeResult.passes.length,
          incomplete: axeResult.incomplete.length,
          source: 'axe-core',
        });
      } catch (err) {
        console.error('[axe-core] scan failed:', err);
      } finally {
        setScanning(false);
      }
    }, DEBOUNCE_MS);
  }, []);

  return { result, scanning, scan };
}
