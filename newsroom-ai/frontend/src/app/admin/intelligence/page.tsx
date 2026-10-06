"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import StoryCard from "@/components/StoryCard";

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
  external_id?: number | null;
  url?: string | null;
  published_at?: string | null;
  discovered_at?: string | null;
  status: string;
  ai_metadata?: {
    political_relevance?: number | null;
    tags?: string[];
  } | null;
};

type AlertItem = {
  id: number;
  story_id: number;
  story_title: string;
  thread_id: number | null;
  thread_title: string | null;
  alert_type: string;
  title: string;
  message: string;
  priority_score: number | null;
  meaningful_change_score: number | null;
  status: string;
  created_at: string;
};

type AlertsResponse = {
  count: number;
  status: string | null;
  results: AlertItem[];
};

type AlertStats = {
  pending: number;
  acknowledged: number;
  dismissed: number;
  delivered: number;
  total: number;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function formatScore(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "—";
  }

  return value.toFixed(2);
}

function formatDate(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function alertTypeLabel(alertType: string) {
  switch (alertType) {
    case "breaking_change":
      return "Mudança relevante";
    case "high_priority_change":
      return "Alta prioridade + mudança";
    case "high_priority_story":
      return "Alta prioridade";
    case "attention":
      return "Atenção";
    default:
      return alertType;
  }
}

function alertTypeClasses(alertType: string) {
  switch (alertType) {
    case "breaking_change":
      return "border-red-200 bg-red-50 text-red-700";
    case "high_priority_change":
      return "border-purple-200 bg-purple-50 text-purple-700";
    case "high_priority_story":
      return "border-orange-200 bg-orange-50 text-orange-700";
    case "attention":
      return "border-yellow-200 bg-yellow-50 text-yellow-700";
    default:
      return "border-gray-200 bg-gray-50 text-gray-700";
  }
}

export default function Home() {
  const [stories, setStories] = useState<Story[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [alertStats, setAlertStats] = useState<AlertStats>({
    pending: 0,
    acknowledged: 0,
    dismissed: 0,
    delivered: 0,
    total: 0,
  });

  const [loading, setLoading] = useState(true);
  const [alertsLoading, setAlertsLoading] = useState(true);

  const [priorityFilter, setPriorityFilter] =
    useState("Todas");

  const [categoryFilter, setCategoryFilter] =
    useState("Todas");

  async function loadStories() {
    try {
      const response = await fetch(
        `${API_BASE_URL}/stories`,
        {
          cache: "no-store",
        }
      );

      if (!response.ok) {
        throw new Error("Erro ao carregar stories");
      }

      const data = await response.json();

      setStories(
        Array.isArray(data)
          ? data
          : []
      );
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  async function loadAlerts() {
    try {
      setAlertsLoading(true);

      const [alertsResponse, statsResponse] = await Promise.all([
        fetch(
          `${API_BASE_URL}/alerts?status=pending&limit=5`,
          { cache: "no-store" }
        ),
        fetch(
          `${API_BASE_URL}/alerts/stats`,
          { cache: "no-store" }
        ),
      ]);

      if (!alertsResponse.ok) {
        throw new Error("Erro ao carregar alertas pendentes");
      }

      if (!statsResponse.ok) {
        throw new Error("Erro ao carregar estatísticas de alertas");
      }

      const alertsData: AlertsResponse =
        await alertsResponse.json();

      const statsData: AlertStats =
        await statsResponse.json();

      setAlerts(alertsData.results ?? []);
      setAlertStats(statsData);
    } catch (error) {
      console.error(error);
    } finally {
      setAlertsLoading(false);
    }
  }

  async function refreshDashboard() {
    await Promise.all([
      loadStories(),
      loadAlerts(),
    ]);
  }

  useEffect(() => {
    refreshDashboard();

    const interval = setInterval(
      refreshDashboard,
      30000
    );

    return () => clearInterval(interval);
  }, []);

  const categories = useMemo(() => {
    const values = stories
      .map((story) => story.category)
      .filter(
        (value): value is string =>
          Boolean(value)
      );

    return [
      "Todas",
      ...Array.from(new Set(values)).sort(),
    ];
  }, [stories]);

  const filteredStories = useMemo(() => {
    return stories.filter((story) => {
      const priorityMatches =
        priorityFilter === "Todas" ||
        story.priority === priorityFilter;

      const categoryMatches =
        categoryFilter === "Todas" ||
        story.category === categoryFilter;

      return (
        priorityMatches &&
        categoryMatches
      );
    });
  }, [
    stories,
    priorityFilter,
    categoryFilter,
  ]);

  function handleStatusChanged(
    storyId: number
  ) {
    setStories((current) =>
      current.filter(
        (story) =>
          story.id !== storyId
      )
    );
  }

  return (
    <main className="min-h-screen bg-gray-100 p-8">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              What Changed Today
            </h1>

            <p className="mt-2 text-gray-600">
              Alterações relevantes detectadas nas fontes monitoradas.
            </p>
          </div>

          <button
            onClick={refreshDashboard}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-800"
          >
            Atualizar agora
          </button>
        </div>

        {/* REQUER ATENÇÃO */}

        <section className="mt-8 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-semibold text-gray-900">
                  Requer atenção
                </h2>

                <span className="rounded-full bg-red-100 px-2.5 py-1 text-xs font-semibold text-red-700">
                  {alertStats.pending} pendentes
                </span>
              </div>

              <p className="mt-1 text-sm text-gray-500">
                Alertas pendentes mais recentes detectados pela pipeline.
              </p>
            </div>

            <Link
              href="/alerts"
              className="text-sm font-medium text-blue-700 hover:underline"
            >
              Ver todos os alertas →
            </Link>
          </div>

          <div className="mt-5 space-y-3">
            {alertsLoading ? (
              <p className="text-sm text-gray-500">
                Carregando alertas...
              </p>
            ) : alerts.length === 0 ? (
              <div className="rounded-lg bg-gray-50 px-4 py-5 text-sm text-gray-500">
                Nenhum alerta pendente no momento.
              </div>
            ) : (
              alerts.map((alert) => (
                <article
                  key={alert.id}
                  className="rounded-lg border border-gray-200 p-4"
                >
                  <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <span
                          className={[
                            "rounded-full border px-2.5 py-1 text-xs font-semibold",
                            alertTypeClasses(alert.alert_type),
                          ].join(" ")}
                        >
                          {alertTypeLabel(alert.alert_type)}
                        </span>

                        <span className="text-xs text-gray-400">
                          {formatDate(alert.created_at)}
                        </span>
                      </div>

                      <Link
                        href={`/stories/${alert.story_id}`}
                        className="font-semibold text-gray-900 hover:text-blue-700"
                      >
                        {alert.story_title || alert.title}
                      </Link>

                      <p className="mt-2 text-sm leading-6 text-gray-600">
                        {alert.message}
                      </p>

                      <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-500">
                        <span>
                          Prioridade: {formatScore(alert.priority_score)}
                        </span>

                        <span>
                          Mudança: {formatScore(alert.meaningful_change_score)}
                        </span>

                        {alert.thread_id && (
                          <Link
                            href={`/threads/${alert.thread_id}`}
                            className="font-medium text-blue-700 hover:underline"
                          >
                            Ver thread
                          </Link>
                        )}
                      </div>
                    </div>

                    <Link
                      href={`/stories/${alert.story_id}`}
                      className="shrink-0 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                    >
                      Abrir story
                    </Link>
                  </div>
                </article>
              ))
            )}
          </div>
        </section>

        {/* STORY FILTERS */}

        <div className="mt-8 rounded-xl bg-white p-5 shadow-sm">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">
                Prioridade
              </label>

              <select
                value={priorityFilter}
                onChange={(event) =>
                  setPriorityFilter(
                    event.target.value
                  )
                }
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
              >
                <option>Todas</option>
                <option>Alta</option>
                <option>Média</option>
                <option>Baixa</option>
                <option>
                  Não classificada
                </option>
              </select>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">
                Categoria
              </label>

              <select
                value={categoryFilter}
                onChange={(event) =>
                  setCategoryFilter(
                    event.target.value
                  )
                }
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
              >
                {categories.map(
                  (category) => (
                    <option
                      key={category}
                      value={category}
                    >
                      {category}
                    </option>
                  )
                )}
              </select>
            </div>
          </div>

          <div className="mt-4 text-sm text-gray-500">
            {filteredStories.length} stories exibidas
          </div>
        </div>

        {/* STORIES */}

        <div className="mt-8 space-y-4">
          {loading ? (
            <p className="text-gray-500">
              Carregando...
            </p>
          ) : filteredStories.length === 0 ? (
            <p className="text-gray-500">
              Nenhuma story encontrada com esses filtros.
            </p>
          ) : (
            filteredStories.map((story) => (
              <StoryCard
                key={story.id}
                story={story}
                onStatusChanged={
                  handleStatusChanged
                }
              />
            ))
          )}
        </div>
      </div>
    </main>
  );
}
