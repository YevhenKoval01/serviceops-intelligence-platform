export function formatLabel(value: string): string {
  return value.replaceAll("_", " ").toLowerCase().replace(/^\w/, (letter) => letter.toUpperCase());
}
