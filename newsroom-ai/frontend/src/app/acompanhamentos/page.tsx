"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Profile = {
  id: number;
  name: string;
  enabled: boolean;
};

type MatchItem = {
  story: {
    id: number;
  };
};

type ThreadSummary = {
  id: number;
  title: string;
  summary?: string | null;
  category?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  story_count: number;
};

type ThreadStory = {
  id: number;
  title: string;
  source: string;
  published_at?: string | null;
};

type ThreadDetail = {
  thread: ThreadSummary;
  stories: ThreadStory[];
  story_count: number;
};

type RelevantThread = ThreadSummary & {
  relevant_story_count: number;
  latest_relevant_story?: ThreadStory;
};

function formatDate(value?: string | null) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

export default function AcompanhamentosPage() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [profileId, setProfileId] = useState<number | null>(null);
  const [threads, setThreads] = useState<RelevantThread[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");

    try {
      const profilesResponse = await fetch(
        `${API_BASE_URL}/monitoring-profiles`,
        { cache: "no-store" }
      );

      if (!profilesResponse.ok) {
        throw new Error("Erro ao carregar os monitores.");
      }

      const profileData = await profilesResponse.json();

      const profileRows: Profile[] = Array.isArray(profileData)
        ? profileData
        : profileData.profiles ?? profileData.results ?? [];

      setProfiles(profileRows);

      if (profileRows.length === 0) {
        setProfileId(null);
        setThreads([]);
        return;
      }

      const selectedId =
        profileId !== null &&
        profileRows.some((item) => item.id === profileId)
          ? profileId
          : profileRows[0].id;

      setProfileId(selectedId);

      const [matchesResponse, threadsResponse] = await Promise.all([
        fetch(
          `${API_BASE_URL}/monitoring-profiles/${selectedId}/matches?limit=200`,
          { cache: "no-store" }
        ),
        fetch(`${API_BASE_URL}/threads`, {
          cache: "no-store",
        }),
      ]);

      if (!matchesResponse.ok || !threadsResponse.ok) {
        throw new Error("Erro ao carregar os acompanhamentos.");
      }

      const matchesData = await matchesResponse.json();
      const allThreads: ThreadSummary[] =
        await threadsResponse.json();

      const matchedStoryIds = new Set<number>(
        (matchesData.matches ?? []).map(
          (item: MatchItem) => item.story.id
        )
      );

      if (matchedStoryIds.size === 0) {
        setThreads([]);
        return;
      }

      const details = await Promise.all(
        allThreads.map(async (thread) => {
          const response = await fetch(
            `${API_BASE_URL}/threads/${thread.id}`,
            { cache: "no-store" }
          );

          if (!response.ok) {
            return null;
          }

          return (await response.json()) as ThreadDetail;
        })
      );

      const relevant: RelevantThread[] = details
        .filter(
          (item): item is ThreadDetail => item !== null
        )
        .map((detail) => {
          const relevantStories = detail.stories.filter(
            (story) => matchedStoryIds.has(story.id)
          );

          if (relevantStories.length === 0) {
            return null;
          }

          const latestRelevantStory =
            relevantStories[relevantStories.length - 1];

          return {
            ...detail.thread,
            story_count: detail.story_count,
            relevant_story_count: relevantStories.length,
            latest_relevant_story: latestRelevantStory,
          };
        })
        .filter(
          (item): item is RelevantThread => item !== null
        )
        .sort((a, b) => {
          const aTime = new Date(
            a.updated_at ?? a.created_at ?? 0
          ).getTime();

          const bTime = new Date(
            b.updated_at ?? b.created_at ?? 0
          ).getTime();

          return bTime - aTime;
        });

      setThreads(relevant);
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

  useEffect(() => {
    load();
  }, [profileId]);

  const selectedProfile = useMemo(
    () =>
      profiles.find((profile) => profile.id === profileId) ??
      null,
    [profiles, profileId]
  );

  if (loading && profiles.length === 0) {
    return (
      <main className="p-6 md:p-8">
        <div className="mx-auto max-w-6xl">
          <div className="rounded-xl border border-gray-200 bg-white p-6 text-sm text-gray-500 shadow-sm">
            Carregando acompanhamentos...
          </div>
        </div>
      </main>
    );
  }

  if (!loading && profiles.length === 0) {
    return (
      <main className="p-6 md:p-8">
        <div className="mx-auto max-w-6xl">
          <div className="rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
            <h1 className="text-2xl font-bold text-gray-900">
              Acompanhamentos
            </h1>

            <p className="mt-3 max-w-2xl text-gray-600">
              Para acompanhar a evolução das matérias, primeiro crie
              um monitor e defina os temas relevantes.
            </p>

            <Link
              href="/monitoring"
              className="mt-6 inline-flex rounded-lg bg-gray-900 px-4 py-2 text-sm font-semibold text-white hover:bg-gray-800"
            >
              Criar monitor
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="p-6 md:p-8">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-blue-700">
              Client Intelligence
            </p>

            <h1 className="mt-1 text-3xl font-bold text-gray-900">
              Acompanhamentos
            </h1>

            <p className="mt-2 max-w-2xl text-gray-600">
              Veja como os assuntos relevantes para o seu monitor
              evoluem ao longo do tempo.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {profiles.length > 1 && (
              <select
                value={profileId ?? ""}
                onChange={(event) =>
                  setProfileId(Number(event.target.value))
                }
                className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
              >
                {profiles.map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {profile.name}
                  </option>
                ))}
              </select>
            )}

            <button
              onClick={load}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Atualizar
            </button>
          </div>
        </div>

        {selectedProfile && (
          <div className="mt-6 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <div className="text-sm text-gray-500">
              Monitor selecionado
            </div>
            <div className="mt-1 font-semibold text-gray-900">
              {selectedProfile.name}
            </div>
          </div>
        )}

        {error && (
          <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <section className="mt-6">
          {loading ? (
            <div className="rounded-xl border border-gray-200 bg-white p-6 text-sm text-gray-500 shadow-sm">
              Atualizando acompanhamentos...
            </div>
          ) : threads.length === 0 ? (
            <div className="rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
              <h2 className="text-lg font-semibold text-gray-900">
                Nenhum acompanhamento relevante ainda
              </h2>

              <p className="mt-2 text-sm leading-6 text-gray-600">
                Há stories relevantes no monitor somente quando elas
                também fazem parte de um thread. Quando isso acontecer,
                a evolução aparecerá aqui automaticamente.
              </p>
            </div>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {threads.map((thread) => (
                <article
                  key={thread.id}
                  className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    {thread.category && (
                      <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
                        {thread.category}
                      </span>
                    )}

                    <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">
                      {thread.story_count} eventos na timeline
                    </span>

                    <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                      {thread.relevant_story_count} relevantes para o monitor
                    </span>
                  </div>

                  <h2 className="mt-4 text-lg font-semibold text-gray-900">
                    {thread.title}
                  </h2>

                  {thread.summary && (
                    <p className="mt-2 line-clamp-3 text-sm leading-6 text-gray-600">
                      {thread.summary}
                    </p>
                  )}

                  {thread.latest_relevant_story && (
                    <div className="mt-4 rounded-lg bg-gray-50 p-3">
                      <div className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                        Último desenvolvimento relevante
                      </div>

                      <div className="mt-1 text-sm font-medium text-gray-800">
                        {thread.latest_relevant_story.title}
                      </div>

                      <div className="mt-1 text-xs text-gray-500">
                        {thread.latest_relevant_story.source} ·{" "}
                        {formatDate(
                          thread.latest_relevant_story.published_at
                        )}
                      </div>
                    </div>
                  )}

                  <div className="mt-5 flex items-center justify-between">
                    <div className="text-xs text-gray-500">
                      Atualizado em {formatDate(thread.updated_at)}
                    </div>

                    <Link
                      href={`/acompanhamentos/${thread.id}${
                        profileId ? `?profile=${profileId}` : ""
                      }`}
                      className="text-sm font-semibold text-blue-700 hover:underline"
                    >
                      Ver evolução completa →
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
