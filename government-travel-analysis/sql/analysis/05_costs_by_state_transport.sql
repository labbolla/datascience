-- Ticket costs by final destination UF plus the three most frequent transport modes
-- among all legs ending in each UF.
-- Trip-level ticket cost is counted once using the final destination of each trip.
USE `projeto_fbd`;

SELECT
    u.nome_uf,
    COUNT(*) AS total_viagens,
    ROUND(SUM(fd.valor_passagem), 2) AS total_custos_passagens,

    (SELECT t1.meio_trasporte
     FROM trecho t1
     JOIN cidade c1 ON c1.id_cidade = t1.cidade_destino
     WHERE c1.uf_id_uf = u.id_uf
     GROUP BY t1.meio_trasporte
     ORDER BY COUNT(*) DESC, t1.meio_trasporte
     LIMIT 1) AS top_meio_1,

    (SELECT t2.meio_trasporte
     FROM trecho t2
     JOIN cidade c2 ON c2.id_cidade = t2.cidade_destino
     WHERE c2.uf_id_uf = u.id_uf
     GROUP BY t2.meio_trasporte
     ORDER BY COUNT(*) DESC, t2.meio_trasporte
     LIMIT 1 OFFSET 1) AS top_meio_2,

    (SELECT t3.meio_trasporte
     FROM trecho t3
     JOIN cidade c3 ON c3.id_cidade = t3.cidade_destino
     WHERE c3.uf_id_uf = u.id_uf
     GROUP BY t3.meio_trasporte
     ORDER BY COUNT(*) DESC, t3.meio_trasporte
     LIMIT 1 OFFSET 2) AS top_meio_3
FROM uf u
JOIN (
    SELECT
        c.uf_id_uf,
        v.id_viagem,
        v.valor_passagem
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
    WHERE c.uf_id_uf IS NOT NULL
) fd ON fd.uf_id_uf = u.id_uf
GROUP BY u.id_uf, u.nome_uf
ORDER BY total_custos_passagens DESC;
