-- SQL implementation of one of the relational-algebra exercises in the report:
-- employees who did not make any international trip.
USE `projeto_fbd`;

SELECT s.nome_completo
FROM servidor s
WHERE NOT EXISTS (
    SELECT 1
    FROM viagem v
    JOIN trecho t ON t.viagem_id_viagem = v.id_viagem
    JOIN cidade c ON c.id_cidade = t.cidade_destino
    WHERE v.servidor_cpf = s.cpf
      AND c.uf_id_uf IS NULL
);
