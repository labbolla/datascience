"use client";

import { useEffect, useState } from "react";

type SchedulerJob = {
  id: string;
  next_run_time: string | null;
};

type OperationsHealth = {
  status: "healthy" | "degraded";
  checked_at: string;
  problems: string[];

  scheduler: {
    running: boolean;
    jobs: SchedulerJob[];
  };

  camara: {
    last_story_discovered_at: string | null;
    stories_last_24h: number;
  };

  deliveries: {
    pending: number;
    sending: number;
    failed: number;
    retrying: number;
    permanently_failed: number;
    sent_last_24h: number;
    last_sent_at: string | null;
  };

  notification_channels: {
    enabled: number;
    disabled: number;
  };
};

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
    timeStyle: "medium",
  }).format(date);
}

function getProblemLabel(problem: string) {
  switch (problem) {
    case "scheduler_not_running":
      return "Scheduler não está em execução";

    case "no_notification_channels_enabled":
      return "Nenhum canal de notificação ativo";

    case "permanent_delivery_failures":
      return "Existem deliveries com falha definitiva";

    case "deliveries_currently_sending":
      return "Existem deliveries em processamento";

    default:
      return problem;
  }
}

export default function OperationsPage() {
  const [health, setHealth] =
    useState<OperationsHealth | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  async function loadHealth() {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `${API_BASE_URL}/health/operations`,
        {
          cache: "no-store",
        }
      );

      if (!response.ok) {
        throw new Error(
          `Erro ao carregar health: ${response.status}`
        );
      }

      const data: OperationsHealth =
        await response.json();

      setHealth(data);
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : "Erro inesperado ao carregar status."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadHealth();

    const interval = setInterval(
      loadHealth,
      30000
    );

    return () => {
      clearInterval(interval);
    };
  }, []);

  if (loading && !health) {
    return (
      <main className="min-h-screen bg-slate-50">
        <div className="mx-auto max-w-6xl px-6 py-8">
          <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
            Carregando status operacional...
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-6xl px-6 py-8">

        {/* HEADER */}

        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="text-sm font-medium uppercase tracking-wider text-slate-500">
              Newsroom AI
            </div>

            <h1 className="mt-2 text-3xl font-bold text-slate-950">
              Operations
            </h1>

            <p className="mt-2 text-sm text-slate-600">
              Estado operacional da ingestão,
              alertas e canais de entrega.
            </p>
          </div>

          <button
            type="button"
            onClick={loadHealth}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Atualizar
          </button>
        </div>

        {error && (
          <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {health && (
          <>
            {/* STATUS */}

            <div
              className={[
                "mb-8 rounded-xl border p-6",

                health.status === "healthy"
                  ? "border-emerald-200 bg-emerald-50"
                  : "border-amber-200 bg-amber-50",
              ].join(" ")}
            >
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">

                <div>
                  <div className="text-sm font-medium text-slate-600">
                    Status geral
                  </div>

                  <div
                    className={[
                      "mt-1 text-2xl font-bold",

                      health.status === "healthy"
                        ? "text-emerald-800"
                        : "text-amber-800",
                    ].join(" ")}
                  >
                    {health.status === "healthy"
                      ? "Saudável"
                      : "Degradado"}
                  </div>
                </div>

                <div className="text-sm text-slate-500">
                  Verificado em{" "}
                  {formatDate(
                    health.checked_at
                  )}
                </div>

              </div>

              {health.problems.length > 0 && (
                <div className="mt-5 space-y-2">
                  {health.problems.map(
                    (problem) => (
                      <div
                        key={problem}
                        className="rounded-lg bg-white/70 px-4 py-2 text-sm text-slate-700"
                      >
                        {getProblemLabel(problem)}
                      </div>
                    )
                  )}
                </div>
              )}
            </div>

            {/* CARDS */}

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">

              <StatusCard
                label="Scheduler"
                value={
                  health.scheduler.running
                    ? "Ativo"
                    : "Parado"
                }
              />

              <StatusCard
                label="Stories Câmara · 24h"
                value={String(
                  health.camara
                    .stories_last_24h
                )}
              />

              <StatusCard
                label="Deliveries enviadas · 24h"
                value={String(
                  health.deliveries
                    .sent_last_24h
                )}
              />

              <StatusCard
                label="Canais ativos"
                value={String(
                  health
                    .notification_channels
                    .enabled
                )}
              />

            </div>

            {/* DETAILS */}

            <div className="mt-8 grid gap-6 lg:grid-cols-2">

              {/* INGESTION */}

              <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-slate-950">
                  Ingestão
                </h2>

                <div className="mt-5 space-y-4 text-sm">
                  <InfoRow
                    label="Fonte"
                    value="Câmara dos Deputados"
                  />

                  <InfoRow
                    label="Última story descoberta"
                    value={formatDate(
                      health.camara
                        .last_story_discovered_at
                    )}
                  />

                  <InfoRow
                    label="Stories últimas 24h"
                    value={String(
                      health.camara
                        .stories_last_24h
                    )}
                  />
                </div>
              </section>

              {/* DELIVERIES */}

              <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-slate-950">
                  Deliveries
                </h2>

                <div className="mt-5 space-y-4 text-sm">
                  <InfoRow
                    label="Pendentes"
                    value={String(
                      health.deliveries.pending
                    )}
                  />

                  <InfoRow
                    label="Enviando"
                    value={String(
                      health.deliveries.sending
                    )}
                  />

                  <InfoRow
                    label="Em retry"
                    value={String(
                      health.deliveries.retrying
                    )}
                  />

                  <InfoRow
                    label="Falha definitiva"
                    value={String(
                      health.deliveries
                        .permanently_failed
                    )}
                  />

                  <InfoRow
                    label="Último envio"
                    value={formatDate(
                      health.deliveries
                        .last_sent_at
                    )}
                  />
                </div>
              </section>

              {/* SCHEDULER */}

              <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-slate-950">
                  Scheduler
                </h2>

                <div className="mt-5 space-y-4">
                  {health.scheduler.jobs.map(
                    (job) => (
                      <div
                        key={job.id}
                        className="rounded-lg border border-slate-200 bg-slate-50 p-4"
                      >
                        <div className="font-mono text-sm font-medium text-slate-900">
                          {job.id}
                        </div>

                        <div className="mt-1 text-xs text-slate-500">
                          Próxima execução:{" "}
                          {formatDate(
                            job.next_run_time
                          )}
                        </div>
                      </div>
                    )
                  )}
                </div>
              </section>

              {/* CHANNELS */}

              <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-slate-950">
                  Canais
                </h2>

                <div className="mt-5 space-y-4 text-sm">
                  <InfoRow
                    label="Ativos"
                    value={String(
                      health
                        .notification_channels
                        .enabled
                    )}
                  />

                  <InfoRow
                    label="Desativados"
                    value={String(
                      health
                        .notification_channels
                        .disabled
                    )}
                  />
                </div>
              </section>

            </div>
          </>
        )}
      </div>
    </main>
  );
}

function StatusCard({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </div>

      <div className="mt-2 text-2xl font-semibold text-slate-950">
        {value}
      </div>
    </div>
  );
}

function InfoRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-100 pb-3 last:border-b-0 last:pb-0">
      <span className="text-slate-500">
        {label}
      </span>

      <span className="text-right font-medium text-slate-900">
        {value}
      </span>
    </div>
  );
}