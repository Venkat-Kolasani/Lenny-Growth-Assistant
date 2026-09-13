export const HTML_SANDBOX = "allow-same-origin";
export const HTML_CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src data:";

export function wrapHtmlArtifact(html: string): string {
  return (
    "<!DOCTYPE html><html><head><meta charset=\"utf-8\">" +
    `<meta http-equiv="Content-Security-Policy" content="${HTML_CSP}">` +
    `</head><body>${html}</body></html>`
  );
}
