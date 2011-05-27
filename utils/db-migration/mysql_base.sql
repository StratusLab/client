-- Host: localhost    Database: opennebula
-- ------------------------------------------------------
-- Server version	5.5.9

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `cluster_pool`
--

DROP TABLE IF EXISTS `cluster_pool`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `cluster_pool` (
  `oid` int(11) NOT NULL,
  `cluster_name` varchar(128) DEFAULT NULL,
  PRIMARY KEY (`oid`),
  UNIQUE KEY `cluster_name` (`cluster_name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cluster_pool`
--

LOCK TABLES `cluster_pool` WRITE;
/*!40000 ALTER TABLE `cluster_pool` DISABLE KEYS */;
/*!40000 ALTER TABLE `cluster_pool` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `history`
--

DROP TABLE IF EXISTS `history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `history` (
  `vid` int(11) NOT NULL DEFAULT '0',
  `seq` int(11) NOT NULL DEFAULT '0',
  `host_name` text,
  `vm_dir` text,
  `hid` int(11) DEFAULT NULL,
  `vm_mad` text,
  `tm_mad` text,
  `stime` int(11) DEFAULT NULL,
  `etime` int(11) DEFAULT NULL,
  `pstime` int(11) DEFAULT NULL,
  `petime` int(11) DEFAULT NULL,
  `rstime` int(11) DEFAULT NULL,
  `retime` int(11) DEFAULT NULL,
  `estime` int(11) DEFAULT NULL,
  `eetime` int(11) DEFAULT NULL,
  `reason` int(11) DEFAULT NULL,
  PRIMARY KEY (`vid`,`seq`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `history`
--

LOCK TABLES `history` WRITE;
/*!40000 ALTER TABLE `history` DISABLE KEYS */;
/*!40000 ALTER TABLE `history` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `host_pool`
--

DROP TABLE IF EXISTS `host_pool`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `host_pool` (
  `oid` int(11) NOT NULL,
  `host_name` varchar(256) DEFAULT NULL,
  `state` int(11) DEFAULT NULL,
  `im_mad` varchar(128) DEFAULT NULL,
  `vm_mad` varchar(128) DEFAULT NULL,
  `tm_mad` varchar(128) DEFAULT NULL,
  `last_mon_time` int(11) DEFAULT NULL,
  `cluster` varchar(128) DEFAULT NULL,
  `template` text,
  PRIMARY KEY (`oid`),
  UNIQUE KEY `host_name` (`host_name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `host_pool`
--

LOCK TABLES `host_pool` WRITE;
/*!40000 ALTER TABLE `host_pool` DISABLE KEYS */;
/*!40000 ALTER TABLE `host_pool` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `host_shares`
--

DROP TABLE IF EXISTS `host_shares`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `host_shares` (
  `hid` int(11) NOT NULL,
  `disk_usage` int(11) DEFAULT NULL,
  `mem_usage` int(11) DEFAULT NULL,
  `cpu_usage` int(11) DEFAULT NULL,
  `max_disk` int(11) DEFAULT NULL,
  `max_mem` int(11) DEFAULT NULL,
  `max_cpu` int(11) DEFAULT NULL,
  `free_disk` int(11) DEFAULT NULL,
  `free_mem` int(11) DEFAULT NULL,
  `free_cpu` int(11) DEFAULT NULL,
  `used_disk` int(11) DEFAULT NULL,
  `used_mem` int(11) DEFAULT NULL,
  `used_cpu` int(11) DEFAULT NULL,
  `running_vms` int(11) DEFAULT NULL,
  PRIMARY KEY (`hid`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `host_shares`
--

LOCK TABLES `host_shares` WRITE;
/*!40000 ALTER TABLE `host_shares` DISABLE KEYS */;
/*!40000 ALTER TABLE `host_shares` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `image_pool`
--

DROP TABLE IF EXISTS `image_pool`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `image_pool` (
  `oid` int(11) NOT NULL,
  `uid` int(11) DEFAULT NULL,
  `name` varchar(128) DEFAULT NULL,
  `type` int(11) DEFAULT NULL,
  `public` int(11) DEFAULT NULL,
  `persistent` int(11) DEFAULT NULL,
  `regtime` int(11) DEFAULT NULL,
  `source` text,
  `state` int(11) DEFAULT NULL,
  `running_vms` int(11) DEFAULT NULL,
  `template` text,
  PRIMARY KEY (`oid`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `image_pool`
--

LOCK TABLES `image_pool` WRITE;
/*!40000 ALTER TABLE `image_pool` DISABLE KEYS */;
/*!40000 ALTER TABLE `image_pool` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `leases`
--

DROP TABLE IF EXISTS `leases`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `leases` (
  `oid` int(11) NOT NULL DEFAULT '0',
  `ip` bigint(20) NOT NULL DEFAULT '0',
  `mac_prefix` bigint(20) DEFAULT NULL,
  `mac_suffix` bigint(20) DEFAULT NULL,
  `vid` int(11) DEFAULT NULL,
  `used` int(11) DEFAULT NULL,
  PRIMARY KEY (`oid`,`ip`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `leases`
--

LOCK TABLES `leases` WRITE;
/*!40000 ALTER TABLE `leases` DISABLE KEYS */;
/*!40000 ALTER TABLE `leases` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `network_pool`
--

DROP TABLE IF EXISTS `network_pool`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `network_pool` (
  `oid` int(11) NOT NULL,
  `uid` int(11) DEFAULT NULL,
  `name` varchar(256) DEFAULT NULL,
  `type` int(11) DEFAULT NULL,
  `bridge` text,
  `public` int(11) DEFAULT NULL,
  `template` text,
  PRIMARY KEY (`oid`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `network_pool`
--

LOCK TABLES `network_pool` WRITE;
/*!40000 ALTER TABLE `network_pool` DISABLE KEYS */;
/*!40000 ALTER TABLE `network_pool` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_pool`
--

DROP TABLE IF EXISTS `user_pool`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_pool` (
  `oid` int(11) NOT NULL,
  `user_name` varchar(256) DEFAULT NULL,
  `password` text,
  `enabled` int(11) DEFAULT NULL,
  PRIMARY KEY (`oid`),
  UNIQUE KEY `user_name` (`user_name`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_pool`
--

LOCK TABLES `user_pool` WRITE;
/*!40000 ALTER TABLE `user_pool` DISABLE KEYS */;
/*!40000 ALTER TABLE `user_pool` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `vm_pool`
--

DROP TABLE IF EXISTS `vm_pool`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `vm_pool` (
  `oid` int(11) NOT NULL,
  `uid` int(11) DEFAULT NULL,
  `name` text,
  `last_poll` int(11) DEFAULT NULL,
  `state` int(11) DEFAULT NULL,
  `lcm_state` int(11) DEFAULT NULL,
  `stime` int(11) DEFAULT NULL,
  `etime` int(11) DEFAULT NULL,
  `deploy_id` text,
  `memory` int(11) DEFAULT NULL,
  `cpu` int(11) DEFAULT NULL,
  `net_tx` int(11) DEFAULT NULL,
  `net_rx` int(11) DEFAULT NULL,
  `last_seq` int(11) DEFAULT NULL,
  `template` text,
  PRIMARY KEY (`oid`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `vm_pool`
--

LOCK TABLES `vm_pool` WRITE;
/*!40000 ALTER TABLE `vm_pool` DISABLE KEYS */;
/*!40000 ALTER TABLE `vm_pool` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
