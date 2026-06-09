export type Env = {
  TURSO_DATABASE_URL: string;
  TURSO_AUTH_TOKEN: string;
  VOCAB_API_TOKEN: string;
  ALLOWED_ORIGINS: string;
};

export type VocabItem = {
  id: string;
  word: string;
  phrase: string;
  meaning: string;
  sentence: string;
  source: string;
  tags: string[];
  created_at: string;
};

export type VocabPayload = {
  id?: string;
  word?: string;
  phrase?: string;
  meaning?: string;
  sentence?: string;
  source?: string;
  tags?: string[] | string;
  created_at?: string;
};
