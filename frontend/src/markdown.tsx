import { type ReactNode } from "react";

export function unemdash(text: string): string {
  return text.replace(/&mdash;|&ndash;/gi, " - ").replace(/\s*[\u2014\u2013\u2015]\s*/g, " - ");
}

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
  const lines = sanitizeSource(unemdash(source)).split("\n");
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
    if (/^(-{3,}|\*{3,})$/.test(line.trim())) {
      blocks.push(<hr key={blocks.length} />);
      i += 1;
      continue;
    }
    if (line.startsWith("> ")) {
      const buf: string[] = [];
      while (i < lines.length && (lines[i] ?? "").startsWith("> ")) {
        buf.push((lines[i] ?? "").replace(/^>\s?/, ""));
        i += 1;
      }
      blocks.push(<blockquote key={blocks.length}>{inline(buf.join(" "))}</blockquote>);
      continue;
    }
    if (line.includes("|") && line.trim().startsWith("|")) {
      const rows: string[][] = [];
      while (i < lines.length && (lines[i] ?? "").includes("|")) {
        const cells = (lines[i] ?? "")
          .split("|")
          .slice(1, -1)
          .map((cell) => cell.trim());
        if (!cells.every((cell) => /^[-:]+$/.test(cell))) rows.push(cells);
        i += 1;
      }
      if (rows[0]) {
        const [head, ...body] = rows;
        blocks.push(
          <table key={blocks.length}>
            <thead>
              <tr>
                {head.map((cell, idx) => (
                  <th key={idx}>{inline(cell)}</th>
                ))}
              </tr>
            </thead>
            {body.length ? (
              <tbody>
                {body.map((row, r) => (
                  <tr key={r}>
                    {row.map((cell, idx) => (
                      <td key={idx}>{inline(cell)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            ) : null}
          </table>,
        );
      }
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
      !(lines[i] ?? "").startsWith("```") &&
      !(lines[i] ?? "").startsWith("> ") &&
      !/^(-{3,}|\*{3,})$/.test((lines[i] ?? "").trim()) &&
      !((lines[i] ?? "").includes("|") && (lines[i] ?? "").trim().startsWith("|"))
    ) {
      buf.push(lines[i] ?? "");
      i += 1;
    }
    blocks.push(<p key={blocks.length}>{inline(buf.join(" "))}</p>);
  }
  return <div className="md">{blocks}</div>;
}
