DROP TABLE IF EXISTS `candidates`, `info`, `jobs`;
CREATE TABLE IF NOT EXISTS `candidates` (`pol_station_code` varchar(15) DEFAULT NULL,`id` varchar(15) NOT NULL,`name` varchar(255) DEFAULT NULL,`sex` char(1) DEFAULT NULL,`age` char(3) DEFAULT NULL,`picture` varchar(15) DEFAULT NULL) ENGINE=InnoDB DEFAULT CHARSET=latin1;
CREATE TABLE IF NOT EXISTS `info` (`pol_code` varchar(15) NOT NULL,`pol_name` varchar(255) DEFAULT NULL,`constituency` varchar(255) DEFAULT NULL,`district` varchar(255) DEFAULT NULL,`region` varchar(255) DEFAULT NULL,`count_on_pdf` varchar(6) DEFAULT NULL,`total_records` int(11) DEFAULT NULL) ENGINE=InnoDB DEFAULT CHARSET=latin1;
CREATE TABLE IF NOT EXISTS `jobs` (`id` int(25) NOT NULL,`file_name` varchar(250) NOT NULL,`status` int(1) NOT NULL DEFAULT '1',`notes` int(11) DEFAULT NULL) ENGINE=InnoDB DEFAULT CHARSET=latin1;
ALTER TABLE `candidates` ADD PRIMARY KEY (`id`);
ALTER TABLE `info` ADD PRIMARY KEY (`pol_code`);
ALTER TABLE `jobs` ADD PRIMARY KEY (`id`), ADD UNIQUE KEY `file_name` (`file_name`);
ALTER TABLE `jobs` MODIFY `id` int(25) NOT NULL AUTO_INCREMENT;
COMMIT;