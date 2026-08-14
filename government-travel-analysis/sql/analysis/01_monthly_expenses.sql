-- Distribution of travel expenses by month in 2024.
-- Trip-level costs are allocated equally across their legs to avoid multiplying
-- the same trip cost when a trip contains multiple rows in `trecho`.
USE `projeto_fbd`;

SELECT
    DATE_FORMAT(t.data_origem, '%Y-%m') AS mes_ano,
    COUNT(*) AS total_trechos,
    ROUND(SUM(v.valor_passagem / tc.total_trechos)
        + SUM(v.valor_diarias / tc.total_trechos)
        + SUM(v.valor_outros / tc.total_trechos)
        - SUM(v.valor_devolvido / tc.total_trechos), 2) AS total_custos,
    ROUND(SUM(v.valor_passagem / tc.total_trechos), 2) AS total_valor_passagem,
    ROUND(SUM(v.valor_diarias / tc.total_trechos), 2) AS total_valor_diarias,
    ROUND(SUM(v.valor_outros / tc.total_trechos), 2) AS total_valor_outros,
    ROUND(SUM(v.valor_devolvido / tc.total_trechos), 2) AS total_valor_devolvido,
    ROUND(
        100 * SUM(v.valor_passagem / tc.total_trechos) /
        NULLIF(SUM((v.valor_passagem + v.valor_diarias + v.valor_outros) / tc.total_trechos), 0),
        2
    ) AS perc_passagem_mes,
    ROUND(
        100 * SUM(v.valor_diarias / tc.total_trechos) /
        NULLIF(SUM((v.valor_passagem + v.valor_diarias + v.valor_outros) / tc.total_trechos), 0),
        2
    ) AS perc_diarias_mes,
    ROUND(
        100 * SUM(v.valor_outros / tc.total_trechos) /
        NULLIF(SUM((v.valor_passagem + v.valor_diarias + v.valor_outros) / tc.total_trechos), 0),
        2
    ) AS perc_outros_mes
FROM trecho t
JOIN viagem v ON v.id_viagem = t.viagem_id_viagem
JOIN (
    SELECT viagem_id_viagem, COUNT(*) AS total_trechos
    FROM trecho
    GROUP BY viagem_id_viagem
) tc ON tc.viagem_id_viagem = t.viagem_id_viagem
WHERE YEAR(t.data_origem) = 2024
GROUP BY DATE_FORMAT(t.data_origem, '%Y-%m')
ORDER BY total_custos DESC;
