"use client";

import { FormEvent, useEffect, useState } from "react";

type NotificationChannel = {
  id: number;
  name: string;
  channel: string;
  destination: string;
  enabled: boolean;
  min_priority_score: number | null;
  min_meaningful_change_score: number | null;
  created_at: string;
  updated_at: string;
};

type ChannelsResponse = {
  count: number;
  results: NotificationChannel[];
};

type ChannelForm = {
  name: string;
  channel: string;
  destination: string;
  min_priority_score: string;
  min_meaningful_change_score: string;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const emptyForm: ChannelForm = {
  name: "",
  channel: "telegram",
  destination: "",
  min_priority_score: "",
  min_meaningful_change_score: "",
};

function formatScore(value: number | null) {
  if (value === null) {
    return "Sem limite";
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

export default function NotificationChannelsPage() {
  const [channels, setChannels] = useState<NotificationChannel[]>([]);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState<ChannelForm>(emptyForm);

  const [editingId, setEditingId] =
    useState<number | null>(null);

  async function loadChannels() {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `${API_BASE_URL}/notification-channels`,
        {
          cache: "no-store",
        }
      );

      if (!response.ok) {
        throw new Error(
          `Erro ao carregar canais: ${response.status}`
        );
      }

      const data: ChannelsResponse =
        await response.json();

      setChannels(data.results ?? []);
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : "Erro inesperado ao carregar canais."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadChannels();
  }, []);

  function updateForm(
    field: keyof ChannelForm,
    value: string
  ) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function resetForm() {
    setEditingId(null);
    setForm(emptyForm);
  }

  function startEditing(
    channel: NotificationChannel
  ) {
    setEditingId(channel.id);

    setForm({
      name: channel.name,
      channel: channel.channel,
      destination: channel.destination,
      min_priority_score:
        channel.min_priority_score !== null
          ? String(channel.min_priority_score)
          : "",
      min_meaningful_change_score:
        channel.min_meaningful_change_score !== null
          ? String(
              channel.min_meaningful_change_score
            )
          : "",
    });

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }

  async function submitForm(
    event: FormEvent
  ) {
    event.preventDefault();

    try {
      setSaving(true);
      setError(null);

      if (!form.name.trim()) {
        throw new Error(
          "Informe o nome do canal."
        );
      }

      if (!form.destination.trim()) {
        throw new Error(
          "Informe o destino."
        );
      }

      const payload = {
        name: form.name.trim(),

        channel: form.channel,

        destination:
          form.destination.trim(),

        min_priority_score:
          form.min_priority_score === ""
            ? null
            : Number(
                form.min_priority_score
              ),

        min_meaningful_change_score:
          form.min_meaningful_change_score === ""
            ? null
            : Number(
                form.min_meaningful_change_score
              ),
      };

      if (
        payload.min_priority_score !== null &&
        (
          Number.isNaN(
            payload.min_priority_score
          ) ||
          payload.min_priority_score < 0 ||
          payload.min_priority_score > 1
        )
      ) {
        throw new Error(
          "A prioridade mínima deve estar entre 0 e 1."
        );
      }

      if (
        payload.min_meaningful_change_score !== null &&
        (
          Number.isNaN(
            payload.min_meaningful_change_score
          ) ||
          payload.min_meaningful_change_score < 0 ||
          payload.min_meaningful_change_score > 1
        )
      ) {
        throw new Error(
          "A mudança mínima deve estar entre 0 e 1."
        );
      }

      let response: Response;

      if (editingId !== null) {
        response = await fetch(
          `${API_BASE_URL}/notification-channels/${editingId}`,
          {
            method: "PATCH",

            headers: {
              "Content-Type": "application/json",
            },

            body: JSON.stringify({
              name: payload.name,
              destination:
                payload.destination,

              min_priority_score:
                payload.min_priority_score,

              min_meaningful_change_score:
                payload.min_meaningful_change_score,
            }),
          }
        );
      } else {
        response = await fetch(
          `${API_BASE_URL}/notification-channels`,
          {
            method: "POST",

            headers: {
              "Content-Type": "application/json",
            },

            body: JSON.stringify({
              ...payload,
              enabled: true,
            }),
          }
        );
      }

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            data.reason ||
            "Erro ao salvar canal."
        );
      }

      resetForm();

      await loadChannels();
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : "Erro inesperado ao salvar canal."
      );
    } finally {
      setSaving(false);
    }
  }

  async function toggleChannel(
    channelId: number
  ) {
    try {
      setError(null);

      const response = await fetch(
        `${API_BASE_URL}/notification-channels/${channelId}/toggle`,
        {
          method: "PATCH",
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Erro ao alterar canal."
        );
      }

      await loadChannels();
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : "Erro inesperado."
      );
    }
  }

  async function deleteChannel(
    channel: NotificationChannel
  ) {
    const confirmed = window.confirm(
      `Excluir o canal "${channel.name}"?`
    );

    if (!confirmed) {
      return;
    }

    try {
      setError(null);

      const response = await fetch(
        `${API_BASE_URL}/notification-channels/${channel.id}`,
        {
          method: "DELETE",
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Erro ao excluir canal."
        );
      }

      if (editingId === channel.id) {
        resetForm();
      }

      await loadChannels();
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : "Erro inesperado."
      );
    }
  }

  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-6xl px-6 py-8">

        {/* HEADER */}

        <div className="mb-8">
          <div className="text-sm font-medium uppercase tracking-wider text-slate-500">
            Newsroom AI
          </div>

          <h1 className="mt-2 text-3xl font-bold text-slate-950">
            Canais de notificação
          </h1>

          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Configure onde os alertas da newsroom
            devem ser enviados e quais limites cada
            canal deve respeitar.
          </p>
        </div>

        {/* ERROR */}

        {error && (
          <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* FORM */}

        <form
          onSubmit={submitForm}
          className="mb-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <div className="mb-5 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-950">
              {editingId !== null
                ? "Editar canal"
                : "Novo canal"}
            </h2>

            {editingId !== null && (
              <button
                type="button"
                onClick={resetForm}
                className="text-sm font-medium text-slate-500 hover:text-slate-900"
              >
                Cancelar edição
              </button>
            )}
          </div>

          <div className="grid gap-5 md:grid-cols-2">

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">
                Nome
              </label>

              <input
                value={form.name}
                onChange={(event) =>
                  updateForm(
                    "name",
                    event.target.value
                  )
                }
                placeholder="Telegram Newsroom"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">
                Canal
              </label>

              <select
                value={form.channel}
                disabled={
                  editingId !== null
                }
                onChange={(event) =>
                  updateForm(
                    "channel",
                    event.target.value
                  )
                }
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm disabled:bg-slate-100"
              >
                <option value="telegram">
                  Telegram
                </option>

                <option value="email">
                  Email
                </option>

                <option value="webhook">
                  Webhook
                </option>
              </select>

              {editingId !== null && (
                <p className="mt-1 text-xs text-slate-500">
                  O tipo do canal não pode ser alterado.
                </p>
              )}
            </div>

            <div className="md:col-span-2">
              <label className="mb-2 block text-sm font-medium text-slate-700">
                Destino
              </label>

              <input
                value={form.destination}
                onChange={(event) =>
                  updateForm(
                    "destination",
                    event.target.value
                  )
                }
                placeholder="-1001234567890"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-slate-500"
              />

              <p className="mt-1 text-xs text-slate-500">
                Para Telegram, informe o chat_id ou @nomecanal.
              </p>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">
                Prioridade mínima
              </label>

              <input
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={
                  form.min_priority_score
                }
                onChange={(event) =>
                  updateForm(
                    "min_priority_score",
                    event.target.value
                  )
                }
                placeholder="Sem limite"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">
                Mudança mínima
              </label>

              <input
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={
                  form.min_meaningful_change_score
                }
                onChange={(event) =>
                  updateForm(
                    "min_meaningful_change_score",
                    event.target.value
                  )
                }
                placeholder="Sem limite"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500"
              />
            </div>
          </div>

          <div className="mt-6">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving
                ? "Salvando..."
                : editingId !== null
                ? "Salvar alterações"
                : "Criar canal"}
            </button>
          </div>
        </form>

        {/* LIST */}

        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-950">
            Canais configurados
          </h2>

          <button
            type="button"
            onClick={loadChannels}
            className="text-sm font-medium text-blue-700 hover:underline"
          >
            Atualizar
          </button>
        </div>

        {loading ? (
          <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
            Carregando canais...
          </div>
        ) : channels.length === 0 ? (
          <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
            Nenhum canal configurado.
          </div>
        ) : (
          <div className="space-y-4">
            {channels.map((channel) => (
              <article
                key={channel.id}
                className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
              >
                <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">

                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-semibold text-slate-950">
                        {channel.name}
                      </h3>

                      <span
                        className={[
                          "rounded-full border px-2.5 py-1 text-xs font-medium",

                          channel.enabled
                            ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                            : "border-slate-200 bg-slate-100 text-slate-500",
                        ].join(" ")}
                      >
                        {channel.enabled
                          ? "Ativo"
                          : "Desativado"}
                      </span>

                      <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-600">
                        {channel.channel}
                      </span>
                    </div>

                    <div className="mt-4 space-y-2 text-sm text-slate-600">
                      <div>
                        <span className="font-medium text-slate-800">
                          Destino:
                        </span>{" "}
                        <span className="font-mono">
                          {channel.destination}
                        </span>
                      </div>

                      <div>
                        <span className="font-medium text-slate-800">
                          Prioridade mínima:
                        </span>{" "}
                        {formatScore(
                          channel.min_priority_score
                        )}
                      </div>

                      <div>
                        <span className="font-medium text-slate-800">
                          Mudança mínima:
                        </span>{" "}
                        {formatScore(
                          channel.min_meaningful_change_score
                        )}
                      </div>

                      <div className="text-xs text-slate-400">
                        Atualizado em{" "}
                        {formatDate(
                          channel.updated_at
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">

                    <button
                      type="button"
                      onClick={() =>
                        toggleChannel(
                          channel.id
                        )
                      }
                      className={[
                        "rounded-lg px-4 py-2 text-sm font-medium transition",

                        channel.enabled
                          ? "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                          : "bg-slate-900 text-white hover:bg-slate-700",
                      ].join(" ")}
                    >
                      {channel.enabled
                        ? "Desativar"
                        : "Ativar"}
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        startEditing(
                          channel
                        )
                      }
                      className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                    >
                      Editar
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        deleteChannel(
                          channel
                        )
                      }
                      className="rounded-lg border border-red-200 bg-white px-4 py-2 text-sm font-medium text-red-600 transition hover:bg-red-50"
                    >
                      Excluir
                    </button>

                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}