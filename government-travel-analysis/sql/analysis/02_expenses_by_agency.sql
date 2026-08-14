-- Total and average travel expenses by superior government agency.
USE `projeto_fbd`;

SELECT
    osup.nome_osup AS nome_orgao_superior,
    COUNT(v.id_viagem) AS total_viagens,
    ROUND(SUM(v.valor_diarias + v.valor_passagem + v.valor_outros - v.valor_devolvido), 2)
        AS total_custos_liquidos,
    ROUND(AVG(v.valor_diarias + v.valor_passagem + v.valor_outros - v.valor_devolvido), 2)
        AS media_custo_viagem,
    SUM(CASE WHEN v.urgencia = 'V' THEN 1 ELSE 0 END) AS viagens_urgentes,
    ROUND(
        100.0 * SUM(CASE WHEN v.urgencia = 'V' THEN 1 ELSE 0 END) / NULLIF(COUNT(v.id_viagem), 0),
        2
    ) AS percentual_viagens_urgentes
FROM orgao_superior osup
JOIN orgao_solicitante osol
  ON osol.orgao_superior_codigo_osup = osup.codigo_osup
JOIN viagem v
  ON v.orgao_solicitante_codigo_osol = osol.codigo_osol
GROUP BY osup.codigo_osup, osup.nome_osup
ORDER BY total_custos_liquidos DESC;
