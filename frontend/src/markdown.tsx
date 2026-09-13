import { type ReactNode } from "react";

function sanitizeSource(src: string): string {
  return src.replace(/<!--[\s\S]*?-->/g, "").replace(/<[^>]*>/g, "");
}

function safeHref(href: string): string | undefined {
  const trimmed = href.trim();
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return undefined;
}

function inline(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  let key = 0;
  let match: RegExpExecArray | null;
  while ((match = re.exec(text))) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    const token = match[0];
    if (token.startsWith("**")) {
      parts.push(<strong key={key++}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("`")) {
      parts.push(<code key={key++}>{token.slice(1, -1)}</code>);
    } else if (token.startsWith("*")) {
      parts.push(<em key={key++}>{token.slice(1, -1)}</em>);
    } else {
      const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
      const url = link ? safeHref(link[2]) : undefined;
      if (link && url) {
        parts.push(
          <a key={key++} href={url} target="_blank" rel="noreferrer">
            {link[1]}
          </a>,
        );
      } else {
        parts.push(token);
      }
    }
    last = match.index + token.length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

export function MarkdownView({ source }: { source: string }) {
  const lines = sanitizeSource(source).split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i] ?? "";
    if (!line.trim()) {
      i += 1;
      continue;
    }
    if (line.startsWith("### ")) {
      blocks.push(<h3 key={blocks.length}>{inline(line.slice(4))}</h3>);
      i += 1;
      continue;
    }
    if (line.startsWith("## ")) {
      blocks.push(<h2 key={blocks.length}>{inline(line.slice(3))}</h2>);
      i += 1;
      continue;
    }
    if (line.startsWith("# ")) {
      blocks.push(<h1 key={blocks.length}>{inline(line.slice(2))}</h1>);
      i += 1;
      continue;
    }
    if (line.startsWith("```")) {
      const buf: string[] = [];
      i += 1;
      while (i < lines.length && !(lines[i] ?? "").startsWith("```")) {
        buf.push(lines[i] ?? "");
        i += 1;
      }
      i += 1;
      blocks.push(
        <pre key={blocks.length}>
          <code>{buf.join("\n")}</code>
        </pre>,
      );
      continue;
    }
    const ordered = /^\d+\. /.test(line);
    const bullet = /^[-*] /.test(line);
    if (ordered || bullet) {
      const items: string[] = [];
      while (
        i < lines.length &&
        (ordered ? /^\d+\. /.test(lines[i] ?? "") : /^[-*] /.test(lines[i] ?? ""))
      ) {
        items.push((lines[i] ?? "").replace(/^([-*] |\d+\. )/, ""));
        i += 1;
      }
      const Tag = ordered ? "ol" : "ul";
      blocks.push(
        <Tag key={blocks.length}>
          {items.map((item, idx) => (
            <li key={idx}>{inline(item)}</li>
          ))}
        </Tag>,
      );
      continue;
    }
    const buf = [line];
    i += 1;
    while (
      i < lines.length &&
      (lines[i] ?? "").trim() &&
      !/^#{1,3} /.test(lines[i] ?? "") &&
      !/^[-*] /.test(lines[i] ?? "") &&
      !/^\d+\. /.test(lines[i] ?? "") &&
      !(lines[i] ?? "").startsWith("```")
    ) {
      buf.push(lines[i] ?? "");
      i += 1;
    }
    blocks.push(<p key={blocks.length}>{inline(buf.join(" "))}</p>);
  }
  return <div className="md">{blocks}</div>;
}
