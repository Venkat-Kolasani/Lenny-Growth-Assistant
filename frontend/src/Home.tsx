export default function Home() {
  return (
    <div className="home">
      <div className="home-spine" aria-hidden="true" />
      <header className="home-top">
        <p className="eyebrow">Lenny's Podcast</p>
        <p className="muted">301 episodes in the corpus</p>
      </header>
      <main className="home-main">
        <h1>The Growth Assistant</h1>
        <p className="lede">
          A desk for grounded questions, Ship 30/30 essays, and one-page growth briefs. The source stays on the page.
        </p>
        <a className="cta" href="#work">
          Enter
        </a>
        <ol className="home-cols">
          <li>
            <em>01</em>
            <strong>Ask</strong>
            <span>Answers name a guest and an episode. If the transcripts do not cover it, it says so.</span>
          </li>
          <li>
            <em>02</em>
            <strong>Write</strong>
            <span>An essay or a brief lands as an artifact you can read and save as PDF.</span>
          </li>
          <li>
            <em>03</em>
            <strong>Keep</strong>
            <span>Chat is the path. The artifact is the work you take with you.</span>
          </li>
        </ol>
      </main>
      <footer className="home-foot">
        <p className="muted">Cloud or this machine. Switch in the header.</p>
      </footer>
    </div>
  );
}
