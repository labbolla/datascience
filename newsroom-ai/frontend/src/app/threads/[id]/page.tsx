"use client";

import Link from "next/link";
import {
  useEffect,
  useMemo,
  useState,
} from "react";
import { useParams } from "next/navigation";


const API_URL =
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
  source?: string | null;
  summary?: string | null;
  url?: string | null;

  category?: string | null;
  priority?: string | null;

  priority_score?: number | null;
  category_score?: number | null;

  published_at?: string | null;
  discovered_at?: string | null;

  status?: string | null;

  has_meaningful_change?: number | null;
  new_information?: number | null;
  new_actor?: number | null;
  new_measure?: number | null;
  status_change?: number | null;
  date_change?: number | null;
  quantitative_change?: number | null;
  contradiction?: number | null;

  change_summary?: string | null;

  change_ai_metadata?: {
    provider?: string;
    model?: string;
    compared_story_ids?: number[];
  } | null;

  generator_metadata?: {
    provider?: string;
    model?: string;

    usage?: {
      input_tokens?: number;
      output_tokens?: number;
      total_tokens?: number;
    };
  } | null;

  change_created_at?: string | null;
};


type ThreadResponse = {
  thread: ThreadInfo;
  stories: ThreadStory[];
  story_count: number;
};


function formatDate(
  value?: string | null
) {
  if (!value) {
    return "—";
  }

  try {
    return new Intl.DateTimeFormat(
      "pt-BR",
      {
        dateStyle: "medium",
        timeStyle: "short",
      }
    ).format(
      new Date(value)
    );
  } catch {
    return value;
  }
}


function formatScore(
  value?: number | null
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  return value.toFixed(2);
}


function getChangeLevel(
  value?: number | null
) {
  if (
    value === null ||
    value === undefined
  ) {
    return {
      label: "Sem análise",
      className:
        "bg-slate-100 text-slate-600",
    };
  }

  if (value >= 0.7) {
    return {
      label: "Alto",
      className:
        "bg-rose-50 text-rose-700",
    };
  }

  if (value >= 0.45) {
    return {
      label: "Médio",
      className:
        "bg-amber-50 text-amber-700",
    };
  }

  return {
    label: "Baixo",
    className:
      "bg-emerald-50 text-emerald-700",
  };
}


function TimelineStory({
  story,
  index,
}: {
  story: ThreadStory;
  index: number;
}) {
  const changeLevel =
    getChangeLevel(
      story.has_meaningful_change
    );

  const effectiveDate =
    story.published_at ||
    story.discovered_at;

  return (
    <div className="relative">

      {/* TIMELINE LINE */}
      <div className="absolute bottom-0 left-[19px] top-10 w-px bg-slate-200" />

      <div className="flex gap-5">

        {/* TIMELINE MARKER */}
        <div className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-slate-300 bg-white text-sm font-semibold text-slate-600 shadow-sm">
          {index + 1}
        </div>


        <div className="min-w-0 flex-1 pb-10">

          {/* STORY CARD */}
          <div className="rounded-xl border bg-white p-6 shadow-sm">

            <div className="flex flex-wrap items-start justify-between gap-4">

              <div className="min-w-0">

                <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                  {story.source || "Fonte"}
                </p>

                <Link
                  href={`/stories/${story.id}`}
                  className="mt-1 block text-xl font-semibold text-slate-900 hover:text-blue-700"
                >
                  {story.title}
                </Link>

                <p className="mt-2 text-sm text-slate-500">
                  {formatDate(
                    effectiveDate
                  )}
                </p>

              </div>


              <div className="flex flex-wrap gap-2">

                {story.category && (
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                    {story.category}
                  </span>
                )}

                {story.priority && (
                  <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
                    {story.priority}
                  </span>
                )}

              </div>

            </div>


            {story.summary && (
              <p className="mt-5 whitespace-pre-line text-sm leading-6 text-slate-700">
                {story.summary}
              </p>
            )}


            <div className="mt-5 flex flex-wrap gap-3">

              <Link
                href={`/stories/${story.id}`}
                className="rounded-lg border px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Detalhes
              </Link>

              {story.url && (
                <a
                  href={story.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-lg border px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Fonte original
                </a>
              )}

            </div>

          </div>


          {/* WHAT CHANGED */}
          {index === 0 ? (

            <div className="mt-4 rounded-xl border border-dashed bg-slate-50 p-5">

              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Início do thread
              </p>

              <p className="mt-2 text-sm text-slate-600">
                Esta é a primeira story conhecida deste thread.
                Ainda não existe histórico anterior para comparação.
              </p>

            </div>

          ) : story.change_summary ? (

            <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50/40 p-5">

              <div className="flex flex-wrap items-center justify-between gap-3">

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">
                    What Changed?
                  </p>
                </div>


                <div className="flex items-center gap-2">

                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold ${changeLevel.className}`}
                  >
                    Mudança{" "}
                    {changeLevel.label}
                  </span>

                  <span className="font-mono text-xs text-slate-500">
                    {formatScore(
                      story.has_meaningful_change
                    )}
                  </span>

                </div>

              </div>


              <p className="mt-3 text-sm leading-6 text-slate-800">
                {story.change_summary}
              </p>


              <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-500">

                {story.new_information !==
                  null &&
                  story.new_information !==
                    undefined && (
                    <span>
                      Nova informação{" "}
                      <strong className="font-mono font-medium text-slate-700">
                        {formatScore(
                          story.new_information
                        )}
                      </strong>
                    </span>
                  )}


                {story.new_actor !==
                  null &&
                  story.new_actor !==
                    undefined && (
                    <span>
                      Novo ator{" "}
                      <strong className="font-mono font-medium text-slate-700">
                        {formatScore(
                          story.new_actor
                        )}
                      </strong>
                    </span>
                  )}


                {story.new_measure !==
                  null &&
                  story.new_measure !==
                    undefined && (
                    <span>
                      Nova medida{" "}
                      <strong className="font-mono font-medium text-slate-700">
                        {formatScore(
                          story.new_measure
                        )}
                      </strong>
                    </span>
                  )}

              </div>

            </div>

          ) : (

            <div className="mt-4 rounded-xl border border-dashed bg-slate-50 p-5">

              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                What Changed?
              </p>

              <p className="mt-2 text-sm text-slate-600">
                Ainda não existe análise de mudança disponível para esta story.
              </p>

            </div>

          )}

        </div>

      </div>

    </div>
  );
}


export default function ThreadDetailPage() {

  const params = useParams();

  const threadId =
    Array.isArray(params.id)
      ? params.id[0]
      : params.id;


  const [
    data,
    setData,
  ] = useState<ThreadResponse | null>(
    null
  );

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState<string | null>(
    null
  );


  useEffect(() => {

    if (!threadId) {
      return;
    }

    async function loadThread() {

      try {

        setLoading(true);
        setError(null);

        const response = await fetch(
          `${API_URL}/threads/${threadId}`,
          {
            cache: "no-store",
          }
        );

        if (!response.ok) {
          throw new Error(
            `Erro ${response.status}`
          );
        }

        const json =
          await response.json();

        setData(json);

      } catch (err) {

        console.error(err);

        setError(
          "Não foi possível carregar o thread."
        );

      } finally {

        setLoading(false);

      }
    }

    loadThread();

  }, [threadId]);


  const latestStory =
    useMemo(() => {

      if (
        !data ||
        data.stories.length === 0
      ) {
        return null;
      }

      return data.stories[
        data.stories.length - 1
      ];

    }, [data]);


  if (loading) {
    return (
      <main className="mx-auto max-w-5xl p-6">
        <p className="text-slate-500">
          Carregando thread...
        </p>
      </main>
    );
  }


  if (error || !data) {
    return (
      <main className="mx-auto max-w-5xl p-6">

        <div className="rounded-xl border bg-white p-6">

          <p className="text-red-600">
            {error ||
              "Thread não encontrado."}
          </p>

          <Link
            href="/"
            className="mt-4 inline-block text-sm font-medium text-blue-700"
          >
            Voltar
          </Link>

        </div>

      </main>
    );
  }


  return (
    <main className="mx-auto max-w-5xl p-6">

      {/* HEADER */}

      <div className="mb-8">

        <Link
          href="/"
          className="text-sm font-medium text-slate-500 hover:text-slate-800"
        >
          ← Dashboard
        </Link>


        <div className="mt-5">

          <div className="flex flex-wrap items-center gap-2">

            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
              Thread #{data.thread.id}
            </span>

            {data.thread.category && (
              <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
                {data.thread.category}
              </span>
            )}

          </div>


          <h1 className="mt-4 text-3xl font-bold tracking-tight text-slate-900">
            {data.thread.title}
          </h1>


          {data.thread.summary && (
            <p className="mt-3 max-w-3xl text-base leading-7 text-slate-600">
              {data.thread.summary}
            </p>
          )}


          <div className="mt-5 flex flex-wrap gap-6 text-sm text-slate-500">

            <span>
              {data.story_count}{" "}
              {data.story_count === 1
                ? "story"
                : "stories"}
            </span>

            {latestStory && (
              <span>
                Última atualização:{" "}
                {formatDate(
                  latestStory.published_at ||
                    latestStory.discovered_at
                )}
              </span>
            )}

          </div>

        </div>

      </div>


      {/* TIMELINE */}

      <section>

        <div className="mb-5">

          <h2 className="text-lg font-semibold text-slate-900">
            Linha do tempo
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Evolução cronológica das stories associadas a este thread.
          </p>

        </div>


        {data.stories.length === 0 ? (

          <div className="rounded-xl border bg-white p-6 text-sm text-slate-600">
            Nenhuma story associada a este thread.
          </div>

        ) : (

          <div>
            {data.stories.map(
              (
                story,
                index
              ) => (
                <TimelineStory
                  key={story.id}
                  story={story}
                  index={index}
                />
              )
            )}
          </div>

        )}

      </section>

    </main>
  );
}