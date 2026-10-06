"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type ThreadInfo = {
  id: number;
  title: string;
  summary?: string | null;
  category?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

type ThreadStory = {
  id: number;
  title: string;
  source: string;
  summary: string;
  url?: string | null;
  category?: string | null;
  priority?: string | null;
  priority_score?: number | null;
  published_at?: string | null;
  discovered_at?: string | null;
  status?: string | null;
  has_meaningful_change?: number | boolean | null;
  new_information?: number | null;
  new_actor?: number | null;
  new_measure?: number | null;
  status_change?: number | null;
  date_change?: number | null;
  quantitative_change?: number | null;
  contradiction?: number | null;
  change_summary?: string | null;
};

type ThreadResponse = {
  thread: ThreadInfo;
  stories: ThreadStory[];
  story_count: number;
};

type Match = {
  story: {
    id: number;
  };
  relevance_score: number;
  urgency_score: number;
  matched_topics: Array<{
    topic: string;
  }>;
  is_alert: boolean;
};

function pct(value?: number | null) {
  if (value === null || value === undefined) {
    return "—";
  }

  return `${Math.round(value * 100)}%`;
}

function formatDate(value?: string | null) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export default function AcompanhamentoDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();

  const threadId = Number(params.id);
  const profileIdParam = searchParams.get("profile");
  const profileId = profileIdParam
    ? Number(profileIdParam)
    : null;

  const [data, setData] = useState<ThreadResponse | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);
  const [profileName, setProfileName] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError("");

        const threadResponse = await fetch(
          `${API_BASE_URL}/threads/${threadId}`,
          { cache: "no-store" }
        );

        if (!threadResponse.ok) {
          throw new Error("Acompanhamento não encontrado.");
        }

        const threadData: ThreadResponse =
          await threadResponse.json();

        setData(threadData);

        if (profileId) {
          const matchesResponse = await fetch(
            `${API_BASE_URL}/monitoring-profiles/${profileId}/matches?limit=200`,
            { cache: "no-store" }
          );

          if (matchesResponse.ok) {
            const matchesData = await matchesResponse.json();
            setMatches(matchesData.matches ?? []);
            setProfileName(matchesData.profile?.name ?? "");
          }
        }
      } catch (err) {
        console.error(err);
        setError(
          err instanceof Error
            ? err.message
            : "Erro inesperado."
        );
      } finally {
        setLoading(false);
      }
    }

    if (Number.isFinite(threadId)) {
      load();
    }
  }, [threadId, profileId]);

  const matchesByStory = useMemo(() => {
    const map = new Map<number, Match>();

    for (const match of matches) {
      map.set(match.story.id, match);
    }

    return map;
  }, [matches]);

  if (loading) {
    return (
      <main className="p-6 md:p-8">
        <div className="mx-auto max-w-5xl">
          <div className="rounded-xl border border-gray-200 bg-white p-6 text-sm text-gray-500 shadow-sm">
            Carregando timeline...
          </div>
        </div>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="p-6 md:p-8">
        <div className="mx-auto max-w-5xl">
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
            {error || "Acompanhamento não encontrado."}
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="p-6 md:p-8">
      <div className="mx-auto max-w-5xl">
        <Link
          href="/acompanhamentos"
          className="text-sm font-medium text-blue-700 hover:underline"
        >
          ← Voltar para acompanhamentos
        </Link>

        <header className="mt-5 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            {data.thread.category && (
              <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
                {data.thread.category}
              </span>
            )}

            <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">
              {data.story_count} eventos
            </span>

            {profileName && (
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                Monitor: {profileName}
              </span>
            )}
          </div>

          <h1 className="mt-4 text-3xl font-bold tracking-tight text-gray-900">
            {data.thread.title}
          </h1>

          {data.thread.summary && (
            <p className="mt-3 max-w-3xl text-base leading-7 text-gray-600">
              {data.thread.summary}
            </p>
          )}

          <div className="mt-5 text-sm text-gray-500">
            Última atualização: {formatDate(data.thread.updated_at)}
          </div>
        </header>

        <section className="mt-8">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              Timeline
            </h2>
            <p className="mt-1 text-sm text-gray-500">
              Evolução cronológica desta matéria.
            </p>
          </div>

          <div className="mt-6">
            {data.stories.map((story, index) => {
              const match = matchesByStory.get(story.id);
              const isRelevant = Boolean(match);

              return (
                <div
                  key={story.id}
                  className="relative grid grid-cols-[28px_1fr] gap-4"
                >
                  <div className="relative flex justify-center">
                    <div
                      className={[
                        "mt-2 h-3 w-3 rounded-full border-2",
                        isRelevant
                          ? "border-blue-700 bg-blue-700"
                          : "border-gray-300 bg-white",
                      ].join(" ")}
                    />

                    {index < data.stories.length - 1 && (
                      <div className="absolute bottom-0 top-5 w-px bg-gray-200" />
                    )}
                  </div>

                  <article className="mb-5 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-medium text-gray-500">
                        {formatDate(
                          story.published_at ??
                            story.discovered_at
                        )}
                      </span>

                      <span className="rounded-full bg-gray-100 px-2 py-1 text-[11px] font-medium text-gray-600">
                        {story.source}
                      </span>

                      {isRelevant && (
                        <span className="rounded-full bg-blue-50 px-2 py-1 text-[11px] font-semibold text-blue-700">
                          Relevante para o monitor
                        </span>
                      )}

                      {match?.is_alert && (
                        <span className="rounded-full bg-red-50 px-2 py-1 text-[11px] font-semibold text-red-700">
                          Atenção imediata
                        </span>
                      )}
                    </div>

                    <h3 className="mt-3 text-lg font-semibold text-gray-900">
                      {story.title}
                    </h3>

                    <p className="mt-2 text-sm leading-6 text-gray-600">
                      {story.summary}
                    </p>

                    {story.change_summary && (
                      <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
                        <div className="text-xs font-semibold uppercase tracking-wide text-amber-700">
                          O que mudou
                        </div>
                        <p className="mt-2 text-sm leading-6 text-amber-900">
                          {story.change_summary}
                        </p>
                      </div>
                    )}

                    {match && (
                      <div className="mt-4 rounded-lg bg-blue-50/70 p-4">
                        <div className="text-xs font-semibold uppercase tracking-wide text-blue-700">
                          Relevância para o monitor
                        </div>

                        <div className="mt-3 flex flex-wrap gap-2">
                          <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-gray-700">
                            Relevância {pct(match.relevance_score)}
                          </span>

                          <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-gray-700">
                            Urgência {pct(match.urgency_score)}
                          </span>

                          {match.matched_topics.map((topic, topicIndex) => (
                            <span
                              key={`${story.id}-${topic.topic}-${topicIndex}`}
                              className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-blue-700"
                            >
                              {topic.topic}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="mt-5 flex flex-wrap items-center gap-4">
                      <Link
                        href={`/stories/${story.id}`}
                        className="text-sm font-semibold text-blue-700 hover:underline"
                      >
                        Ver detalhes da story →
                      </Link>

                      {story.url && (
                        <a
                          href={story.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-sm font-medium text-gray-600 hover:underline"
                        >
                          Abrir fonte oficial ↗
                        </a>
                      )}
                    </div>
                  </article>
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </main>
  );
}
