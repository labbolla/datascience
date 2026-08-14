-- Trip costs by final destination country.
-- Each trip is attributed once, to the destination of its last leg, so trip-level
-- costs are not duplicated across multiple legs.
USE `projeto_fbd`;

SELECT
    p.nome_pais,
    COUNT(*) AS total_viagens,
    ROUND(SUM(v.valor_passagem + v.valor_diarias + v.valor_outros - v.valor_devolvido), 2)
        AS total_custos_liquidos,
    ROUND(AVG(v.valor_passagem + v.valor_diarias + v.valor_outros - v.valor_devolvido), 2)
        AS media_custos_liquidos,
    ROUND(AVG(v.valor_passagem), 2) AS media_passagem,
    ROUND(AVG(v.valor_diarias), 2) AS media_diarias
FROM viagem v
JOIN (
    SELECT viagem_id_viagem, MAX(seq_trecho) AS last_seq
    FROM trecho
    GROUP BY viagem_id_viagem
) ls ON ls.viagem_id_viagem = v.id_viagem
JOIN trecho t
  ON t.viagem_id_viagem = v.id_viagem
 AND t.seq_trecho = ls.last_seq
JOIN cidade c ON c.id_cidade = t.cidade_destino
JOIN pais p ON p.id_pais = c.pais_id_pais
GROUP BY p.id_pais, p.nome_pais
HAVING COUNT(*) > 9
ORDER BY media_custos_liquidos DESC;
