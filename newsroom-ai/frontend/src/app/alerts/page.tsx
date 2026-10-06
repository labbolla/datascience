"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

type AlertStatus =
  | "pending"
  | "acknowledged"
  | "dismissed"
  | "delivered";

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

  status: AlertStatus;

  metadata: {
    rule_version?: string;
    thresholds?: Record<string, unknown>;
    signals?: {
      priority_score?: number;
      meaningful_change?: number;
      new_information?: number;
      new_actor?: number;
      new_measure?: number;
      status_change?: number;
      date_change?: number;
      quantitative_change?: number;
      contradiction?: number;
    };
    category?: string;
    priority?: string;
  } | null;

  created_at: string;
  delivered_at: string | null;
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

type FilterStatus = "all" | AlertStatus;

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function formatDate(value: string | null) {
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

function formatScore(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "—";
  }

  return value.toFixed(2);
}

function getStatusLabel(status: AlertStatus) {
  switch (status) {
    case "pending":
      return "Pendente";

    case "acknowledged":
      return "Reconhecido";

    case "dismissed":
      return "Descartado";

    case "delivered":
      return "Entregue";

    default:
      return status;
  }
}

function getAlertTypeLabel(alertType: string) {
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

function getStatusClasses(status: AlertStatus) {
  switch (status) {
    case "pending":
      return "border-amber-200 bg-amber-50 text-amber-800";

    case "acknowledged":
      return "border-blue-200 bg-blue-50 text-blue-800";

    case "dismissed":
      return "border-slate-200 bg-slate-100 text-slate-600";

    case "delivered":
      return "border-emerald-200 bg-emerald-50 text-emerald-800";

    default:
      return "border-slate-200 bg-slate-100 text-slate-700";
  }
}

function getAlertTypeClasses(alertType: string) {
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
      return "border-slate-200 bg-slate-50 text-slate-700";
  }
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [stats, setStats] = useState<AlertStats>({
    pending: 0,
    acknowledged: 0,
    dismissed: 0,
    delivered: 0,
    total: 0,
  });

  const [filter, setFilter] = useState<FilterStatus>("pending");

  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);

  const [error, setError] = useState<string | null>(null);

  const [updatingAlertId, setUpdatingAlertId] =
    useState<number | null>(null);

  async function loadAlerts(
    selectedFilter: FilterStatus = filter
  ) {
    try {
      setLoading(true);
      setError(null);

      const query =
        selectedFilter === "all"
          ? ""
          : `?status=${encodeURIComponent(
              selectedFilter
            )}`;

      const response = await fetch(
        `${API_BASE_URL}/alerts${query}`,
        {
          cache: "no-store",
        }
      );

      if (!response.ok) {
        throw new Error(
          `Erro ao carregar alertas: ${response.status}`
        );
      }

      const data: AlertsResponse =
        await response.json();

      setAlerts(data.results ?? []);
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : "Erro inesperado ao carregar alertas."
      );
    } finally {
      setLoading(false);
    }
  }

  async function loadStats() {
    try {
      setStatsLoading(true);

      const response = await fetch(
        `${API_BASE_URL}/alerts/stats`,
        {
          cache: "no-store",
        }
      );

      if (!response.ok) {
        throw new Error(
          `Erro ao carregar estatísticas: ${response.status}`
        );
      }

      const data: AlertStats =
        await response.json();

      setStats(data);
    } catch (err) {
      console.error(
        "[ALERT STATS ERROR]",
        err
      );
    } finally {
      setStatsLoading(false);
    }
  }

  async function refreshAll(
    selectedFilter: FilterStatus = filter
  ) {
    await Promise.all([
      loadAlerts(selectedFilter),
      loadStats(),
    ]);
  }

  useEffect(() => {
    refreshAll(filter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  async function updateAlertStatus(
    alertId: number,
    newStatus: AlertStatus
  ) {
    try {
      setUpdatingAlertId(alertId);
      setError(null);

      const response = await fetch(
        `${API_BASE_URL}/alerts/${alertId}/status`,
        {
          method: "PATCH",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            status: newStatus,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(
          data.error ||
            `Erro ao atualizar alerta: ${response.status}`
        );
      }

      await refreshAll(filter);
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : "Erro inesperado ao atualizar alerta."
      );
    } finally {
      setUpdatingAlertId(null);
    }
  }

  const filters = useMemo(
    () => [
      {
        key: "all" as const,
        label: "Todos",
        count: stats.total,
      },
      {
        key: "pending" as const,
        label: "Pendentes",
        count: stats.pending,
      },
      {
        key: "acknowledged" as const,
        label: "Reconhecidos",
        count: stats.acknowledged,
      },
      {
        key: "dismissed" as const,
        label: "Descartados",
        count: stats.dismissed,
      },
      {
        key: "delivered" as const,
        label: "Entregues",
        count: stats.delivered,
      },
    ],
    [stats]
  );

  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-7xl px-6 py-8">
        {/* HEADER */}

        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-2 text-sm font-medium uppercase tracking-wider text-slate-500">
              Newsroom AI
            </div>

            <h1 className="text-3xl font-bold text-slate-950">
              Alertas
            </h1>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              Caixa operacional de mudanças relevantes e stories
              que exigem atenção.
            </p>
          </div>

          <button
            type="button"
            onClick={() => refreshAll(filter)}
            disabled={loading}
            className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Atualizar
          </button>
        </div>

        {/* STATS */}

        <div className="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Pendentes"
            value={stats.pending}
            loading={statsLoading}
          />

          <StatCard
            label="Reconhecidos"
            value={stats.acknowledged}
            loading={statsLoading}
          />

          <StatCard
            label="Descartados"
            value={stats.dismissed}
            loading={statsLoading}
          />

          <StatCard
            label="Entregues"
            value={stats.delivered}
            loading={statsLoading}
          />
        </div>

        {/* FILTERS */}

        <div className="mb-6 overflow-x-auto">
          <div className="inline-flex min-w-max rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
            {filters.map((item) => {
              const active =
                filter === item.key;

              return (
                <button
                  key={item.key}
                  type="button"
                  onClick={() =>
                    setFilter(item.key)
                  }
                  className={[
                    "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition",
                    active
                      ? "bg-slate-900 text-white"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
                  ].join(" ")}
                >
                  <span>{item.label}</span>

                  <span
                    className={[
                      "rounded-full px-2 py-0.5 text-xs",
                      active
                        ? "bg-white/15 text-white"
                        : "bg-slate-100 text-slate-600",
                    ].join(" ")}
                  >
                    {item.count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* ERROR */}

        {error && (
          <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* CONTENT */}

        {loading ? (
          <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500 shadow-sm">
            Carregando alertas...
          </div>
        ) : alerts.length === 0 ? (
          <div className="rounded-xl border border-slate-200 bg-white p-10 text-center shadow-sm">
            <div className="text-lg font-semibold text-slate-900">
              Nenhum alerta nesta fila
            </div>

            <p className="mt-2 text-sm text-slate-500">
              Não existem alertas com o filtro selecionado.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {alerts.map((alert) => (
              <AlertCard
                key={alert.id}
                alert={alert}
                updating={
                  updatingAlertId === alert.id
                }
                onStatusChange={
                  updateAlertStatus
                }
              />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

function StatCard({
  label,
  value,
  loading,
}: {
  label: string;
  value: number;
  loading: boolean;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="text-sm font-medium text-slate-500">
        {label}
      </div>

      <div className="mt-2 text-3xl font-semibold text-slate-950">
        {loading ? "—" : value}
      </div>
    </div>
  );
}

function AlertCard({
  alert,
  updating,
  onStatusChange,
}: {
  alert: AlertItem;
  updating: boolean;
  onStatusChange: (
    alertId: number,
    status: AlertStatus
  ) => Promise<void>;
}) {
  const signals =
    alert.metadata?.signals ?? {};

  return (
    <article className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="p-6">
        {/* TOP ROW */}

        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span
                className={[
                  "rounded-full border px-2.5 py-1 text-xs font-semibold",
                  getAlertTypeClasses(
                    alert.alert_type
                  ),
                ].join(" ")}
              >
                {getAlertTypeLabel(
                  alert.alert_type
                )}
              </span>

              <span
                className={[
                  "rounded-full border px-2.5 py-1 text-xs font-medium",
                  getStatusClasses(
                    alert.status
                  ),
                ].join(" ")}
              >
                {getStatusLabel(
                  alert.status
                )}
              </span>

              {alert.metadata?.category && (
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-600">
                  {alert.metadata.category}
                </span>
              )}
            </div>

            <Link
              href={`/stories/${alert.story_id}`}
              className="text-xl font-semibold leading-7 text-slate-950 transition hover:text-blue-700"
            >
              {alert.story_title ||
                alert.title}
            </Link>

            <p className="mt-3 max-w-4xl text-sm leading-6 text-slate-700">
              {alert.message}
            </p>
          </div>

          <div className="shrink-0 text-left text-xs text-slate-500 lg:text-right">
            <div>
              {formatDate(
                alert.created_at
              )}
            </div>

            <div className="mt-1">
              Alert #{alert.id}
            </div>
          </div>
        </div>

        {/* SCORES */}

        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <ScoreCard
            label="Prioridade"
            value={alert.priority_score}
          />

          <ScoreCard
            label="Mudança significativa"
            value={
              alert.meaningful_change_score
            }
          />

          <ScoreCard
            label="Nova informação"
            value={
              signals.new_information
            }
          />

          <ScoreCard
            label="Nova medida"
            value={signals.new_measure}
          />
        </div>

        {/* LINKS */}

        <div className="mt-5 flex flex-wrap gap-x-5 gap-y-2 text-sm">
          <Link
            href={`/stories/${alert.story_id}`}
            className="font-medium text-blue-700 hover:underline"
          >
            Ver story
          </Link>

          {alert.thread_id && (
            <Link
              href={`/threads/${alert.thread_id}`}
              className="font-medium text-blue-700 hover:underline"
            >
              Ver thread
            </Link>
          )}
        </div>

        {/* THREAD */}

        {alert.thread_id &&
          alert.thread_title && (
            <div className="mt-4 rounded-lg bg-slate-50 px-4 py-3">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Thread
              </div>

              <div className="mt-1 text-sm font-medium text-slate-800">
                {alert.thread_title}
              </div>
            </div>
          )}

        {/* ACTIONS */}

        <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-slate-100 pt-5">
          {alert.status !==
            "acknowledged" && (
            <button
              type="button"
              disabled={updating}
              onClick={() =>
                onStatusChange(
                  alert.id,
                  "acknowledged"
                )
              }
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {updating
                ? "Atualizando..."
                : "Reconhecer"}
            </button>
          )}

          {alert.status !==
            "dismissed" && (
            <button
              type="button"
              disabled={updating}
              onClick={() =>
                onStatusChange(
                  alert.id,
                  "dismissed"
                )
              }
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Descartar
            </button>
          )}

          {alert.status !==
            "pending" && (
            <button
              type="button"
              disabled={updating}
              onClick={() =>
                onStatusChange(
                  alert.id,
                  "pending"
                )
              }
              className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm text-slate-500 transition hover:bg-slate-50 hover:text-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Voltar para pendente
            </button>
          )}

          {alert.status ===
            "delivered" &&
            alert.delivered_at && (
              <div className="ml-auto text-xs text-slate-500">
                Entregue em{" "}
                {formatDate(
                  alert.delivered_at
                )}
              </div>
            )}
        </div>
      </div>
    </article>
  );
}

function ScoreCard({
  label,
  value,
}: {
  label: string;
  value:
    | number
    | null
    | undefined;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
      <div className="text-xs font-medium text-slate-500">
        {label}
      </div>

      <div className="mt-1 text-lg font-semibold text-slate-900">
        {formatScore(value)}
      </div>
    </div>
  );
}