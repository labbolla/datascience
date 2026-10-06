"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type ThreadInfo = {
  id: number;
  title: string;
  summary?: string | null;
  category?: string | null;
};

type Props = {
  storyId: number;
  profileId?: number | null;
  variant?: "compact" | "card";
};

export default function StoryContextLinks({
  storyId,
  profileId = null,
  variant = "compact",
}: Props) {
  const [thread, setThread] = useState<ThreadInfo | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadThread() {
      try {
        const response = await fetch(
          `${API_BASE_URL}/stories/${storyId}/thread`,
          { cache: "no-store" }
        );

        if (!response.ok) {
          return;
        }

        const data = await response.json();

        if (!cancelled) {
          setThread(data.thread ?? null);
        }
      } catch (error) {
        console.error(
          `Erro ao carregar thread da story ${storyId}`,
          error
        );
      } finally {
        if (!cancelled) {
          setLoaded(true);
        }
      }
    }

    loadThread();

    return () => {
      cancelled = true;
    };
  }, [storyId]);

  if (!loaded || !thread) {
    return null;
  }

  const href = `/acompanhamentos/${thread.id}${
    profileId ? `?profile=${profileId}` : ""
  }`;

  if (variant === "card") {
    return (
      <div className="rounded-xl border border-blue-200 bg-blue-50/60 p-5">
        <div className="text-xs font-semibold uppercase tracking-wide text-blue-700">
          Esta story faz parte de um acompanhamento
        </div>

        <h2 className="mt-2 text-lg font-semibold text-gray-900">
          {thread.title}
        </h2>

        {thread.summary && (
          <p className="mt-2 text-sm leading-6 text-gray-600">
            {thread.summary}
          </p>
        )}

        <div className="mt-4 flex flex-wrap gap-3">
          <Link
            href={href}
            className="inline-flex rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800"
          >
            Ver evolução completa →
          </Link>

          <Link
            href={`/threads/${thread.id}`}
            className="inline-flex rounded-lg border border-blue-200 bg-white px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50"
          >
            Ver thread técnico
          </Link>
        </div>
      </div>
    );
  }

  return (
    <Link
      href={href}
      className="text-sm font-semibold text-blue-700 hover:underline"
    >
      Ver evolução completa →
    </Link>
  );
}
