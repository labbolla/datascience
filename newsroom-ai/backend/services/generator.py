import json
import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


MODEL_NAME = "gpt-6-luna"


api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY não encontrada no arquivo .env"
    )


client = OpenAI(
    api_key=api_key
)


def generate_change_summary(
    current_story: dict,
    previous_stories: list[dict],
    changes: dict,
) -> dict:
    """
    Generates a concise, factual newsroom-oriented explanation
    of what changed compared with the previous history.

    OpenAI is used only for language generation.
    The factual source remains the supplied documents.
    """

    previous_text = []

    for index, story in enumerate(
        previous_stories,
        start=1,
    ):
        previous_text.append(
            "\n".join(
                [
                    f"DOCUMENTO ANTERIOR {index}",
                    f"ID: {story.get('id', '')}",
                    f"Título: {story.get('title', '')}",
                    f"Conteúdo: {story.get('summary', '')}",
                ]
            )
        )

    history_text = "\n\n".join(
        previous_text
    )

    signals_text = json.dumps(
        changes,
        ensure_ascii=False,
        indent=2,
    )

    instructions = """
Você é um assistente de apoio a uma redação jornalística.

Sua tarefa é explicar de forma factual SOMENTE o que a STORY NOVA
acrescenta, altera, esclarece, corrige ou contradiz em relação
ao histórico anterior fornecido.

REGRAS OBRIGATÓRIAS:

- Use SOMENTE os documentos fornecidos.
- Não use conhecimento externo.
- Não invente fatos, contexto, causas ou consequências.
- Descreva primeiro a DIFERENÇA em relação ao histórico.
- Não resuma novamente toda a story nova.
- Não comece com frases como "A nova story é..." quando isso não for necessário.
- Não transforme diferenças de redação em diferenças factuais.
- Não presuma causalidade.
- Não faça avaliações políticas ou editoriais.
- Não diga que algo é importante, grave, positivo ou negativo.
- Os sinais estruturados servem apenas como apoio.
- O texto dos documentos é a fonte factual principal.
- Os sinais estruturados nunca substituem o conteúdo factual dos documentos.
- Se não houver mudança factual relevante, diga isso claramente.
- Identifique concretamente a novidade quando for possível.
- Preserve com precisão nomes, cargos, instituições, números, datas e referências.
- Não abrevie nomes de pessoas de uma forma que possa gerar ambiguidade.
- Em afirmações sobre investigação, acusação, condenação, suspeita,
  processo judicial ou qualquer status jurídico, preserve exatamente
  quem é o sujeito da afirmação e a forma como ela aparece nos documentos.
- Não atribua a uma pessoa algo que o documento não atribua explicitamente a ela.
- Não transforme alegações, pedidos, acusações ou declarações dos documentos
  em fatos estabelecidos.
- Quando necessário, use formulações atributivas como
  "o documento afirma", "o requerimento menciona" ou "o pedido solicita".
- Se houver apenas mudança de destinatário, ator, data, quantidade
  ou instrumento, diga isso diretamente.
- Escreva em português brasileiro.
- Use preferencialmente 1 ou 2 frases.
- Use no máximo 3 frases.
- Seja conciso.
- Não mencione IA, JEV, scores, probabilidades, tokens ou modelos.
""".strip()

    user_input = f"""
STORY NOVA

Título:
{current_story.get("title", "")}

Conteúdo:
{current_story.get("summary", "")}


HISTÓRICO ANTERIOR

{history_text}


SINAIS ESTRUTURADOS JÁ CALCULADOS

{signals_text}


Escreva agora o resumo factual do que mudou.

Comece diretamente pela diferença mais concreta em relação ao histórico.
""".strip()

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=instructions,
        input=user_input,
        max_output_tokens=250,
    )

    summary = (
        response.output_text or ""
    ).strip()

    usage = getattr(
        response,
        "usage",
        None,
    )

    metadata = {
        "provider": "OpenAI",
        "model": response.model,
        "response_id": response.id,
    }

    if usage:
        metadata["usage"] = {
            "input_tokens": getattr(
                usage,
                "input_tokens",
                None,
            ),
            "output_tokens": getattr(
                usage,
                "output_tokens",
                None,
            ),
            "total_tokens": getattr(
                usage,
                "total_tokens",
                None,
            ),
        }

    return {
        "summary": summary,
        "metadata": metadata,
    }

def generate_thread_identity(
    stories: list[dict],
) -> dict:
    """
    Generates an editorial title and short summary
    for a story thread using only the supplied stories.
    """

    if not stories:
        raise ValueError(
            "Não existem stories para gerar o thread."
        )

    documents = []

    for index, story in enumerate(
        stories,
        start=1,
    ):
        documents.append(
            "\n".join(
                [
                    f"STORY {index}",
                    f"ID: {story.get('id', '')}",
                    f"Título: {story.get('title', '')}",
                    f"Conteúdo: {story.get('summary', '')}",
                ]
            )
        )

    stories_text = "\n\n".join(
        documents
    )

    instructions = """
Você é um assistente de apoio a uma redação jornalística.

Sua tarefa é criar a identidade editorial de um thread
que agrupa várias stories relacionadas.

Use SOMENTE as informações fornecidas.

REGRAS PARA O TÍTULO:

- Deve identificar o assunto específico que une as stories.
- Não use títulos genéricos como "Atualizações políticas".
- Não use "Thread", "Story" ou "Notícia".
- Não use linguagem sensacionalista.
- Não faça avaliações políticas.
- Não invente contexto.
- Preserve nomes, números e referências importantes quando forem úteis.
- Evite usar apenas o número de um documento se houver uma descrição
  mais informativa disponível.
- O título deve ser curto e facilmente escaneável por um jornalista.
- Preferencialmente até 100 caracteres.
- Em referências a investigação, acusação, suspeita, condenação ou status jurídico,
  preserve a atribuição ao documento quando ela existir.
- Não transforme afirmações, alegações ou enquadramentos presentes nas stories
  em fatos estabelecidos.
- Quando necessário, use formulações como
  "os requerimentos mencionam", "os documentos afirmam" ou
  "as stories fazem referência a".
- Preserve com precisão quem é o sujeito de qualquer afirmação jurídica.
- Use no máximo 100 caracteres.

REGRAS PARA O RESUMO:

- Explique em uma ou duas frases o que une as stories.
- Descreva o assunto central e, quando aplicável,
  como ele está evoluindo.
- Não faça previsões.
- Não use conhecimento externo.
- Não transforme alegações dos documentos em fatos estabelecidos.
- Seja factual e neutro.
- Não mencione IA, scores, modelos ou processos internos.
- Deve ter entre 35 e 70 palavras.
- Use no máximo 2 frases no resumo.
- Evite repetir informação que já aparece no título.

FORMATO OBRIGATÓRIO:

TITULO: <título>
RESUMO: <resumo>

Não escreva nenhuma outra linha.
""".strip()

    user_input = f"""
STORIES DO THREAD

{stories_text}


Crie o título e o resumo deste thread.
""".strip()

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=instructions,
        input=user_input,
        max_output_tokens=400,
    )

    output = (
        response.output_text or ""
    ).strip()

    title = None
    summary = None

    for line in output.splitlines():

        clean_line = line.strip()

        if clean_line.upper().startswith(
            "TITULO:"
        ):
            title = clean_line.split(
                ":",
                1,
            )[1].strip()

        elif clean_line.upper().startswith(
            "TÍTULO:"
        ):
            title = clean_line.split(
                ":",
                1,
            )[1].strip()

        elif clean_line.upper().startswith(
            "RESUMO:"
        ):
            summary = clean_line.split(
                ":",
                1,
            )[1].strip()

    if not title or not summary:
        raise ValueError(
            "Resposta do gerador de thread "
            "não pôde ser interpretada: "
            f"{output}"
        )

    usage = getattr(
        response,
        "usage",
        None,
    )

    metadata = {
        "provider": "OpenAI",
        "model": response.model,
        "response_id": response.id,
    }

    if usage:
        metadata["usage"] = {
            "input_tokens": getattr(
                usage,
                "input_tokens",
                None,
            ),
            "output_tokens": getattr(
                usage,
                "output_tokens",
                None,
            ),
            "total_tokens": getattr(
                usage,
                "total_tokens",
                None,
            ),
        }

    return {
        "title": title,
        "summary": summary,
        "metadata": metadata,
    }