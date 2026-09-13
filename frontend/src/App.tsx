import { type CSSProperties, type FormEvent, type PointerEvent as ReactPointerEvent, useCallback, useEffect, useRef, useState } from "react";

import { ArtifactViewer, type Artifact } from "./ArtifactViewer";
import { MarkdownView, unemdash } from "./markdown";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

type Citation = {
  guest: string;
  episode_title: string;
  youtube_url: string | null;
  chunk_id: string;
};

type ArtifactRef = {
  id: string;
  type: string;
  title: string | null;
};

type Message = {
  id: string;
  role: string;
  content: string;
  skill_used: string | null;
  citations: Citation[];
  reasoning?: string | null;
  artifact?: ArtifactRef | null;
};

type Session = {
  id: string;
  model_provider: string;
  model_name: string;
  title?: string | null;
  archived?: boolean;
};

type Pane = "chat" | "artifact";
type DialogState = { kind: "delete"; id: string; label: string } | { kind: "rename"; id: string } | null;
type PaneWidths = { sessions: number; artifact: number };

const PANE_KEY = "pane-widths";

function readPanes(): PaneWidths {
  try {
    const parsed = JSON.parse(localStorage.getItem(PANE_KEY) ?? "");
    return {
      sessions: Math.max(160, Math.min(420, Number(parsed.sessions) || 220)),
      artifact: Math.max(200, Math.min(520, Number(parsed.artifact) || 280)),
    };
  } catch {
    return { sessions: 220, artifact: 280 };
  }
}

const SAMPLE_BANK = [
  "Why do most AI products fail in production?",
  "How should a CEO stay in the details without micromanaging?",
  "How do you build a high-performing growth team?",
  "When should a company invest in a new acquisition channel?",
  "How do you know when it's time to leave your job?",
  "What is Brian Chesky's new playbook for running product?",
  "How do you craft a sales pitch that actually wins deals?",
  "How did Drew Houston build Dropbox as a founder?",
  "Why might ChatGPT become the next big growth channel?",
  "What is Shreyas Doshi's art of product management from Stripe?",
  "Write me a Ship 30/30 essay on activation for a B2B product",
  "Write a growth brief for shipping an AI feature people will actually use",
];

function pickSamples(seed: string, n = 5): string[] {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i++) h = Math.imul(h ^ seed.charCodeAt(i), 16777619);
  const copy = [...SAMPLE_BANK];
  for (let i = copy.length - 1; i > 0; i--) {
    h = Math.imul(h ^ (h >>> 16), 2246822519) >>> 0;
    const j = h % (i + 1);
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy.slice(0, n);
}

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [showArchived, setShowArchived] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [activeArtifactId, setActiveArtifactId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);
  const [pane, setPane] = useState<Pane>("chat");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [artifactBadge, setArtifactBadge] = useState(false);
  const [dialog, setDialog] = useState<DialogState>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [panes, setPanes] = useState(readPanes);
  const listRef = useRef<HTMLDivElement>(null);
  const emptySeed = useRef(`empty-${Math.random().toString(36).slice(2)}`);
  const active = sessions.find((s) => s.id === activeId) ?? null;
  const samples = pickSamples(activeId ?? emptySeed.current);
  const started = messages.some((message) => message.role === "user" || message.role === "assistant");

  const loadSessions = useCallback(async (archived: boolean) => {
    const query = archived ? "?archived=true" : "";
    const response = await fetch(`${API}/sessions${query}`, { cache: "no-store" });
    if (!response.ok) throw new Error(await readError(response));
    const data: unknown = await response.json();
    const list = Array.isArray(data) ? (data as Session[]) : [];
    setSessions(list);
  }, []);

  const openSession = useCallback(async (id: string) => {
    const response = await fetch(`${API}/sessions/${id}`, { cache: "no-store" });
    if (!response.ok) throw new Error(await readError(response));
    const data = await response.json();
    setActiveId(id);
    setMessages(data.messages ?? []);
    const nextArtifacts: Artifact[] = data.artifacts ?? [];
    setArtifacts(nextArtifacts);
    setActiveArtifactId(nextArtifacts.at(-1)?.id ?? null);
    setArtifactBadge(false);
    setSidebarOpen(false);
  }, []);

  useEffect(() => {
    loadSessions(showArchived).catch((err) => setBanner(err.message));
  }, [loadSessions, showArchived]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages, busy]);

  function clearThread() {
    setActiveId(null);
    setMessages([]);
    setArtifacts([]);
    setActiveArtifactId(null);
  }

  async function removeFromList(id: string) {
    let remaining: Session[] = [];
    setSessions((prev) => {
      remaining = prev.filter((session) => session.id !== id);
      return remaining;
    });
    if (activeId !== id) return;
    if (remaining[0]) {
      await openSession(remaining[0].id).catch((err) => setBanner(err.message));
      return;
    }
    clearThread();
  }

  async function createSession() {
    setBanner(null);
    const response = await fetch(`${API}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
      cache: "no-store",
    });
    if (!response.ok) {
      setBanner(await readError(response));
      return;
    }
    const session: Session = await response.json();
    setShowArchived(false);
    await loadSessions(false);
    setActiveId(session.id);
    setMessages([]);
    setArtifacts([]);
    setActiveArtifactId(null);
    setArtifactBadge(false);
    setSidebarOpen(false);
  }

  async function changeProvider(provider: string) {
    setBanner(null);
    let sessionId = activeId;
    if (!sessionId) {
      const created = await fetch(`${API}/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (!created.ok) {
        setBanner(await readError(created));
        return;
      }
      const session: Session = await created.json();
      sessionId = session.id;
      setShowArchived(false);
      await loadSessions(false);
      setActiveId(session.id);
      setMessages([]);
      setArtifacts([]);
    }
    const response = await fetch(`${API}/sessions/${sessionId}/provider`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider }),
    });
    if (!response.ok) {
      setBanner(await readError(response));
      return;
    }
    const updated: Session = await response.json();
    setSessions((prev) =>
      prev.map((item) =>
        item.id === updated.id ? { ...updated, title: item.title ?? updated.title, archived: item.archived } : item,
      ),
    );
    await openSession(updated.id);
  }

  async function deleteSession(id: string) {
    const response = await fetch(`${API}/sessions/${id}`, { method: "DELETE" });
    if (!response.ok && response.status !== 404) {
      setBanner(await readError(response));
      return;
    }
    await removeFromList(id);
  }

  async function patchSession(id: string, body: { title?: string; archived?: boolean }) {
    const response = await fetch(`${API}/sessions/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      setBanner(await readError(response));
      return null;
    }
    return (await response.json()) as Session;
  }

  async function confirmDialog() {
    if (dialog?.kind === "delete") {
      const id = dialog.id;
      setDialog(null);
      await deleteSession(id);
      return;
    }
    if (dialog?.kind === "rename") {
      const id = dialog.id;
      setDialog(null);
      const updated = await patchSession(id, { title: renameDraft });
      if (updated) {
        setSessions((prev) => prev.map((session) => (session.id === id ? { ...session, ...updated } : session)));
      }
    }
  }

  async function setArchived(id: string, archived: boolean) {
    const updated = await patchSession(id, { archived });
    if (updated) await removeFromList(id);
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    await sendText(draft);
  }

  async function sendText(raw: string) {
    const text = raw.trim();
    if (!text || busy) return;
    let sessionId = activeId;
    if (!sessionId) {
      const response = await fetch(`${API}/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (!response.ok) {
        setBanner(await readError(response));
        return;
      }
      const session: Session = await response.json();
      sessionId = session.id;
      setShowArchived(false);
      await loadSessions(false);
      setActiveId(session.id);
    }
    setDraft("");
    setBusy(true);
    setBanner(null);
    setSessions((prev) =>
      prev.map((s) => (s.id === sessionId && !s.title ? { ...s, title: text.slice(0, 80) } : s)),
    );
    setMessages((prev) => [
      ...prev,
      { id: "local-user", role: "user", content: text, skill_used: null, citations: [] },
    ]);
    try {
      const response = await fetch(`${API}/sessions/${sessionId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: text }),
      });
      if (!response.ok) throw new Error(await readError(response));
      const reply: Message & { artifact?: Artifact | null } = await response.json();
      setMessages((prev) => [...prev, reply]);
      if (reply.artifact) {
        setArtifacts((prev) => [...prev, reply.artifact!]);
        setActiveArtifactId(reply.artifact.id);
        if (pane === "chat") setArtifactBadge(true);
      }
    } catch (err) {
      setBanner(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  function printArtifact(id: string) {
    setActiveArtifactId(id);
    setPane("artifact");
    window.setTimeout(() => window.print(), 80);
  }

  function startResize(side: "sessions" | "artifact", event: ReactPointerEvent<HTMLDivElement>) {
    event.preventDefault();
    const origin = event.clientX;
    const start = panes[side];
    const move = (ev: PointerEvent) => {
      const dx = ev.clientX - origin;
      const next = Math.max(160, Math.min(520, side === "sessions" ? start + dx : start - dx));
      setPanes((prev) => ({ ...prev, [side]: next }));
    };
    const up = (ev: PointerEvent) => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      const dx = ev.clientX - origin;
      const next = Math.max(160, Math.min(520, side === "sessions" ? start + dx : start - dx));
      const widths = { ...panes, [side]: next };
      setPanes(widths);
      localStorage.setItem(PANE_KEY, JSON.stringify(widths));
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  return (
    <div
      className="app"
      style={{ "--sessions-w": `${panes.sessions}px`, "--artifact-w": `${panes.artifact}px` } as CSSProperties}
    >
      {banner ? (
        <div className="banner" role="alert">
          <span>{unemdash(banner)}</span>
          <button type="button" className="ghost" aria-label="Dismiss error" onClick={() => setBanner(null)}>
            ×
          </button>
        </div>
      ) : null}

      <aside className={`sessions${sidebarOpen ? " open" : ""}`}>
        <div className="sessions-head">
          <div>
            <a className="home-link" href="#">
              Home
            </a>
            <p className="eyebrow">Sessions ({sessions.length})</p>
          </div>
          <button type="button" onClick={() => void createSession()}>
            New
          </button>
        </div>
        <div className="session-filter" role="tablist" aria-label="Session status">
          <button type="button" role="tab" aria-selected={!showArchived} onClick={() => setShowArchived(false)}>
            Active
          </button>
          <button type="button" role="tab" aria-selected={showArchived} onClick={() => setShowArchived(true)}>
            Archived
          </button>
        </div>
        <nav aria-label="Sessions">
          {sessions.length === 0 ? (
            <p className="muted">{showArchived ? "No archived threads." : "No threads yet."}</p>
          ) : (
            sessions.map((session) => (
              <div key={session.id} className="session-row">
                <button
                  type="button"
                  className={session.id === activeId ? "session active" : "session"}
                  title={sessionLabel(session)}
                  onClick={() => openSession(session.id).catch((err) => setBanner(err.message))}
                >
                  <span>{sessionLabel(session)}</span>
                  <small>{session.model_provider}</small>
                </button>
                <details
                  className="session-menu"
                  onToggle={(event) => {
                    if (!event.currentTarget.open) return;
                    document.querySelectorAll<HTMLDetailsElement>("details.session-menu").forEach((item) => {
                      if (item !== event.currentTarget) item.open = false;
                    });
                  }}
                >
                  <summary aria-label={`Actions for ${sessionLabel(session)}`}>⋯</summary>
                  <div className="session-menu-panel">
                    <button
                      type="button"
                      onClick={(event) => {
                        event.currentTarget.closest("details")?.removeAttribute("open");
                        setRenameDraft(sessionLabel(session));
                        setDialog({ kind: "rename", id: session.id });
                      }}
                    >
                      Rename
                    </button>
                    <button
                      type="button"
                      onClick={(event) => {
                        event.currentTarget.closest("details")?.removeAttribute("open");
                        void setArchived(session.id, !showArchived);
                      }}
                    >
                      {showArchived ? "Restore" : "Archive"}
                    </button>
                    <button
                      type="button"
                      onClick={(event) => {
                        event.currentTarget.closest("details")?.removeAttribute("open");
                        setDialog({ kind: "delete", id: session.id, label: sessionLabel(session) });
                      }}
                    >
                      Delete
                    </button>
                  </div>
                </details>
              </div>
            ))
          )}
        </nav>
      </aside>

      <div
        className="gutter gutter-sessions"
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize sessions"
        onPointerDown={(event) => startResize("sessions", event)}
      />

      <main className={`chat${pane === "chat" ? "" : " hidden-mobile"}`}>
        <header className="chat-head">
          <button type="button" className="menu" onClick={() => setSidebarOpen(true)} aria-label="Open sessions">
            Sessions
          </button>
          <label className="sr" htmlFor="provider">
            Model provider
          </label>
          <select
            id="provider"
            className="model-select"
            value={active?.model_provider ?? "groq"}
            onChange={(event) => changeProvider(event.target.value)}
            aria-live="polite"
          >
            <option value="groq">Groq · openai/gpt-oss-120b</option>
            <option value="ollama">Ollama (local) · llama3.2:3b</option>
          </select>
          <div className="tabs" role="tablist">
            <button type="button" role="tab" aria-selected={pane === "chat"} onClick={() => setPane("chat")}>
              Chat
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={pane === "artifact"}
              onClick={() => {
                setPane("artifact");
                setArtifactBadge(false);
              }}
            >
              Artifact{artifactBadge ? " · new" : ""}
            </button>
          </div>
        </header>

        <div className="thread" ref={listRef} aria-live="polite">
          {messages.map((message) => (
            <article key={message.id} className={`turn ${message.role}`}>
              <p className="role">{roleLabel(message.role)}</p>
              {message.artifact ? (
                <ArtifactCard
                  title={message.artifact.title ?? "Untitled"}
                  kind={artifactKind(message.skill_used)}
                  onOpen={() => {
                    setActiveArtifactId(message.artifact!.id);
                    setPane("artifact");
                    setArtifactBadge(false);
                  }}
                  onPrint={() => printArtifact(message.artifact!.id)}
                />
              ) : message.role === "user" ? (
                <p>{message.content}</p>
              ) : (
                <MarkdownView source={message.content} />
              )}
              {message.reasoning ? (
                <details className="trace">
                  <summary>Thinking</summary>
                  <pre>{unemdash(message.reasoning)}</pre>
                </details>
              ) : null}
              {message.citations?.length ? (
                <ul className="cites">
                  {message.citations.map((cite) => (
                    <li key={cite.chunk_id}>
                      <a href={cite.youtube_url ?? undefined} target="_blank" rel="noreferrer">
                        View source: episode with {cite.guest}
                      </a>
                      <span>{cite.episode_title}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </article>
          ))}
          {!started ? (
            <div className="empty">
              <p>Ask about onboarding, pricing, or activation, or say “write me an essay on…”</p>
              <ul className="samples">
                {samples.map((question) => (
                  <li key={question}>
                    <button type="button" className="sample" onClick={() => void sendText(question)}>
                      {question}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {busy ? <p className="muted">Retrieving and writing…</p> : null}
        </div>

        <form className="composer" onSubmit={send}>
          <label className="sr" htmlFor="prompt">
            Message
          </label>
          <textarea
            id="prompt"
            rows={3}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask a grounded product or growth question"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                e.currentTarget.form?.requestSubmit();
              }
            }}
          />
          <button type="submit" disabled={busy || !draft.trim()}>
            Send
          </button>
        </form>
      </main>

      <div
        className="gutter gutter-artifact"
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize artifact"
        onPointerDown={(event) => startResize("artifact", event)}
      />

      <section className={`artifact${pane === "artifact" ? "" : " hidden-mobile"}`} aria-label="Artifact viewer">
        <ArtifactViewer
          artifacts={artifacts}
          activeId={activeArtifactId}
          onSelect={setActiveArtifactId}
          onPrint={() => activeArtifactId && printArtifact(activeArtifactId)}
        />
      </section>

      {sidebarOpen ? (
        <button type="button" className="scrim" aria-label="Close sessions" onClick={() => setSidebarOpen(false)} />
      ) : null}

      {dialog ? (
        <dialog
          className="session-dialog"
          aria-labelledby="session-dialog-title"
          ref={(el) => {
            if (el && !el.open) el.showModal();
          }}
          onClose={() => setDialog(null)}
        >
          {dialog.kind === "delete" ? (
            <>
              <h2 id="session-dialog-title">Delete session</h2>
              <p>
                Delete “{dialog.label}”? Messages and artifacts will be removed.
              </p>
              <div className="actions">
                <button type="button" className="ghost" onClick={() => setDialog(null)}>
                  Cancel
                </button>
                <button type="button" onClick={() => void confirmDialog()}>
                  Delete
                </button>
              </div>
            </>
          ) : (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void confirmDialog();
              }}
            >
              <h2 id="session-dialog-title">Rename session</h2>
              <label className="sr" htmlFor="session-title">
                Title
              </label>
              <input
                id="session-title"
                value={renameDraft}
                onChange={(event) => setRenameDraft(event.target.value)}
                autoFocus
              />
              <div className="actions">
                <button type="button" className="ghost" onClick={() => setDialog(null)}>
                  Cancel
                </button>
                <button type="submit">Save</button>
              </div>
            </form>
          )}
        </dialog>
      ) : null}
    </div>
  );
}

function shortId(id: string) {
  return id.slice(0, 8);
}

function sessionLabel(session: Session) {
  const title = session.title?.trim();
  return title || shortId(session.id);
}

function roleLabel(role: string) {
  if (role === "user") return "You";
  if (role === "assistant") return "Assistant";
  return "System";
}

function artifactKind(skill: string | null) {
  if (skill === "growth_brief") return "Growth brief";
  if (skill === "ship30_essay") return "Essay";
  return "Document";
}

function ArtifactCard({
  title,
  kind,
  onOpen,
  onPrint,
}: {
  title: string;
  kind: string;
  onOpen: () => void;
  onPrint: () => void;
}) {
  return (
    <div className="doc-card">
      <button type="button" className="doc-card-main" onClick={onOpen}>
        <small>{kind}</small>
        <strong>{unemdash(title)}</strong>
      </button>
      <button type="button" className="ghost no-print" onClick={onPrint}>
        Download PDF
      </button>
    </div>
  );
}

async function readError(response: Response) {
  const text = await response.text();
  try {
    const json = JSON.parse(text) as { detail?: string };
    if (typeof json.detail === "string") return json.detail;
  } catch {
    /* raw */
  }
  if (response.status === 503) return "Database unreachable.";
  if (response.status === 504) return "The model didn't respond in time. Retry, or switch provider.";
  return text || `Request failed (${response.status})`;
}
