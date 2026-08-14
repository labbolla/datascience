-- Government Travel Analysis
-- Cleaned SQL schema reconstructed from the final MySQL Workbench model.
-- Target: MySQL 5.7+

CREATE SCHEMA IF NOT EXISTS `projeto_fbd` DEFAULT CHARACTER SET latin1;
USE `projeto_fbd`;

CREATE TABLE IF NOT EXISTS `pais` (
  `id_pais` INT(11) NOT NULL,
  `nome_pais` VARCHAR(45) NOT NULL,
  PRIMARY KEY (`id_pais`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `uf` (
  `id_uf` INT(11) NOT NULL,
  `nome_uf` VARCHAR(45) NOT NULL,
  `pais_id_pais` INT(11) NOT NULL,
  PRIMARY KEY (`id_uf`),
  INDEX `fk_uf_pais1_idx` (`pais_id_pais` ASC),
  CONSTRAINT `fk_uf_pais1`
    FOREIGN KEY (`pais_id_pais`)
    REFERENCES `pais` (`id_pais`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `cidade` (
  `id_cidade` INT(11) NOT NULL,
  `nome_cidade` VARCHAR(45) NOT NULL,
  `pais_id_pais` INT(11) NOT NULL,
  `uf_id_uf` INT(11) NULL DEFAULT NULL,
  PRIMARY KEY (`id_cidade`),
  INDEX `fk_cidade_pais1_idx` (`pais_id_pais` ASC),
  INDEX `fk_cidade_uf1_idx` (`uf_id_uf` ASC),
  CONSTRAINT `fk_cidade_pais1`
    FOREIGN KEY (`pais_id_pais`)
    REFERENCES `pais` (`id_pais`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_cidade_uf1`
    FOREIGN KEY (`uf_id_uf`)
    REFERENCES `uf` (`id_uf`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `orgao_superior` (
  `codigo_osup` INT(11) NOT NULL,
  `nome_osup` VARCHAR(61) NOT NULL,
  PRIMARY KEY (`codigo_osup`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `orgao_solicitante` (
  `codigo_osol` INT(11) NOT NULL,
  `nome_osol` VARCHAR(76) NOT NULL,
  `orgao_superior_codigo_osup` INT(11) NOT NULL,
  PRIMARY KEY (`codigo_osol`),
  INDEX `fk_orgao_solicitante_orgao_superior_idx` (`orgao_superior_codigo_osup` ASC),
  CONSTRAINT `fk_orgao_solicitante_orgao_superior`
    FOREIGN KEY (`orgao_superior_codigo_osup`)
    REFERENCES `orgao_superior` (`codigo_osup`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `servidor` (
  `cpf` VARCHAR(20) NOT NULL,
  `nome_completo` VARCHAR(60) NOT NULL,
  `cargo` VARCHAR(50) NULL DEFAULT NULL,
  PRIMARY KEY (`cpf`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `viagem` (
  `id_viagem` INT(11) NOT NULL,
  `urgencia` CHAR(1) NOT NULL,
  `motivo` TEXT NULL DEFAULT NULL,
  `valor_diarias` DECIMAL(10,2) NOT NULL,
  `valor_passagem` DECIMAL(10,2) NOT NULL,
  `valor_outros` DECIMAL(10,2) NOT NULL,
  `valor_devolvido` DECIMAL(10,2) NOT NULL,
  `servidor_cpf` VARCHAR(20) NOT NULL,
  `orgao_solicitante_codigo_osol` INT(11) NOT NULL,
  PRIMARY KEY (`id_viagem`),
  INDEX `fk_viagem_servidor1_idx` (`servidor_cpf` ASC),
  INDEX `fk_viagem_orgao_solicitante1_idx` (`orgao_solicitante_codigo_osol` ASC),
  CONSTRAINT `fk_viagem_servidor1`
    FOREIGN KEY (`servidor_cpf`)
    REFERENCES `servidor` (`cpf`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_viagem_orgao_solicitante1`
    FOREIGN KEY (`orgao_solicitante_codigo_osol`)
    REFERENCES `orgao_solicitante` (`codigo_osol`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `trecho` (
  `seq_trecho` INT(3) NOT NULL,
  `meio_trasporte` VARCHAR(45) NOT NULL,
  `num_diarias` DECIMAL(10,2) NOT NULL,
  `missao` CHAR(1) NOT NULL,
  `data_origem` DATE NOT NULL,
  `data_destino` DATE NOT NULL,
  `cidade_origem` INT(11) NOT NULL,
  `cidade_destino` INT(11) NOT NULL,
  `viagem_id_viagem` INT(11) NOT NULL,
  PRIMARY KEY (`seq_trecho`, `viagem_id_viagem`),
  INDEX `fk_trecho_viagem1_idx` (`viagem_id_viagem` ASC),
  INDEX `fk_trecho_cidade_origem_idx` (`cidade_origem` ASC),
  INDEX `fk_trecho_cidade_destino_idx` (`cidade_destino` ASC),
  CONSTRAINT `fk_trecho_cidade_origem`
    FOREIGN KEY (`cidade_origem`)
    REFERENCES `cidade` (`id_cidade`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_trecho_cidade_destino`
    FOREIGN KEY (`cidade_destino`)
    REFERENCES `cidade` (`id_cidade`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_trecho_viagem1`
    FOREIGN KEY (`viagem_id_viagem`)
    REFERENCES `viagem` (`id_viagem`)
    ON DELETE CASCADE
    ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
