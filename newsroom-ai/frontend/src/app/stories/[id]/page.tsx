"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import StoryContextLinks from "@/components/StoryContextLinks";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Story = {
  id: number;
  title: string;
  source: string;
  source_type?: string | null;
  time?: string | null;
  priority: string;
  category?: string | null;
  priority_score?: number | null;
  category_score?: number | null;
  summary: string;
  external_id?: string | number | null;
  url?: string | null;
  published_at?: string | null;
  discovered_at?: string | null;
  status: string;
  ai_metadata?: {
    political_relevance?: number | null;
    tags?: string[];
  } | null;
};

type StoryChange = {
  story_id: number;
  thread_id?: number | null;
  has_meaningful_change?: number | boolean | null;
  new_information?: number | null;
  new_actor?: number | null;
  new_measure?: number | null;
  status_change?: number | null;
  date_change?: number | null;
  quantitative_change?: number | null;
  contradiction?: number | null;
  change_summary?: string | null;
  created_at?: string | null;
};

function formatDate(value?: string | null) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function pct(value?: number | null) {
  if (value === null || value === undefined) {
    return "—";
  }

  return `${Math.round(value * 100)}%`;
}

export default function StoryDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();

  const storyId = Number(params.id);
  const profileParam = searchParams.get("profile");
  const profileId = profileParam ? Number(profileParam) : null;

  const [story, setStory] = useState<Story | null>(null);
  const [change, setChange] = useState<StoryChange | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError("");

        const [storyResponse, changeResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/stories/${storyId}`, {
            cache: "no-store",
          }),
          fetch(`${API_BASE_URL}/stories/${storyId}/changes`, {
            cache: "no-store",
          }),
        ]);

        if (!storyResponse.ok) {
          throw new Error("Story não encontrada.");
        }

        const storyData = await storyResponse.json();

        if (storyData?.success === false) {
          throw new Error(storyData.error ?? "Story não encontrada.");
        }

        setStory(storyData);

        if (changeResponse.ok) {
          const changeData = await changeResponse.json();

          if (changeData?.success !== false && !changeData?.error) {
            setChange(changeData);
          }
        }
      } catch (err) {
        console.error(err);
        setError(
          err instanceof Error ? err.message : "Erro inesperado."
        );
      } finally {
        setLoading(false);
      }
    }

    if (Number.isFinite(storyId)) {
      load();
    }
  }, [storyId]);

  if (loading) {
    return (
      <main className="p-6 md:p-8">
        <div className="mx-auto max-w-5xl">
          <div className="rounded-xl border border-gray-200 bg-white p-6 text-sm text-gray-500 shadow-sm">
            Carregando story...
          </div>
        </div>
      </main>
    );
  }

  if (error || !story) {
    return (
      <main className="p-6 md:p-8">
        <div className="mx-auto max-w-5xl">
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
            {error || "Story não encontrada."}
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="p-6 md:p-8">
      <div className="mx-auto max-w-5xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Link
            href="/"
            className="text-sm font-medium text-blue-700 hover:underline"
          >
            ← Voltar para dashboard
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

        <article className="mt-5 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap gap-2">
            {story.category && (
              <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
                {story.category}
              </span>
            )}

            <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700">
              {story.priority}
            </span>

            <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">
              {story.status}
            </span>
          </div>

          <h1 className="mt-5 text-3xl font-bold tracking-tight text-gray-900">
            {story.title}
          </h1>

          <div className="mt-3 text-sm text-gray-500">
            {story.source} · {formatDate(story.published_at ?? story.discovered_at)}
          </div>

          <p className="mt-6 whitespace-pre-wrap text-base leading-7 text-gray-700">
            {story.summary}
          </p>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg bg-gray-50 p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                Prioridade
              </div>
              <div className="mt-1 text-lg font-semibold text-gray-900">
                {pct(story.priority_score)}
              </div>
            </div>

            <div className="rounded-lg bg-gray-50 p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                Categoria
              </div>
              <div className="mt-1 text-lg font-semibold text-gray-900">
                {pct(story.category_score)}
              </div>
            </div>

            <div className="rounded-lg bg-gray-50 p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                Relevância política
              </div>
              <div className="mt-1 text-lg font-semibold text-gray-900">
                {pct(story.ai_metadata?.political_relevance)}
              </div>
            </div>
          </div>
        </article>

        <div className="mt-6">
          <StoryContextLinks
            storyId={story.id}
            profileId={profileId}
            variant="card"
          />
        </div>

        {change && (
          <section className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-5 shadow-sm">
            <div className="text-xs font-semibold uppercase tracking-wide text-amber-700">
              O que mudou
            </div>

            <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-amber-950">
              {change.change_summary ||
                "Há uma análise de mudança registrada para esta story."}
            </p>

            <div className="mt-4 flex flex-wrap gap-2 text-xs">
              {change.new_information !== null &&
                change.new_information !== undefined && (
                  <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">
                    Nova informação {pct(change.new_information)}
                  </span>
                )}

              {change.new_measure !== null &&
                change.new_measure !== undefined && (
                  <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">
                    Nova medida {pct(change.new_measure)}
                  </span>
                )}

              {change.status_change !== null &&
                change.status_change !== undefined && (
                  <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">
                    Mudança de status {pct(change.status_change)}
                  </span>
                )}

              {change.contradiction !== null &&
                change.contradiction !== undefined && (
                  <span className="rounded-full bg-white px-2.5 py-1 text-gray-700">
                    Contradição {pct(change.contradiction)}
                  </span>
                )}
            </div>
          </section>
        )}

        {story.ai_metadata?.tags && story.ai_metadata.tags.length > 0 && (
          <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="text-sm font-semibold text-gray-900">
              Tags
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {story.ai_metadata.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600"
                >
                  {tag}
                </span>
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
