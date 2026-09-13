# 2026-09-13 — artifact export menu

## Tried

User asked for Markdown (.md) and Word (.docx) alongside PDF, with a neat end-user choice and solid UX.

## Worked

- One **Export** `<details>` menu on the chat document card and Artifact head (same progressive-disclosure idea as session ⋯).
- `.md` = Blob download of the artifact body.
- `.docx` = minimal OOXML zip (STORE) built in the browser; no new npm package.
- PDF unchanged: focus artifact + `window.print()`.

## Failed / corrected

- First draft used a drop shadow under the menu; removed to stay within the flat editorial chrome.
- TypeScript disliked `Uint8Array` as `BlobPart` under the current lib types; wrapped with `Uint8Array.from(bytes)`.

## Not done

- Docx does not render markdown tables/headings as Word styles (plain lines). Upgrade path noted in `exportArtifact.ts`.
