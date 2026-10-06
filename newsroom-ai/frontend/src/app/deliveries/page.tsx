"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

type DeliveryStatus =
  | "pending"
  | "sending"
  | "sent"
  | "failed";

type Delivery = {
  id: number;
  alert_id: number;

  channel: string;
  destination: string | null;

  status: DeliveryStatus;

  attempt_count: number;
  max_attempts: number;

  next_attempt_at: string | null;
  last_attempt_at: string | null;

  external_id: string | null;
  last_error: string | null;

  created_at: string;
  updated_at: string;
  sent_at: string | null;

  alert_title: string;
  alert_type: string;
};

type DeliveriesResponse = {
  count: number;
  status: string | null;
  results: Delivery[];
};

type DeliveryStats = {
  pending: number;
  sending: number;
  sent: number;
  failed: number;
  retrying: number;
  permanently_failed: number;
  total: number;
};

type FilterStatus =
  | "all"
  | DeliveryStatus;

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function formatDate(
  value: string | null
) {
  if (!value) {
    return "—";
  }

  const date =
    new Date(value);

  if (
    Number.isNaN(
      date.getTime()
    )
  ) {
    return value;
  }

  return new Intl.DateTimeFormat(
    "pt-BR",
    {
      dateStyle: "short",
      timeStyle: "short",
    }
  ).format(date);
}

function getStatusLabel(
  status: DeliveryStatus
) {
  switch (status) {
    case "pending":
      return "Pendente";

    case "sending":
      return "Enviando";

    case "sent":
      return "Enviado";

    case "failed":
      return "Falhou";

    default:
      return status;
  }
}

function getStatusClasses(
  status: DeliveryStatus
) {
  switch (status) {
    case "pending":
      return (
        "border-amber-200 " +
        "bg-amber-50 " +
        "text-amber-800"
      );

    case "sending":
      return (
        "border-blue-200 " +
        "bg-blue-50 " +
        "text-blue-800"
      );

    case "sent":
      return (
        "border-emerald-200 " +
        "bg-emerald-50 " +
        "text-emerald-800"
      );

    case "failed":
      return (
        "border-red-200 " +
        "bg-red-50 " +
        "text-red-700"
      );

    default:
      return (
        "border-slate-200 " +
        "bg-slate-50 " +
        "text-slate-700"
      );
  }
}

export default function DeliveriesPage() {
  const [
    deliveries,
    setDeliveries,
  ] = useState<Delivery[]>([]);

  const [
    stats,
    setStats,
  ] = useState<DeliveryStats>({
    pending: 0,
    sending: 0,
    sent: 0,
    failed: 0,
    retrying: 0,
    permanently_failed: 0,
    total: 0,
  });

  const [
    filter,
    setFilter,
  ] = useState<FilterStatus>(
    "all"
  );

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    statsLoading,
    setStatsLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState<string | null>(
    null
  );

  const [
    retryingId,
    setRetryingId,
  ] = useState<number | null>(
    null
  );

  async function loadDeliveries(
    selectedFilter:
      FilterStatus = filter
  ) {
    try {
      setLoading(true);
      setError(null);

      const query =
        selectedFilter === "all"
          ? ""
          : (
              "?status=" +
              encodeURIComponent(
                selectedFilter
              )
            );

      const response =
        await fetch(
          `${API_BASE_URL}/deliveries${query}`,
          {
            cache: "no-store",
          }
        );

      if (!response.ok) {
        throw new Error(
          "Erro ao carregar " +
          `deliveries: ${response.status}`
        );
      }

      const data:
        DeliveriesResponse =
          await response.json();

      setDeliveries(
        data.results ?? []
      );
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : (
              "Erro inesperado " +
              "ao carregar deliveries."
            )
      );
    } finally {
      setLoading(false);
    }
  }

  async function loadStats() {
    try {
      setStatsLoading(true);

      const response =
        await fetch(
          `${API_BASE_URL}/deliveries/stats`,
          {
            cache: "no-store",
          }
        );

      if (!response.ok) {
        throw new Error(
          "Erro ao carregar " +
          `estatísticas: ${response.status}`
        );
      }

      const data:
        DeliveryStats =
          await response.json();

      setStats(data);
    } catch (err) {
      console.error(
        "[DELIVERY STATS ERROR]",
        err
      );
    } finally {
      setStatsLoading(false);
    }
  }

  async function refreshAll(
    selectedFilter:
      FilterStatus = filter
  ) {
    await Promise.all([
      loadDeliveries(
        selectedFilter
      ),
      loadStats(),
    ]);
  }

  useEffect(() => {
    refreshAll(filter);

    const interval =
      setInterval(
        () => {
          refreshAll(filter);
        },
        30000
      );

    return () => {
      clearInterval(
        interval
      );
    };

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  async function retryDelivery(
    deliveryId: number
  ) {
    try {
      setRetryingId(
        deliveryId
      );

      setError(null);

      const response =
        await fetch(
          `${API_BASE_URL}/deliveries/${deliveryId}/retry`,
          {
            method: "POST",
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
          data.reason ||
          "Erro ao tentar novamente."
        );
      }

      if (!data.success) {
        throw new Error(
          data.reason ||
          "Retry não executado."
        );
      }

      await refreshAll(
        filter
      );
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : (
              "Erro inesperado " +
              "ao executar retry."
            )
      );
    } finally {
      setRetryingId(
        null
      );
    }
  }

  const filters = useMemo(
    () => [
      {
        key: "all" as const,
        label: "Todas",
        count: stats.total,
      },

      {
        key: "pending" as const,
        label: "Pendentes",
        count: stats.pending,
      },

      {
        key: "sending" as const,
        label: "Enviando",
        count: stats.sending,
      },

      {
        key: "sent" as const,
        label: "Enviadas",
        count: stats.sent,
      },

      {
        key: "failed" as const,
        label: "Falhas",
        count: stats.failed,
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
            <div className="text-sm font-medium uppercase tracking-wider text-slate-500">
              Newsroom AI
            </div>

            <h1 className="mt-2 text-3xl font-bold text-slate-950">
              Delivery Monitor
            </h1>

            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Acompanhe os envios,
              retries e falhas dos
              alertas da newsroom.
            </p>
          </div>

          <button
            type="button"
            onClick={() =>
              refreshAll(filter)
            }
            disabled={loading}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-50"
          >
            Atualizar
          </button>

        </div>

        {/* STATS */}

        <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">

          <StatCard
            label="Pendentes"
            value={stats.pending}
            loading={statsLoading}
          />

          <StatCard
            label="Enviando"
            value={stats.sending}
            loading={statsLoading}
          />

          <StatCard
            label="Enviadas"
            value={stats.sent}
            loading={statsLoading}
          />

          <StatCard
            label="Falhas"
            value={stats.failed}
            loading={statsLoading}
          />

          <StatCard
            label="Em retry"
            value={stats.retrying}
            loading={statsLoading}
          />

          <StatCard
            label="Falha definitiva"
            value={
              stats.permanently_failed
            }
            loading={statsLoading}
          />

        </div>

        {/* FILTERS */}

        <div className="mb-6 overflow-x-auto">
          <div className="inline-flex min-w-max rounded-xl border border-slate-200 bg-white p-1 shadow-sm">

            {filters.map(
              (item) => {
                const active =
                  filter ===
                  item.key;

                return (
                  <button
                    key={
                      item.key
                    }
                    type="button"
                    onClick={() =>
                      setFilter(
                        item.key
                      )
                    }
                    className={[
                      "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition",

                      active
                        ? "bg-slate-900 text-white"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
                    ].join(" ")}
                  >
                    <span>
                      {item.label}
                    </span>

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
              }
            )}

          </div>
        </div>

        {/* ERROR */}

        {error && (
          <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* LIST */}

        {loading ? (
          <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500 shadow-sm">
            Carregando deliveries...
          </div>
        ) : deliveries.length === 0 ? (
          <div className="rounded-xl border border-slate-200 bg-white p-10 text-center shadow-sm">
            <div className="text-lg font-semibold text-slate-900">
              Nenhuma delivery encontrada
            </div>

            <p className="mt-2 text-sm text-slate-500">
              Não existem registros
              com o filtro selecionado.
            </p>
          </div>
        ) : (
          <div className="space-y-4">

            {deliveries.map(
              (delivery) => (
                <DeliveryCard
                  key={
                    delivery.id
                  }
                  delivery={
                    delivery
                  }
                  retrying={
                    retryingId ===
                    delivery.id
                  }
                  onRetry={
                    retryDelivery
                  }
                />
              )
            )}

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

      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </div>

      <div className="mt-2 text-3xl font-semibold text-slate-950">
        {loading
          ? "—"
          : value}
      </div>

    </div>
  );
}

function DeliveryCard({
  delivery,
  retrying,
  onRetry,
}: {
  delivery: Delivery;
  retrying: boolean;
  onRetry: (
    deliveryId: number
  ) => Promise<void>;
}) {
  const canRetry =
    delivery.status === "failed";

  const hasAutomaticRetry =
    delivery.status === "failed" &&
    delivery.attempt_count <
      delivery.max_attempts &&
    delivery.next_attempt_at !==
      null;

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">

      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">

        <div className="min-w-0 flex-1">

          {/* BADGES */}

          <div className="mb-3 flex flex-wrap items-center gap-2">

            <span
              className={[
                "rounded-full border px-2.5 py-1 text-xs font-semibold",

                getStatusClasses(
                  delivery.status
                ),
              ].join(" ")}
            >
              {getStatusLabel(
                delivery.status
              )}
            </span>

            <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-600">
              {delivery.channel}
            </span>

            {hasAutomaticRetry && (
              <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs text-amber-700">
                Retry agendado
              </span>
            )}

          </div>

          {/* TITLE */}

          <Link
            href={`/alerts`}
            className="text-lg font-semibold text-slate-950 transition hover:text-blue-700"
          >
            {delivery.alert_title}
          </Link>

          <div className="mt-2 text-sm text-slate-500">
            Alert #{delivery.alert_id}
            {" · "}
            Delivery #{delivery.id}
          </div>

          {/* DETAILS */}

          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">

            <InfoCard
              label="Destino"
              value={
                delivery.destination ||
                "—"
              }
              mono
            />

            <InfoCard
              label="Tentativas"
              value={
                `${delivery.attempt_count} / ${delivery.max_attempts}`
              }
            />

            <InfoCard
              label="Última tentativa"
              value={
                formatDate(
                  delivery.last_attempt_at
                )
              }
            />

            <InfoCard
              label="Próxima tentativa"
              value={
                formatDate(
                  delivery.next_attempt_at
                )
              }
            />

          </div>

          {/* FAILURE */}

          {delivery.last_error && (
            <div className="mt-5 rounded-lg border border-red-100 bg-red-50 p-4">

              <div className="text-xs font-semibold uppercase tracking-wide text-red-600">
                Último erro
              </div>

              <div className="mt-2 break-words font-mono text-xs leading-5 text-red-700">
                {delivery.last_error}
              </div>

            </div>
          )}

          {/* SENT INFO */}

          {delivery.status ===
            "sent" && (
            <div className="mt-5 rounded-lg bg-emerald-50 p-4 text-sm text-emerald-800">

              Enviado em{" "}
              {formatDate(
                delivery.sent_at
              )}

              {delivery.external_id && (
                <>
                  {" · ID externo: "}
                  <span className="font-mono">
                    {
                      delivery.external_id
                    }
                  </span>
                </>
              )}

            </div>
          )}

        </div>

        {/* ACTIONS */}

        <div className="shrink-0">

          {canRetry ? (
            <button
              type="button"
              disabled={retrying}
              onClick={() =>
                onRetry(
                  delivery.id
                )
              }
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {retrying
                ? "Preparando..."
                : "Retry"}
            </button>
          ) : (
            <div className="text-xs text-slate-400">
              {delivery.status ===
              "sent"
                ? "Concluído"
                : "Processamento automático"}
            </div>
          )}

        </div>

      </div>

      {/* FOOTER */}

      <div className="mt-5 border-t border-slate-100 pt-4 text-xs text-slate-400">

        Criado em{" "}
        {formatDate(
          delivery.created_at
        )}

        {" · "}

        Atualizado em{" "}
        {formatDate(
          delivery.updated_at
        )}

      </div>

    </article>
  );
}

function InfoCard({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">

      <div className="text-xs font-medium text-slate-500">
        {label}
      </div>

      <div
        className={[
          "mt-1 break-words text-sm font-medium text-slate-900",

          mono
            ? "font-mono"
            : "",
        ].join(" ")}
      >
        {value}
      </div>

    </div>
  );
}