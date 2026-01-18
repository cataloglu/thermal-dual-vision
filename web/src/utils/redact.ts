export const REDACTED_VALUE = '***REDACTED***';

export function redactRtspUrl(url: string): string {
  if (!url) {
    return url;
  }
  return url.replace(/\/\/([^/@]+)@/g, `//${REDACTED_VALUE}@`);
}
