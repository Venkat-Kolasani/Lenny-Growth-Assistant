import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { ArtifactViewer, type Artifact } from "./ArtifactViewer";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

type Citation = {
  guest: string;
  episode_title: string;
  youtube_url: string | null;
  chunk_id: string;
};

type Message = {
  id: string;
  role: string;
  content: string;
  skill_used: string | null;
  citations: Citation[];
};

type Session = {
  id: string;
  model_provider: string;
  model_name: string;
};

type Pane = "chat" | "artifact";

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
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
  const listRef = useRef<HTMLDivElement>(null);
  const active = sessions.find((s) => s.id === activeId) ?? null;

  const loadSessions = useCallback(async () => {
    const response = await fetch(`${API}/sessions`, { cache: "no-store" });
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
    loadSessions().catch((err) => setBanner(err.message));
  }, [loadSessions]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages, busy]);

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
    setSessions((prev) => [session, ...prev]);
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
      setSessions((prev) => [session, ...prev]);
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
    setSessions((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
    await openSession(updated.id);
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    const text = draft.trim();
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
      setSessions((prev) => [session, ...prev]);
      setActiveId(session.id);
    }
    setDraft("");
    setBusy(true);
    setBanner(null);
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

  return (
    <div className="app">
      {banner ? (
        <div className="banner" role="alert">
          {banner}
        </div>
      ) : null}

      <aside className={`sessions${sidebarOpen ? " open" : ""}`}>
        <div className="sessions-head">
          <p className="eyebrow">Sessions ({sessions.length})</p>
          <button type="button" onClick={createSession}>
            New
          </button>
        </div>
        <nav aria-label="Sessions">
          {sessions.length === 0 ? (
            <p className="muted">No threads yet.</p>
          ) : (
            sessions.map((session) => (
              <button
                key={session.id}
                type="button"
                className={session.id === activeId ? "session active" : "session"}
                onClick={() => openSession(session.id).catch((err) => setBanner(err.message))}
              >
                <span>{shortId(session.id)}</span>
                <small>{session.model_provider}</small>
              </button>
            ))
          )}
        </nav>
      </aside>

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
            <option value="groq">Groq · llama-3.3-70b-versatile</option>
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
          {messages.length === 0 ? (
            <p className="empty">
              Ask about onboarding, pricing, or activation — or say “write me an essay on…”
            </p>
          ) : (
            messages.map((message) => (
              <article key={message.id} className={`turn ${message.role}`}>
                <p>{message.content}</p>
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
            ))
          )}
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

      <section className={`artifact${pane === "artifact" ? "" : " hidden-mobile"}`} aria-label="Artifact viewer">
        <ArtifactViewer artifacts={artifacts} activeId={activeArtifactId} onSelect={setActiveArtifactId} />
      </section>

      {sidebarOpen ? (
        <button type="button" className="scrim" aria-label="Close sessions" onClick={() => setSidebarOpen(false)} />
      ) : null}
    </div>
  );
}

function shortId(id: string) {
  return id.slice(0, 8);
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
  if (response.status === 504) return "The model didn't respond in time — retry, or switch provider.";
  return text || `Request failed (${response.status})`;
}
