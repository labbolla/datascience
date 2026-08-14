-- Compact one-row-per-trip view with first/last leg, organization and net cost.
USE `projeto_fbd`;

DROP VIEW IF EXISTS `view_viagem_custo`;

CREATE VIEW `view_viagem_custo` AS
SELECT
    v.id_viagem,
    t_first.data_origem AS data_inicio,
    t_last.data_destino AS data_final,
    c_start.nome_cidade AS cidade_inicio,
    c_end.nome_cidade AS cidade_final,
    osup.nome_osup AS orgao_superior,
    rs.total_trechos,
    rs.total_num_diarias,
    (v.valor_diarias + v.valor_passagem + v.valor_outros - v.valor_devolvido) AS custo_total
FROM viagem v
JOIN (
    SELECT
        viagem_id_viagem,
        MIN(seq_trecho) AS first_seq,
        MAX(seq_trecho) AS last_seq,
        COUNT(*) AS total_trechos,
        SUM(num_diarias) AS total_num_diarias
    FROM trecho
    GROUP BY viagem_id_viagem
) rs ON rs.viagem_id_viagem = v.id_viagem
JOIN trecho t_first
  ON t_first.viagem_id_viagem = v.id_viagem
 AND t_first.seq_trecho = rs.first_seq
JOIN trecho t_last
  ON t_last.viagem_id_viagem = v.id_viagem
 AND t_last.seq_trecho = rs.last_seq
JOIN cidade c_start ON c_start.id_cidade = t_first.cidade_origem
JOIN cidade c_end ON c_end.id_cidade = t_last.cidade_destino
JOIN orgao_solicitante osol
  ON osol.codigo_osol = v.orgao_solicitante_codigo_osol
JOIN orgao_superior osup
  ON osup.codigo_osup = osol.orgao_superior_codigo_osup;
