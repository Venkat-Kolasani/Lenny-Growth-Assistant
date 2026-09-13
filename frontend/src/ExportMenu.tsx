import { type ExportFormat } from "./exportArtifact";

type Props = {
  onExport: (format: ExportFormat) => void;
  align?: "left" | "right";
};

function closeMenu(target: EventTarget | null) {
  const details = target instanceof Element ? target.closest("details") : null;
  if (details) details.open = false;
}

/** One Export control; formats stay in a short menu (same pattern as session ⋯). */
export function ExportMenu({ onExport, align = "right" }: Props) {
  return (
    <details className={`export-menu${align === "left" ? " export-menu-left" : ""}`}>
      <summary aria-label="Export artifact">Export</summary>
      <div className="export-menu-panel" role="menu">
        <button
          type="button"
          role="menuitem"
          onClick={(event) => {
            onExport("md");
            closeMenu(event.currentTarget);
          }}
        >
          Markdown (.md)
        </button>
        <button
          type="button"
          role="menuitem"
          onClick={(event) => {
            onExport("docx");
            closeMenu(event.currentTarget);
          }}
        >
          Word (.docx)
        </button>
        <button
          type="button"
          role="menuitem"
          onClick={(event) => {
            onExport("pdf");
            closeMenu(event.currentTarget);
          }}
        >
          PDF
        </button>
      </div>
    </details>
  );
}
