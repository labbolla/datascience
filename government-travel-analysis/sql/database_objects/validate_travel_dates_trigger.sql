-- Prevents insertion of a travel leg whose departure date is after its arrival date.
USE `projeto_fbd`;

DROP TRIGGER IF EXISTS `BeforeInsertTrecho`;

DELIMITER $$
CREATE TRIGGER `BeforeInsertTrecho`
BEFORE INSERT ON `trecho`
FOR EACH ROW
BEGIN
    IF NEW.data_origem > NEW.data_destino THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Erro: A data de origem nao pode ser posterior a data de destino';
    END IF;
END $$
DELIMITER ;
