/** One of eight gradients, picked from an id so a course keeps the same colours everywhere it appears. */
export function meshClass(id: number): string {
  return `mesh-${Math.abs(id) % 8}`;
}

/** Bar colour for a score. The percentage is always printed next to it, so colour is never the only signal. */
export function scoreTone(fraction: number): { bar: string; text: string } {
  if (fraction >= 0.7) return { bar: "bg-[#7ca82e]", text: "text-ok" };
  if (fraction >= 0.4) return { bar: "bg-[#e8b616]", text: "text-warn" };
  return { bar: "bg-[#d8412f]", text: "text-bad" };
}
