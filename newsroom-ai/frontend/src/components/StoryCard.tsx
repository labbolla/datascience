"use client";

import Link from "next/link";
import { useState } from "react";

type Story = {
  id: number;
  title: string;
  source: string;
  time: string;
  priority: string;
  category?: string | null;
  priority_score?: number | null;
  category_score?: number | null;
  summary: string;
  url?: string | null;
  published_at?: string | null;
  discovered_at?: string | null;
  status: string;
  ai_metadata?: {
    political_relevance?: number | null;
    tags?: string[];
  } | null;
};

type StoryCardProps = {
  story: Story;
  onStatusChanged?: (storyId: number) => void;
};

function formatDate(value?: string | null) {
  if (!value) return "-";

  const date = new Date(value);

  return date.toLocaleString("pt-BR");
}

function formatScore(value?: number | null) {
  if (value === null || value === undefined) {
    return "-";
  }

  return value.toFixed(2);
}

export default function StoryCard({
  story,
  onStatusChanged,
}: StoryCardProps) {
  const [loading, setLoading] = useState(false);

  async function updateStatus(status: string) {
    setLoading(true);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/stories/${story.id}/status`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            status,
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Erro ao atualizar status");
      }

      const data = await response.json();

      if (data.success && onStatusChanged) {
        onStatusChanged(story.id);
      }
    } catch (error) {
      console.error(error);
      alert("Não foi possível atualizar a story.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            {story.title}
          </h2>

          <p className="mt-1 text-sm text-gray-500">
            {story.source}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <span className="rounded-full bg-gray-200 px-3 py-1 text-sm font-medium text-gray-800">
            {story.priority}
          </span>

          {story.category && (
            <span className="rounded-full border border-gray-300 px-3 py-1 text-sm text-gray-700">
              {story.category}
            </span>
          )}
        </div>
      </div>

      <p className="mt-4 text-gray-700">
        {story.summary}
      </p>

      <div className="mt-5 grid gap-3 text-sm text-gray-600 md:grid-cols-2">
        <div>
          <span className="font-medium text-gray-800">
            Prioridade:
          </span>{" "}
          {formatScore(story.priority_score)}
        </div>

        <div>
          <span className="font-medium text-gray-800">
            Categoria:
          </span>{" "}
          {formatScore(story.category_score)}
        </div>

        <div>
          <span className="font-medium text-gray-800">
            Publicado:
          </span>{" "}
          {formatDate(story.published_at)}
        </div>

        <div>
          <span className="font-medium text-gray-800">
            Descoberto:
          </span>{" "}
          {formatDate(story.discovered_at)}
        </div>

        {story.ai_metadata?.political_relevance !== undefined && (
          <div>
            <span className="font-medium text-gray-800">
              Relevância política:
            </span>{" "}
            {formatScore(
              story.ai_metadata.political_relevance
            )}
          </div>
        )}
      </div>

      {story.ai_metadata?.tags &&
        story.ai_metadata.tags.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {story.ai_metadata.tags.map((tag) => (
              <span
                key={tag}
                className="rounded-md bg-gray-100 px-2 py-1 text-xs text-gray-600"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

      <div className="mt-6 flex flex-wrap gap-2">
        <button
          disabled={loading}
          onClick={() => updateStatus("reviewed")}
          className="rounded-lg bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Revisada
        </button>

        <button
          disabled={loading}
          onClick={() => updateStatus("important")}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-800 disabled:opacity-50"
        >
          Importante
        </button>

        <button
          disabled={loading}
          onClick={() => updateStatus("ignored")}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-500 disabled:opacity-50"
        >
          Ignorar
        </button>

        <Link
          href={`/stories/${story.id}`}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-800"
        >
          Detalhes
        </Link>

        {story.url && (
          <a
            href={story.url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-800"
          >
            Fonte
          </a>
        )}
      </div>
    </div>
  );
}