"""Transform Portal da Transparência travel CSV exports into normalized tables.

This is a cleaned portfolio version of the original academic ETL workflow.
It expects the column names used by the 2024 Portal da Transparência exports
used in the project and produces CSV files that match `sql/schema/schema.sql`.

Raw data are not committed to the repository. Traveler CPF values are replaced
with artificial IDs in the generated tables.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import pandas as pd


TRAVEL_REQUIRED = {
    "Identificador do processo de viagem",
    "Viagem Urgente",
    "Motivo",
    "Valor diárias",
    "Valor passagens",
    "Valor outros gastos",
    "Valor devolução",
    "Nome",
    "Cargo",
    "Código órgão solicitante",
    "Nome órgão solicitante",
    "Código do órgão superior",
    "Nome do órgão superior",
}

SEGMENT_REQUIRED = {
    "Sequência Trecho",
    "Meio de transporte",
    "Número Diárias",
    "Missao?",
    "Origem - Data",
    "Destino - Data",
    "Origem - Cidade",
    "Origem - UF",
    "Origem - País",
    "Destino - Cidade",
    "Destino - UF",
    "Destino - País",
    "Identificador do processo de viagem",
}


def read_portal_csv(path: Path) -> pd.DataFrame:
    """Read a semicolon-delimited Portal CSV with common Brazilian encodings."""
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(path, sep=";", encoding=encoding, dtype=str, low_memory=False)
            df.columns = df.columns.str.strip()
            return df
        except UnicodeDecodeError as exc:
            last_error = exc
    raise RuntimeError(f"Unable to decode {path}") from last_error


def require_columns(df: pd.DataFrame, required: Iterable[str], source_name: str) -> None:
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"{source_name} is missing required columns: {missing}")


def decimal_series(series: pd.Series) -> pd.Series:
    """Convert Brazilian decimal strings such as 1.234,56 to numeric values."""
    s = series.fillna("").astype(str).str.strip()
    comma_decimal = s.str.contains(",", regex=False)
    s.loc[comma_decimal] = (
        s.loc[comma_decimal]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    s = s.str.replace(r"[^0-9.\-]", "", regex=True)
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def date_series(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, dayfirst=True, errors="coerce")
    return parsed.dt.strftime("%Y-%m-%d")


def clean_text(value: object, fallback: str = "Nao informado") -> str:
    if pd.isna(value):
        return fallback
    text = str(value).strip()
    return text if text else fallback


def build_artificial_ids(names: pd.Series) -> pd.Series:
    """Generate stable sequential artificial IDs based on unique traveler names."""
    cleaned = names.fillna("").astype(str).str.strip()
    unique_names = sorted(n for n in cleaned.unique() if n)
    mapping = {name: f"ART{idx:010d}" for idx, name in enumerate(unique_names, start=1)}

    # Keep missing-name records distinct enough for referential integrity.
    missing_counter = 0
    result = []
    for name in cleaned:
        if name:
            result.append(mapping[name])
        else:
            missing_counter += 1
            result.append(f"ARTMISSING{missing_counter:07d}")
    return pd.Series(result, index=names.index, dtype="object")


def transform_travel(df: pd.DataFrame, out_dir: Path) -> None:
    require_columns(df, TRAVEL_REQUIRED, "travel CSV")
    work = df.copy()

    work["cpf_artificial"] = build_artificial_ids(work["Nome"])
    work["urgencia"] = work["Viagem Urgente"].fillna("").astype(str).str.strip().str.upper().eq("SIM").map({True: "V", False: "F"})

    for col in ["Valor diárias", "Valor passagens", "Valor outros gastos", "Valor devolução"]:
        work[col] = decimal_series(work[col])

    work["Identificador do processo de viagem"] = pd.to_numeric(
        work["Identificador do processo de viagem"], errors="coerce"
    )
    work["Código órgão solicitante"] = pd.to_numeric(work["Código órgão solicitante"], errors="coerce")
    work["Código do órgão superior"] = pd.to_numeric(work["Código do órgão superior"], errors="coerce")
    work = work.dropna(
        subset=["Identificador do processo de viagem", "Código órgão solicitante", "Código do órgão superior"]
    )

    orgao_superior = (
        work[["Código do órgão superior", "Nome do órgão superior"]]
        .drop_duplicates(subset=["Código do órgão superior"])
        .rename(columns={
            "Código do órgão superior": "codigo_osup",
            "Nome do órgão superior": "nome_osup",
        })
    )
    orgao_superior["codigo_osup"] = orgao_superior["codigo_osup"].astype(int)
    orgao_superior["nome_osup"] = orgao_superior["nome_osup"].map(clean_text)

    orgao_solicitante = (
        work[["Código órgão solicitante", "Nome órgão solicitante", "Código do órgão superior"]]
        .drop_duplicates(subset=["Código órgão solicitante"])
        .rename(columns={
            "Código órgão solicitante": "codigo_osol",
            "Nome órgão solicitante": "nome_osol",
            "Código do órgão superior": "orgao_superior_codigo_osup",
        })
    )
    orgao_solicitante["codigo_osol"] = orgao_solicitante["codigo_osol"].astype(int)
    orgao_solicitante["orgao_superior_codigo_osup"] = orgao_solicitante["orgao_superior_codigo_osup"].astype(int)
    orgao_solicitante["nome_osol"] = orgao_solicitante["nome_osol"].map(clean_text)

    servidor = (
        work[["cpf_artificial", "Nome", "Cargo"]]
        .drop_duplicates(subset=["cpf_artificial"])
        .rename(columns={"cpf_artificial": "cpf", "Nome": "nome_completo", "Cargo": "cargo"})
    )
    servidor["nome_completo"] = servidor["nome_completo"].map(clean_text)
    servidor["cargo"] = servidor["cargo"].where(servidor["cargo"].notna(), None)

    viagem = (
        work[[
            "Identificador do processo de viagem",
            "urgencia",
            "Motivo",
            "Valor diárias",
            "Valor passagens",
            "Valor outros gastos",
            "Valor devolução",
            "cpf_artificial",
            "Código órgão solicitante",
        ]]
        .drop_duplicates(subset=["Identificador do processo de viagem"])
        .rename(columns={
            "Identificador do processo de viagem": "id_viagem",
            "Motivo": "motivo",
            "Valor diárias": "valor_diarias",
            "Valor passagens": "valor_passagem",
            "Valor outros gastos": "valor_outros",
            "Valor devolução": "valor_devolvido",
            "cpf_artificial": "servidor_cpf",
            "Código órgão solicitante": "orgao_solicitante_codigo_osol",
        })
    )
    viagem["id_viagem"] = viagem["id_viagem"].astype(int)
    viagem["orgao_solicitante_codigo_osol"] = viagem["orgao_solicitante_codigo_osol"].astype(int)
    viagem["motivo"] = viagem["motivo"].where(viagem["motivo"].notna(), None)

    orgao_superior.to_csv(out_dir / "orgao_superior_final.csv", sep=";", index=False, encoding="utf-8")
    orgao_solicitante.to_csv(out_dir / "orgao_solicitante_final.csv", sep=";", index=False, encoding="utf-8")
    servidor.to_csv(out_dir / "servidor_final.csv", sep=";", index=False, encoding="utf-8")
    viagem.to_csv(out_dir / "viagem_final.csv", sep=";", index=False, encoding="utf-8")


def transform_segments(df: pd.DataFrame, out_dir: Path) -> None:
    require_columns(df, SEGMENT_REQUIRED, "segment CSV")
    work = df.copy()

    # Normalize geography values before building deterministic surrogate IDs.
    for col in ["Origem - Cidade", "Origem - País", "Destino - Cidade", "Destino - País"]:
        work[col] = work[col].map(clean_text)
    for col in ["Origem - UF", "Destino - UF"]:
        work[col] = work[col].fillna("").astype(str).str.strip()

    country_values = sorted(set(work["Origem - País"]) | set(work["Destino - País"]))
    country_map = {name: idx for idx, name in enumerate(country_values, start=10)}

    uf_pairs = sorted({
        (country, uf)
        for country_col, uf_col in [("Origem - País", "Origem - UF"), ("Destino - País", "Destino - UF")]
        for country, uf in zip(work[country_col], work[uf_col])
        if uf
    })
    uf_map = {pair: idx for idx, pair in enumerate(uf_pairs, start=1000)}

    city_keys = sorted({
        (country, uf, city)
        for country_col, uf_col, city_col in [
            ("Origem - País", "Origem - UF", "Origem - Cidade"),
            ("Destino - País", "Destino - UF", "Destino - Cidade"),
        ]
        for country, uf, city in zip(work[country_col], work[uf_col], work[city_col])
    })
    city_map = {key: idx for idx, key in enumerate(city_keys, start=100000)}

    work["id_pais_origem"] = work["Origem - País"].map(country_map)
    work["id_pais_destino"] = work["Destino - País"].map(country_map)
    work["id_uf_origem"] = [uf_map.get((country, uf)) if uf else None for country, uf in zip(work["Origem - País"], work["Origem - UF"])]
    work["id_uf_destino"] = [uf_map.get((country, uf)) if uf else None for country, uf in zip(work["Destino - País"], work["Destino - UF"])]
    work["id_cidade_origem"] = [city_map[(country, uf, city)] for country, uf, city in zip(work["Origem - País"], work["Origem - UF"], work["Origem - Cidade"])]
    work["id_cidade_destino"] = [city_map[(country, uf, city)] for country, uf, city in zip(work["Destino - País"], work["Destino - UF"], work["Destino - Cidade"])]

    pais = pd.DataFrame(
        [{"id_pais": country_map[name], "nome_pais": name} for name in country_values]
    )
    uf = pd.DataFrame([
        {"id_uf": uf_map[(country, uf_name)], "nome_uf": uf_name, "pais_id_pais": country_map[country]}
        for country, uf_name in uf_pairs
    ])
    cidade = pd.DataFrame([
        {
            "id_cidade": city_map[(country, uf_name, city)],
            "nome_cidade": city,
            "pais_id_pais": country_map[country],
            "uf_id_uf": uf_map.get((country, uf_name)) if uf_name else None,
        }
        for country, uf_name, city in city_keys
    ])
    if not cidade.empty:
        cidade["uf_id_uf"] = cidade["uf_id_uf"].astype("Int64")

    work["seq_trecho"] = pd.to_numeric(work["Sequência Trecho"], errors="coerce")
    work["num_diarias"] = decimal_series(work["Número Diárias"])
    work["missao"] = work["Missao?"].fillna("").astype(str).str.strip().str.upper().eq("SIM").map({True: "V", False: "F"})
    work["data_origem"] = date_series(work["Origem - Data"])
    work["data_destino"] = date_series(work["Destino - Data"])
    work["viagem_id_viagem"] = pd.to_numeric(work["Identificador do processo de viagem"], errors="coerce")

    trecho = pd.DataFrame({
        "seq_trecho": work["seq_trecho"],
        "meio_trasporte": work["Meio de transporte"].map(clean_text),
        "num_diarias": work["num_diarias"],
        "missao": work["missao"],
        "data_origem": work["data_origem"],
        "data_destino": work["data_destino"],
        "cidade_origem": work["id_cidade_origem"],
        "cidade_destino": work["id_cidade_destino"],
        "viagem_id_viagem": work["viagem_id_viagem"],
    }).dropna(subset=["seq_trecho", "data_origem", "data_destino", "viagem_id_viagem"])

    trecho["seq_trecho"] = trecho["seq_trecho"].astype(int)
    trecho["viagem_id_viagem"] = trecho["viagem_id_viagem"].astype(int)

    pais.to_csv(out_dir / "pais_final.csv", sep=";", index=False, encoding="utf-8")
    uf.to_csv(out_dir / "uf_final.csv", sep=";", index=False, encoding="utf-8")
    cidade.to_csv(out_dir / "cidade_final.csv", sep=";", index=False, encoding="utf-8")
    trecho.to_csv(out_dir / "trecho_final.csv", sep=";", index=False, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize 2024 government travel CSV exports.")
    parser.add_argument("--travel", type=Path, default=Path("data/raw/2024_Viagem.csv"))
    parser.add_argument("--segments", type=Path, default=Path("data/raw/2024_Trecho.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    travel_df = read_portal_csv(args.travel)
    segment_df = read_portal_csv(args.segments)

    transform_travel(travel_df, args.output_dir)
    transform_segments(segment_df, args.output_dir)

    print(f"Generated normalized CSV tables in: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
