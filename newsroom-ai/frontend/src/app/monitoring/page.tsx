"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type MonitoringProfileSummary = {
  id: number;
  name: string;
  description?: string | null;
  enabled: boolean;
  min_relevance_score: number;
  min_urgency_score: number;
};

type MonitoringTopic = {
  id: number;
  topic: string;
  semantic_description?: string | null;
  weight: number;
  urgency_boost: number;
  enabled: boolean;
  created_at?: string;
};

type MonitoringProfileDetail = {
  success: boolean;
  profile: MonitoringProfileSummary & {
    alert_on_status_change: boolean;
    alert_on_new_measure: boolean;
    alert_on_date_change: boolean;
    alert_on_contradiction: boolean;
    created_at?: string;
    updated_at?: string;
  };
  topics: MonitoringTopic[];
  stats: {
    total_matches: number;
    total_alerts: number;
    new_alerts: number;
  };
};

type MatchItem = {
  match_id: number;
  story: {
    id: number;
    title: string;
    summary: string;
    source: string;
    category?: string | null;
    priority: string;
    priority_score: number;
    published_at?: string | null;
  };
  relevance_score: number;
  urgency_score: number;
  matched_topics: Array<{
    topic: string;
    match_type?: string;
    semantic_similarity?: number | null;
  }>;
  is_alert: boolean;
  requires_attention?: boolean;
  created_at: string;
};

type MatchesResponse = {
  success: boolean;
  count: number;
  matches: MatchItem[];
};

type BriefingResponse = {
  success: boolean;
  briefing_text: string;
};

function pct(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value * 100)}%`;
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(d);
}

function scoreClasses(value: number) {
  if (value >= 0.75) {
    return "bg-red-50 text-red-700 border-red-200";
  }

  if (value >= 0.5) {
    return "bg-amber-50 text-amber-700 border-amber-200";
  }

  return "bg-gray-50 text-gray-600 border-gray-200";
}

export default function MonitoringPage() {
  const [profiles, setProfiles] = useState<MonitoringProfileSummary[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState<number | null>(null);
  const [detail, setDetail] = useState<MonitoringProfileDetail | null>(null);
  const [matches, setMatches] = useState<MatchItem[]>([]);
  const [briefing, setBriefing] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [backfilling, setBackfilling] = useState(false);
  const [backfillMessage, setBackfillMessage] = useState("");
  const [error, setError] = useState("");

  const [showNewProfile, setShowNewProfile] = useState(false);
  const [newProfileName, setNewProfileName] = useState("");
  const [newProfileDescription, setNewProfileDescription] = useState("");

  const [newTopic, setNewTopic] = useState("");

  async function loadProfiles() {
    const response = await fetch(`${API_BASE_URL}/monitoring-profiles`, {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error("Erro ao carregar perfis de monitoramento");
    }

    const data = await response.json();
    const rows = Array.isArray(data) ? data : data.results ?? data.profiles ?? [];

    setProfiles(rows);

    if (rows.length > 0 && selectedProfileId === null) {
      setSelectedProfileId(rows[0].id);
    }
  }

  async function loadProfile(profileId: number) {
    const [detailResponse, matchesResponse, briefingResponse] =
      await Promise.all([
        fetch(`${API_BASE_URL}/monitoring-profiles/${profileId}`, {
          cache: "no-store",
        }),
        fetch(`${API_BASE_URL}/monitoring-profiles/${profileId}/matches?limit=50`, {
          cache: "no-store",
        }),
        fetch(`${API_BASE_URL}/monitoring-profiles/${profileId}/briefing?hours=24&limit=50`, {
          cache: "no-store",
        }),
      ]);

    if (!detailResponse.ok) {
      throw new Error("Erro ao carregar o perfil");
    }

    if (!matchesResponse.ok) {
      throw new Error("Erro ao carregar os matches");
    }

    const detailData: MonitoringProfileDetail = await detailResponse.json();
    const matchesData: MatchesResponse = await matchesResponse.json();

    setDetail(detailData);
    setMatches(matchesData.matches ?? []);

    if (briefingResponse.ok) {
      const briefingData: BriefingResponse = await briefingResponse.json();
      setBriefing(briefingData.briefing_text ?? "");
    } else {
      setBriefing("");
    }
  }

  async function refreshAll() {
    try {
      setLoading(true);
      setError("");

      await loadProfiles();

      if (selectedProfileId !== null) {
        await loadProfile(selectedProfileId);
      }
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Erro inesperado");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProfiles().catch((err) => {
      console.error(err);
      setError(err instanceof Error ? err.message : "Erro inesperado");
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    if (selectedProfileId === null) {
      setDetail(null);
      setMatches([]);
      setBriefing("");
      return;
    }

    setLoading(true);

    loadProfile(selectedProfileId)
      .catch((err) => {
        console.error(err);
        setError(err instanceof Error ? err.message : "Erro inesperado");
      })
      .finally(() => setLoading(false));
  }, [selectedProfileId]);

  const urgentMatches = useMemo(
    () =>
      matches.filter(
        (item) =>
          item.requires_attention ?? item.is_alert
      ),
    [matches]
  );

  const followUpMatches = useMemo(
    () =>
      matches.filter(
        (item) =>
          !(item.requires_attention ?? item.is_alert)
      ),
    [matches]
  );

  async function runBackfill(
    profileId: number,
    days = 30
  ) {
    try {
      setBackfilling(true);
      setBackfillMessage("");
      setError("");

      const response = await fetch(
        `${API_BASE_URL}/monitoring-profiles/${profileId}/backfill?days=${days}&limit=1000`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok || data?.success === false) {
        if (data?.reason === "profile_has_no_enabled_topics") {
          setBackfillMessage(
            "Adicione pelo menos um tema antes de analisar o histórico."
          );
          return;
        }

        throw new Error(
          data?.reason || "Erro ao analisar histórico"
        );
      }

      setBackfillMessage(
        `${data.stories_evaluated} stories analisadas · ` +
          `${data.matches} relevantes · ` +
          `${data.requires_attention} exigem atenção. ` +
          `Nenhuma notificação retroativa foi enviada.`
      );

      await loadProfile(profileId);
    } catch (err) {
      console.error(err);
      setError(
        err instanceof Error
          ? err.message
          : "Erro inesperado"
      );
    } finally {
      setBackfilling(false);
    }
  }

  async function createProfile(event: FormEvent) {
    event.preventDefault();

    if (!newProfileName.trim()) return;

    try {
      setSaving(true);
      setError("");

      const response = await fetch(`${API_BASE_URL}/monitoring-profiles`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: newProfileName.trim(),
          description: newProfileDescription.trim() || null,
          min_relevance_score: 0.5,
          min_urgency_score: 0.75,
          alert_on_status_change: true,
          alert_on_new_measure: true,
          alert_on_date_change: false,
          alert_on_contradiction: true,
        }),
      });

      if (!response.ok) {
        throw new Error("Erro ao criar perfil");
      }

      const created = await response.json();

      setNewProfileName("");
      setNewProfileDescription("");
      setShowNewProfile(false);

      await loadProfiles();

      if (created?.id) {
        setSelectedProfileId(created.id);
      } else if (created?.profile?.id) {
        setSelectedProfileId(created.profile.id);
      }
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Erro inesperado");
    } finally {
      setSaving(false);
    }
  }

  async function addTopic(event: FormEvent) {
    event.preventDefault();

    if (selectedProfileId === null || !newTopic.trim()) return;

    try {
      setSaving(true);
      setError("");

      const response = await fetch(
        `${API_BASE_URL}/monitoring-profiles/${selectedProfileId}/topics`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            topic: newTopic.trim(),
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Erro ao adicionar tema");
      }

      setNewTopic("");

      await runBackfill(selectedProfileId, 30);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Erro inesperado");
    } finally {
      setSaving(false);
    }
  }

  async function toggleProfile() {
    if (!detail || selectedProfileId === null) return;

    try {
      setSaving(true);

      const response = await fetch(
        `${API_BASE_URL}/monitoring-profiles/${selectedProfileId}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            enabled: !detail.profile.enabled,
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Erro ao atualizar perfil");
      }

      await Promise.all([
        loadProfile(selectedProfileId),
        loadProfiles(),
      ]);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Erro inesperado");
    } finally {
      setSaving(false);
    }
  }

  async function toggleTopic(topic: MonitoringTopic) {
    if (selectedProfileId === null) return;

    try {
      setSaving(true);

      const response = await fetch(
        `${API_BASE_URL}/monitoring-topics/${topic.id}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            enabled: !topic.enabled,
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Erro ao atualizar tema");
      }

      await loadProfile(selectedProfileId);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Erro inesperado");
    } finally {
      setSaving(false);
    }
  }

  async function deleteTopic(topicId: number) {
    if (selectedProfileId === null) return;

    try {
      setSaving(true);

      const response = await fetch(
        `${API_BASE_URL}/monitoring-topics/${topicId}`,
        {
          method: "DELETE",
        }
      );

      if (!response.ok) {
        throw new Error("Erro ao remover tema");
      }

      await loadProfile(selectedProfileId);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Erro inesperado");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-100 p-6 md:p-8">
      <div className="mx-auto max-w-7xl">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <Link
                href="/"
                className="text-sm font-medium text-blue-700 hover:underline"
              >
                ← Dashboard
              </Link>
            </div>

            <h1 className="mt-3 text-3xl font-bold text-gray-900">
              Client Monitor
            </h1>

            <p className="mt-2 max-w-3xl text-gray-600">
              Monitoramento personalizado de temas regulatórios e
              institucionais, com relevância, urgência e briefing por cliente.
            </p>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => setShowNewProfile((value) => !value)}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-800 hover:bg-gray-50"
            >
              + Novo monitor
            </button>

            <button
              onClick={refreshAll}
              className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
            >
              Atualizar
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {backfillMessage && (
          <div className="mt-6 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
            {backfillMessage}
          </div>
        )}

        {showNewProfile && (
          <form
            onSubmit={createProfile}
            className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
          >
            <h2 className="text-lg font-semibold text-gray-900">
              Novo monitor
            </h2>

            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">
                  Nome
                </label>

                <input
                  value={newProfileName}
                  onChange={(event) => setNewProfileName(event.target.value)}
                  placeholder="Ex.: Energia Brasil"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">
                  Descrição
                </label>

                <input
                  value={newProfileDescription}
                  onChange={(event) =>
                    setNewProfileDescription(event.target.value)
                  }
                  placeholder="Ex.: Monitoramento regulatório do setor elétrico"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div className="mt-4">
              <button
                disabled={saving}
                className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                Criar monitor
              </button>
            </div>
          </form>
        )}

        <div className="mt-8 grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
          <aside className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
              Monitores
            </div>

            <div className="space-y-2">
              {profiles.map((profile) => (
                <button
                  key={profile.id}
                  onClick={() => setSelectedProfileId(profile.id)}
                  className={[
                    "w-full rounded-lg border px-3 py-3 text-left transition",
                    selectedProfileId === profile.id
                      ? "border-blue-200 bg-blue-50"
                      : "border-gray-200 bg-white hover:bg-gray-50",
                  ].join(" ")}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-gray-900">
                      {profile.name}
                    </span>

                    <span
                      className={[
                        "h-2.5 w-2.5 rounded-full",
                        profile.enabled ? "bg-emerald-500" : "bg-gray-300",
                      ].join(" ")}
                    />
                  </div>

                  {profile.description && (
                    <p className="mt-1 line-clamp-2 text-xs text-gray-500">
                      {profile.description}
                    </p>
                  )}
                </button>
              ))}

              {!loading && profiles.length === 0 && (
                <p className="text-sm text-gray-500">
                  Nenhum monitor criado.
                </p>
              )}
            </div>
          </aside>

          <div className="min-w-0">
            {loading && !detail ? (
              <div className="rounded-xl bg-white p-6 text-sm text-gray-500 shadow-sm">
                Carregando monitor...
              </div>
            ) : !detail ? (
              <div className="rounded-xl bg-white p-6 text-sm text-gray-500 shadow-sm">
                Selecione ou crie um monitor.
              </div>
            ) : (
              <>
                <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <div className="flex flex-wrap items-center gap-3">
                        <h2 className="text-2xl font-semibold text-gray-900">
                          {detail.profile.name}
                        </h2>

                        <span
                          className={[
                            "rounded-full px-2.5 py-1 text-xs font-semibold",
                            detail.profile.enabled
                              ? "bg-emerald-100 text-emerald-700"
                              : "bg-gray-100 text-gray-600",
                          ].join(" ")}
                        >
                          {detail.profile.enabled ? "Ativo" : "Pausado"}
                        </span>
                      </div>

                      <p className="mt-2 text-sm text-gray-600">
                        {detail.profile.description || "Sem descrição."}
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() =>
                          selectedProfileId !== null &&
                          runBackfill(selectedProfileId, 30)
                        }
                        disabled={saving || backfilling}
                        className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50"
                      >
                        {backfilling
                          ? "Analisando histórico..."
                          : "Analisar histórico · 30 dias"}
                      </button>

                      <button
                        onClick={toggleProfile}
                        disabled={saving || backfilling}
                        className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                      >
                        {detail.profile.enabled
                          ? "Pausar monitor"
                          : "Ativar monitor"}
                      </button>
                    </div>
                  </div>

                  <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-lg bg-gray-50 p-4">
                      <div className="text-xs uppercase tracking-wide text-gray-400">
                        Relevantes
                      </div>
                      <div className="mt-1 text-2xl font-semibold text-gray-900">
                        {detail.stats.total_matches}
                      </div>
                    </div>

                    <div className="rounded-lg bg-red-50 p-4">
                      <div className="text-xs uppercase tracking-wide text-red-500">
                        Alertas
                      </div>
                      <div className="mt-1 text-2xl font-semibold text-red-700">
                        {detail.stats.total_alerts}
                      </div>
                    </div>

                    <div className="rounded-lg bg-orange-50 p-4">
                      <div className="text-xs uppercase tracking-wide text-orange-500">
                        Novos alertas
                      </div>
                      <div className="mt-1 text-2xl font-semibold text-orange-700">
                        {detail.stats.new_alerts}
                      </div>
                    </div>

                    <div className="rounded-lg bg-blue-50 p-4">
                      <div className="text-xs uppercase tracking-wide text-blue-500">
                        Temas ativos
                      </div>
                      <div className="mt-1 text-2xl font-semibold text-blue-700">
                        {detail.topics.filter((topic) => topic.enabled).length}
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 flex flex-wrap gap-4 text-sm text-gray-500">
                    <span>
                      Relevância mínima:{" "}
                      <strong className="text-gray-800">
                        {pct(detail.profile.min_relevance_score)}
                      </strong>
                    </span>

                    <span>
                      Urgência mínima:{" "}
                      <strong className="text-gray-800">
                        {pct(detail.profile.min_urgency_score)}
                      </strong>
                    </span>
                  </div>
                </section>

                <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">
                      Temas monitorados
                    </h3>

                    <p className="mt-1 text-sm text-gray-500">
                      O nome do tema serve para match literal. A descrição
                      semântica amplia o conceito usado pelos embeddings.
                    </p>
                  </div>

                  <div className="mt-5 grid gap-3 md:grid-cols-2">
                    {detail.topics.map((topic) => (
                      <div
                        key={topic.id}
                        className="rounded-lg border border-gray-200 p-4"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-semibold text-gray-900">
                                {topic.topic}
                              </span>

                              <span
                                className={[
                                  "rounded-full px-2 py-0.5 text-xs font-medium",
                                  topic.enabled
                                    ? "bg-emerald-100 text-emerald-700"
                                    : "bg-gray-100 text-gray-500",
                                ].join(" ")}
                              >
                                {topic.enabled ? "Ativo" : "Pausado"}
                              </span>
                            </div>

                            <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">
                              <span>Peso: {topic.weight.toFixed(2)}</span>
                              <span>
                                Boost urgência: {topic.urgency_boost.toFixed(2)}
                              </span>
                            </div>
                          </div>

                          <div className="flex gap-2">
                            <button
                              onClick={() => toggleTopic(topic)}
                              className="text-xs font-medium text-blue-700 hover:underline"
                            >
                              {topic.enabled ? "Pausar" : "Ativar"}
                            </button>

                            <button
                              onClick={() => deleteTopic(topic.id)}
                              className="text-xs font-medium text-red-600 hover:underline"
                            >
                              Remover
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <form
                    onSubmit={addTopic}
                    className="mt-5 rounded-lg bg-gray-50 p-4"
                  >
                    <div className="text-sm font-semibold text-gray-800">
                      Adicionar tema de interesse
                    </div>

                    <p className="mt-1 text-xs leading-5 text-gray-500">
                      Informe apenas a palavra-chave ou matéria que deseja
                      acompanhar. O sistema prepara automaticamente a busca.
                    </p>

                    <div className="mt-3 flex flex-col gap-3 sm:flex-row">
                      <input
                        value={newTopic}
                        onChange={(event) =>
                          setNewTopic(event.target.value)
                        }
                        placeholder="Ex.: ANEEL, PIX, Bets, Open Finance"
                        className="min-w-0 flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
                      />

                      <button
                        disabled={saving || backfilling}
                        className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                      >
                        {saving
                          ? "Preparando tema..."
                          : "Adicionar tema"}
                      </button>
                    </div>
                  </form>
                </section>

                {urgentMatches.length > 0 && (
                  <section className="mt-6 rounded-xl border border-red-200 bg-white p-5 shadow-sm">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                          Atenção imediata
                        </h3>
                        <p className="mt-1 text-sm text-gray-500">
                          Desenvolvimentos que ultrapassaram o limite de urgência.
                        </p>
                      </div>

                      <span className="rounded-full bg-red-100 px-2.5 py-1 text-xs font-semibold text-red-700">
                        {urgentMatches.length}
                      </span>
                    </div>

                    <div className="mt-4 space-y-3">
                      {urgentMatches.map((item) => (
                        <article
                          key={item.match_id}
                          className="rounded-lg border border-red-100 bg-red-50/30 p-4"
                        >
                          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                            <div className="min-w-0">
                              <Link
                                href={`/stories/${item.story.id}`}
                                className="font-semibold text-gray-900 hover:text-blue-700"
                              >
                                {item.story.title}
                              </Link>

                              <div className="mt-1 text-xs text-gray-500">
                                {item.story.source} ·{" "}
                                {formatDate(item.story.published_at)}
                              </div>

                              <p className="mt-3 text-sm leading-6 text-gray-600">
                                {item.story.summary}
                              </p>

                              <div className="mt-3 flex flex-wrap gap-2">
                                {item.matched_topics.map((topic, index) => (
                                  <span
                                    key={`${item.match_id}-${topic.topic}-${index}`}
                                    className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700"
                                  >
                                    {topic.topic}
                                  </span>
                                ))}
                              </div>
                            </div>

                            <div className="flex shrink-0 gap-2">
                              <span
                                className={[
                                  "rounded-lg border px-3 py-2 text-xs font-semibold",
                                  scoreClasses(item.relevance_score),
                                ].join(" ")}
                              >
                                Relevância {pct(item.relevance_score)}
                              </span>

                              <span
                                className={[
                                  "rounded-lg border px-3 py-2 text-xs font-semibold",
                                  scoreClasses(item.urgency_score),
                                ].join(" ")}
                              >
                                Urgência {pct(item.urgency_score)}
                              </span>
                            </div>
                          </div>
                        </article>
                      ))}
                    </div>
                  </section>
                )}

                <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        Acompanhamento
                      </h3>
                      <p className="mt-1 text-sm text-gray-500">
                        Stories relevantes que não exigem alerta imediato.
                      </p>
                    </div>

                    <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-600">
                      {followUpMatches.length}
                    </span>
                  </div>

                  <div className="mt-4 space-y-3">
                    {followUpMatches.length === 0 ? (
                      <div className="rounded-lg bg-gray-50 p-4 text-sm text-gray-500">
                        Nenhum item de acompanhamento.
                      </div>
                    ) : (
                      followUpMatches.map((item) => (
                        <article
                          key={item.match_id}
                          className="rounded-lg border border-gray-200 p-4"
                        >
                          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                            <div className="min-w-0">
                              <Link
                                href={`/stories/${item.story.id}`}
                                className="font-semibold text-gray-900 hover:text-blue-700"
                              >
                                {item.story.title}
                              </Link>

                              <div className="mt-1 text-xs text-gray-500">
                                {item.story.source} ·{" "}
                                {formatDate(item.story.published_at)}
                              </div>

                              <p className="mt-3 text-sm leading-6 text-gray-600">
                                {item.story.summary}
                              </p>

                              <div className="mt-3 flex flex-wrap gap-2">
                                {item.matched_topics.map((topic, index) => (
                                  <span
                                    key={`${item.match_id}-${topic.topic}-${index}`}
                                    className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700"
                                  >
                                    {topic.topic}
                                  </span>
                                ))}
                              </div>
                            </div>

                            <div className="flex shrink-0 gap-2">
                              <span className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs font-semibold text-gray-600">
                                Relevância {pct(item.relevance_score)}
                              </span>

                              <span className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs font-semibold text-gray-600">
                                Urgência {pct(item.urgency_score)}
                              </span>
                            </div>
                          </div>
                        </article>
                      ))
                    )}
                  </div>
                </section>

                <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Briefing — últimas 24 horas
                  </h3>

                  <p className="mt-1 text-sm text-gray-500">
                    Visão consolidada do monitor pronta para leitura.
                  </p>

                  <div className="mt-4 whitespace-pre-wrap rounded-lg bg-gray-950 p-5 text-sm leading-7 text-gray-100">
                    {briefing || "Nenhum briefing disponível para o período."}
                  </div>
                </section>
              </>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
