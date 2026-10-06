"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import StoryContextLinks from "@/components/StoryContextLinks";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type ProfileListItem = {
  id: number;
  name: string;
  description?: string | null;
  enabled: boolean;
};

type ProfileDetail = {
  success: boolean;
  profile: {
    id: number;
    name: string;
    description?: string | null;
    enabled: boolean;
    min_relevance_score: number;
    min_urgency_score: number;
  };
  topics: Array<{
    id: number;
    topic: string;
    enabled: boolean;
  }>;
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
    published_at?: string | null;
  };
  relevance_score: number;
  urgency_score: number;
  matched_topics: Array<{ topic: string }>;
  is_alert: boolean;
  requires_attention?: boolean;
};

type MatchesResponse = {
  success: boolean;
  count: number;
  matches: MatchItem[];
};

type BriefingResponse = {
  success: boolean;
  briefing_text?: string;
};

function pct(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "—";
  }

  return `${Math.round(value * 100)}%`;
}

function formatDate(value?: string | null) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

export default function ClientDashboard() {
  const [profiles, setProfiles] = useState<ProfileListItem[]>([]);
  const [profileId, setProfileId] = useState<number | null>(null);
  const [detail, setDetail] = useState<ProfileDetail | null>(null);
  const [matches, setMatches] = useState<MatchItem[]>([]);
  const [briefing, setBriefing] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadProfiles() {
    const response = await fetch(
      `${API_BASE_URL}/monitoring-profiles`,
      { cache: "no-store" }
    );

    if (!response.ok) {
      throw new Error("Erro ao carregar os monitores.");
    }

    const data = await response.json();

    const rows: ProfileListItem[] = Array.isArray(data)
      ? data
      : data.profiles ?? data.results ?? [];

    setProfiles(rows);

    if (rows.length === 0) {
      setProfileId(null);
      setDetail(null);
      setMatches([]);
      setBriefing("");
      return;
    }

    setProfileId((current) => {
      if (
        current !== null &&
        rows.some((profile) => profile.id === current)
      ) {
        return current;
      }

      return rows[0].id;
    });
  }

  async function loadProfile(id: number) {
    const [detailResponse, matchesResponse, briefingResponse] =
      await Promise.all([
        fetch(`${API_BASE_URL}/monitoring-profiles/${id}`, {
          cache: "no-store",
        }),
        fetch(
          `${API_BASE_URL}/monitoring-profiles/${id}/matches?limit=20`,
          { cache: "no-store" }
        ),
        fetch(
          `${API_BASE_URL}/monitoring-profiles/${id}/briefing?hours=24&limit=20`,
          { cache: "no-store" }
        ),
      ]);

    if (!detailResponse.ok || !matchesResponse.ok) {
      throw new Error("Erro ao carregar o monitor.");
    }

    const detailData: ProfileDetail =
      await detailResponse.json();

    const matchesData: MatchesResponse =
      await matchesResponse.json();

    setDetail(detailData);
    setMatches(matchesData.matches ?? []);

    if (briefingResponse.ok) {
      const briefingData: BriefingResponse =
        await briefingResponse.json();

      setBriefing(briefingData.briefing_text ?? "");
    } else {
      setBriefing("");
    }
  }

  async function refresh() {
    try {
      setError("");
      await loadProfiles();

      if (profileId !== null) {
        await loadProfile(profileId);
      }
    } catch (err) {
      console.error(err);
      setError(
        err instanceof Error ? err.message : "Erro inesperado."
      );
    }
  }

  useEffect(() => {
    loadProfiles()
      .catch((err) => {
        console.error(err);
        setError(
          err instanceof Error ? err.message : "Erro inesperado."
        );
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (profileId === null) {
      return;
    }

    loadProfile(profileId).catch((err) => {
      console.error(err);
      setError(
        err instanceof Error ? err.message : "Erro inesperado."
      );
    });
  }, [profileId]);

  const urgent = useMemo(
    () =>
      matches
        .filter(
          (item) =>
            item.requires_attention ?? item.is_alert
        )
        .slice(0, 5),
    [matches]
  );

  const followUp = useMemo(
    () =>
      matches
        .filter(
          (item) =>
            !(item.requires_attention ?? item.is_alert)
        )
        .slice(0, 5),
    [matches]
  );

  if (loading) {
    return (
      <main className="p-6 md:p-8">
        <div className="mx-auto max-w-6xl">
          <div className="rounded-xl border border-gray-200 bg-white p-6 text-sm text-gray-500 shadow-sm">
            Carregando Newsroom AI...
          </div>
        </div>
      </main>
    );
  }

  if (profiles.length === 0) {
    return (
      <main className="p-6 md:p-8">
        <div className="mx-auto max-w-5xl">
          <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm md:p-12">
            <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
              Primeiro acesso
            </span>

            <h1 className="mt-5 max-w-3xl text-3xl font-bold tracking-tight text-gray-900 md:text-4xl">
              Transforme fontes institucionais em inteligência para a sua organização.
            </h1>

            <p className="mt-4 max-w-2xl text-base leading-7 text-gray-600">
              Você ainda não possui nenhum monitor configurado.
              Crie o primeiro monitor, escolha os temas de interesse
              e o Newsroom AI passará a separar o que exige atenção
              do que pode ser acompanhado no briefing.
            </p>

            <div className="mt-7">
              <Link
                href="/monitoring"
                className="inline-flex rounded-lg bg-gray-900 px-5 py-3 text-sm font-semibold text-white hover:bg-gray-800"
              >
                Criar primeiro monitor
              </Link>
            </div>

            <div className="mt-10 grid gap-4 md:grid-cols-3">
              <div className="rounded-xl bg-gray-50 p-5">
                <div className="text-sm font-semibold text-gray-900">
                  1. Defina o monitor
                </div>
                <p className="mt-2 text-sm leading-6 text-gray-500">
                  Dê um nome ao cliente, área ou setor que será acompanhado.
                </p>
              </div>

              <div className="rounded-xl bg-gray-50 p-5">
                <div className="text-sm font-semibold text-gray-900">
                  2. Escolha os temas
                </div>
                <p className="mt-2 text-sm leading-6 text-gray-500">
                  PIX, Open Finance, LGPD, apostas, energia, saúde e outros.
                </p>
              </div>

              <div className="rounded-xl bg-gray-50 p-5">
                <div className="text-sm font-semibold text-gray-900">
                  3. Receba inteligência
                </div>
                <p className="mt-2 text-sm leading-6 text-gray-500">
                  Relevância, urgência, alertas e briefing organizados.
                </p>
              </div>
            </div>
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
              Dashboard
            </h1>

            <p className="mt-2 text-gray-600">
              O que exige atenção e o que acompanhar agora.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
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

            <Link
              href="/monitoring"
              className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Configurar monitor
            </Link>

            <button
              onClick={refresh}
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

        {detail && (
          <>
            <section className="mt-8 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
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
                      {detail.profile.enabled
                        ? "Monitor ativo"
                        : "Monitor pausado"}
                    </span>
                  </div>

                  {detail.profile.description && (
                    <p className="mt-2 text-sm text-gray-600">
                      {detail.profile.description}
                    </p>
                  )}
                </div>

                <div className="text-sm text-gray-500">
                  {detail.topics.filter((topic) => topic.enabled).length} temas ativos
                </div>
              </div>

              <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-lg bg-red-50 p-4">
                  <div className="text-xs font-semibold uppercase tracking-wide text-red-500">
                    Atenção imediata
                  </div>
                  <div className="mt-1 text-3xl font-bold text-red-700">
                    {urgent.length}
                  </div>
                </div>

                <div className="rounded-lg bg-blue-50 p-4">
                  <div className="text-xs font-semibold uppercase tracking-wide text-blue-500">
                    Desenvolvimentos
                  </div>
                  <div className="mt-1 text-3xl font-bold text-blue-700">
                    {detail.stats.total_matches}
                  </div>
                </div>

                <div className="rounded-lg bg-gray-50 p-4">
                  <div className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                    Relevância mínima
                  </div>
                  <div className="mt-1 text-2xl font-semibold text-gray-900">
                    {pct(detail.profile.min_relevance_score)}
                  </div>
                </div>

                <div className="rounded-lg bg-gray-50 p-4">
                  <div className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                    Urgência mínima
                  </div>
                  <div className="mt-1 text-2xl font-semibold text-gray-900">
                    {pct(detail.profile.min_urgency_score)}
                  </div>
                </div>
              </div>
            </section>

            <section className="mt-6 rounded-xl border border-red-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    Atenção imediata
                  </h2>
                  <p className="mt-1 text-sm text-gray-500">
                    Desenvolvimentos que ultrapassaram o limite de urgência.
                  </p>
                </div>

                <span className="rounded-full bg-red-100 px-2.5 py-1 text-xs font-semibold text-red-700">
                  {urgent.length}
                </span>
              </div>

              <div className="mt-4 space-y-3">
                {urgent.length === 0 ? (
                  <div className="rounded-lg bg-gray-50 p-4 text-sm text-gray-500">
                    Nenhuma atenção imediata no momento.
                  </div>
                ) : (
                  urgent.map((item) => (
                    <article
                      key={item.match_id}
                      className="rounded-lg border border-red-100 bg-red-50/30 p-4"
                    >
                      <Link
                        href={`/stories/${item.story.id}${profileId ? `?profile=${profileId}` : ""}`}
                        className="font-semibold text-gray-900 hover:text-blue-700"
                      >
                        {item.story.title}
                      </Link>

                      <div className="mt-1 text-xs text-gray-500">
                        {item.story.source} · {formatDate(item.story.published_at)}
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

                        <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-gray-600">
                          Relevância {pct(item.relevance_score)}
                        </span>

                        <span className="rounded-full bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700">
                          Urgência {pct(item.urgency_score)}
                        </span>
                      </div>

                      <div className="mt-4 flex flex-wrap items-center gap-4">
                        <Link
                          href={`/stories/${item.story.id}${profileId ? `?profile=${profileId}` : ""}`}
                          className="text-sm font-medium text-gray-700 hover:underline"
                        >
                          Ver detalhes
                        </Link>

                        <StoryContextLinks
                          storyId={item.story.id}
                          profileId={profileId}
                        />
                      </div>
                    </article>
                  ))
                )}
              </div>
            </section>

            <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    Acompanhamento
                  </h2>
                  <p className="mt-1 text-sm text-gray-500">
                    Relevante para o monitor, sem necessidade de interrupção imediata.
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <Link
                    href="/acompanhamentos"
                    className="text-sm font-semibold text-blue-700 hover:underline"
                  >
                    Ver acompanhamentos →
                  </Link>

                  <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-600">
                    {followUp.length}
                  </span>
                </div>
              </div>

              <div className="mt-4 space-y-3">
                {followUp.length === 0 ? (
                  <div className="rounded-lg bg-gray-50 p-4 text-sm text-gray-500">
                    Nenhum item de acompanhamento no momento.
                  </div>
                ) : (
                  followUp.map((item) => (
                    <article
                      key={item.match_id}
                      className="rounded-lg border border-gray-200 p-4"
                    >
                      <Link
                        href={`/stories/${item.story.id}${profileId ? `?profile=${profileId}` : ""}`}
                        className="font-semibold text-gray-900 hover:text-blue-700"
                      >
                        {item.story.title}
                      </Link>

                      <div className="mt-1 text-xs text-gray-500">
                        {item.story.source} · {formatDate(item.story.published_at)}
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

                        <span className="rounded-full bg-gray-50 px-2.5 py-1 text-xs font-medium text-gray-600">
                          Relevância {pct(item.relevance_score)}
                        </span>

                        <span className="rounded-full bg-gray-50 px-2.5 py-1 text-xs font-medium text-gray-600">
                          Urgência {pct(item.urgency_score)}
                        </span>
                      </div>

                      <div className="mt-4 flex flex-wrap items-center gap-4">
                        <Link
                          href={`/stories/${item.story.id}${profileId ? `?profile=${profileId}` : ""}`}
                          className="text-sm font-medium text-gray-700 hover:underline"
                        >
                          Ver detalhes
                        </Link>

                        <StoryContextLinks
                          storyId={item.story.id}
                          profileId={profileId}
                        />
                      </div>
                    </article>
                  ))
                )}
              </div>
            </section>

            <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    Briefing das últimas 24 horas
                  </h2>
                  <p className="mt-1 text-sm text-gray-500">
                    Resumo consolidado do que entrou no seu monitor.
                  </p>
                </div>

                <Link
                  href="/monitoring"
                  className="text-sm font-medium text-blue-700 hover:underline"
                >
                  Gerenciar temas →
                </Link>
              </div>

              <div className="mt-4 whitespace-pre-wrap rounded-lg bg-gray-950 p-5 text-sm leading-7 text-gray-100">
                {briefing || "Nenhum briefing disponível para o período."}
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  );
}
