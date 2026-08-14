-- Travel allowances and travel profile by government employee.
-- `total_valor_liquido_diarias_outros` is intentionally named to make clear
-- that it includes daily allowances + other costs - returned amounts.
USE `projeto_fbd`;

SELECT
    s.cpf,
    s.nome_completo,
    s.cargo,
    COALESCE(vs.total_viagens, 0) AS total_viagens,
    COALESCE(vs.total_valor_diarias, 0) AS total_valor_diarias,
    COALESCE(vs.total_valor_liquido_diarias_outros, 0) AS total_valor_liquido_diarias_outros,
    COALESCE(ts.total_trechos, 0) AS total_trechos,
    COALESCE(ts.total_num_diarias, 0) AS total_num_diarias,
    COALESCE(ic.total_international_travels, 0) AS total_international_travels,
    COALESCE(vs.total_viagens, 0) - COALESCE(ic.total_international_travels, 0)
        AS total_national_travels
FROM servidor s
LEFT JOIN (
    SELECT
        servidor_cpf,
        COUNT(*) AS total_viagens,
        ROUND(SUM(valor_diarias), 2) AS total_valor_diarias,
        ROUND(SUM(valor_diarias + valor_outros - valor_devolvido), 2)
            AS total_valor_liquido_diarias_outros
    FROM viagem
    GROUP BY servidor_cpf
) vs ON vs.servidor_cpf = s.cpf
LEFT JOIN (
    SELECT
        v.servidor_cpf,
        COUNT(*) AS total_trechos,
        SUM(t.num_diarias) AS total_num_diarias
    FROM viagem v
    JOIN trecho t ON t.viagem_id_viagem = v.id_viagem
    GROUP BY v.servidor_cpf
) ts ON ts.servidor_cpf = s.cpf
LEFT JOIN (
    SELECT
        v.servidor_cpf,
        COUNT(DISTINCT v.id_viagem) AS total_international_travels
    FROM viagem v
    JOIN trecho t ON t.viagem_id_viagem = v.id_viagem
    JOIN cidade c ON c.id_cidade = t.cidade_destino
    WHERE c.uf_id_uf IS NULL
    GROUP BY v.servidor_cpf
) ic ON ic.servidor_cpf = s.cpf
ORDER BY total_valor_liquido_diarias_outros DESC, total_viagens DESC;
