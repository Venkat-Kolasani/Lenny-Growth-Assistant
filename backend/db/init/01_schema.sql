CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_metadata JSONB NOT NULL DEFAULT '{}',
    model_provider TEXT NOT NULL DEFAULT 'groq',
    model_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    skill_used TEXT,
    citations JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX messages_session_id_idx ON messages (session_id, created_at);

CREATE TABLE artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    message_id UUID REFERENCES messages(id),
    type TEXT NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX artifacts_session_id_idx ON artifacts (session_id);

CREATE TABLE transcript_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_guest TEXT NOT NULL,
    episode_title TEXT NOT NULL,
    youtube_url TEXT,
    publish_date DATE,
    topic_tags TEXT[] NOT NULL DEFAULT '{}',
    chunk_index INT NOT NULL,
    contextual_prefix TEXT,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(768),
    search_vector TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(contextual_prefix, '') || ' ' || chunk_text)
    ) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (episode_guest, episode_title, chunk_index)
);
-- ponytail: ivfflat lists=100 is fine until the corpus is loaded; rebuild if recall drops
CREATE INDEX transcript_chunks_embedding_idx
    ON transcript_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX transcript_chunks_search_vector_idx
    ON transcript_chunks USING gin (search_vector);
CREATE INDEX transcript_chunks_topic_tags_idx
    ON transcript_chunks USING gin (topic_tags);

CREATE TABLE retrieval_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES messages(id),
    query TEXT NOT NULL,
    method TEXT NOT NULL,
    retrieved_chunk_ids UUID[] NOT NULL,
    scores JSONB,
    confidence FLOAT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
