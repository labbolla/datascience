-- Stored procedure: retrieves one or more trips and calculates their net total cost.
USE `projeto_fbd`;

DROP PROCEDURE IF EXISTS `CalcularCustoViagemTemp`;

DELIMITER $$
CREATE PROCEDURE `CalcularCustoViagemTemp`(
    IN p_id_viagem_list TEXT
)
BEGIN
    DROP TEMPORARY TABLE IF EXISTS TempViagemCusto;

    CREATE TEMPORARY TABLE TempViagemCusto (
        id_viagem INT,
        nome_completo VARCHAR(60),
        nome_osol VARCHAR(76),
        valor_diarias DECIMAL(10,2),
        valor_passagem DECIMAL(10,2),
        valor_outros DECIMAL(10,2),
        valor_devolvido DECIMAL(10,2),
        valor_total DECIMAL(10,2)
    );

    INSERT INTO TempViagemCusto (
        id_viagem,
        nome_completo,
        nome_osol,
        valor_diarias,
        valor_passagem,
        valor_outros,
        valor_devolvido,
        valor_total
    )
    SELECT
        v.id_viagem,
        s.nome_completo,
        osol.nome_osol,
        v.valor_diarias,
        v.valor_passagem,
        v.valor_outros,
        v.valor_devolvido,
        (v.valor_diarias + v.valor_passagem + v.valor_outros - v.valor_devolvido) AS valor_total
    FROM viagem v
    JOIN servidor s ON s.cpf = v.servidor_cpf
    JOIN orgao_solicitante osol
      ON osol.codigo_osol = v.orgao_solicitante_codigo_osol
    WHERE p_id_viagem_list IS NULL
       OR TRIM(p_id_viagem_list) = ''
       OR FIND_IN_SET(CAST(v.id_viagem AS CHAR), REPLACE(p_id_viagem_list, ' ', '')) > 0;

    SELECT * FROM TempViagemCusto ORDER BY id_viagem;
END $$
DELIMITER ;
