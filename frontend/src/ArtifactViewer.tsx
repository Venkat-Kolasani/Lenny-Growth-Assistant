import { HTML_SANDBOX, wrapHtmlArtifact } from "./artifact";
import { ExportMenu } from "./ExportMenu";
import { type ExportFormat } from "./exportArtifact";
import { MarkdownView, unemdash } from "./markdown";

export type Artifact = {
  id: string;
  type: string;
  title: string | null;
  content: string;
};

type Props = {
  artifacts: Artifact[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onExport?: (artifact: Artifact, format: ExportFormat) => void;
};

export function ArtifactViewer({ artifacts, activeId, onSelect, onExport }: Props) {
  const current =
    artifacts.find((item) => item.id === activeId) ?? artifacts[artifacts.length - 1] ?? null;
  if (!current) {
    return (
      <>
        <p className="eyebrow">Artifact</p>
        <p className="muted">
          Ask for a Ship 30/30 essay or a growth brief and it will show up here. Ordinary Q&amp;A stays in chat.
        </p>
      </>
    );
  }
  return (
    <>
      <div className="artifact-head">
        <div className="artifact-head-row">
          <p className="eyebrow">Artifact</p>
          {onExport ? (
            <div className="no-print">
              <ExportMenu onExport={(format) => onExport(current, format)} />
            </div>
          ) : null}
        </div>
        {artifacts.length > 1 ? (
          <div className="artifact-tabs" role="tablist" aria-label="Artifacts">
            {artifacts.map((item) => (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={item.id === current.id}
                onClick={() => onSelect(item.id)}
              >
                {unemdash(item.title ?? item.type)}
              </button>
            ))}
          </div>
        ) : null}
      </div>
      <div className="artifact-body">
        {current.type === "html" ? (
          <iframe
            title={current.title ?? "HTML artifact"}
            sandbox={HTML_SANDBOX}
            srcDoc={wrapHtmlArtifact(current.content)}
          />
        ) : (
          <MarkdownView source={current.content} />
        )}
      </div>
    </>
  );
}
