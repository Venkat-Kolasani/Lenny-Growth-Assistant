import { HTML_SANDBOX, wrapHtmlArtifact } from "./artifact";
import { MarkdownView } from "./markdown";

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
};

export function ArtifactViewer({ artifacts, activeId, onSelect }: Props) {
  const current =
    artifacts.find((item) => item.id === activeId) ?? artifacts[artifacts.length - 1] ?? null;
  if (!current) {
    return (
      <>
        <p className="eyebrow">Artifact</p>
        <p className="muted">
          Essays and growth briefs will render here. This thread has not produced one yet.
        </p>
      </>
    );
  }
  return (
    <>
      <div className="artifact-head">
        <p className="eyebrow">Artifact</p>
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
                {item.title ?? item.type}
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
