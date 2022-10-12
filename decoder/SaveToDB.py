#!/usr/bin/env python
# coding: utf-8

# # Version 1.0 - 2022-10-12
# - ) Adapted from Node Red version

import mysql.connector
from mysql.connector.errors import ProgrammingError
from mysql.connector import errorcode
import os
import logging
from datetime import datetime


def connectToDB():
    '''Connect to the Database'''
    _conn = mysql.connector.connect(
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT')
    )

    # Get Cursor
    _cur = _conn.cursor(dictionary=True)

    return _conn, _cur


def CreateSchema(schemaName):

    try:
        conn, cur = connectToDB()

        sqlStr = f"""CREATE DATABASE `{schemaName}`;"""

        cur.execute(sqlStr)
        conn.commit()

    finally:
        try:
            conn
            if conn is not None:
                conn.close()
        except:
            pass


def CreateTable(dataDict, schemaName, tblName):
    try:
        conn, cur = connectToDB()

        sqlStr = f"""CREATE TABLE `{schemaName}`.`{tblName}` (
                    `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
                    `timestamp` int(10) unsigned NOT NULL DEFAULT 0,
                    `WIn` int(10) unsigned NOT NULL DEFAULT 0,
                    `WOut` int(10) unsigned NOT NULL DEFAULT 0,
                    `PIn` double unsigned NOT NULL DEFAULT 0,
                    `POut` double unsigned NOT NULL DEFAULT 0,
                    `U1` double unsigned NOT NULL DEFAULT 0,
                    `U2` double unsigned NOT NULL DEFAULT 0,
                    `U3` double unsigned NOT NULL DEFAULT 0,
                    `I1` double unsigned NOT NULL DEFAULT 0,
                    `I2` double unsigned NOT NULL DEFAULT 0,
                    `I3` double unsigned NOT NULL DEFAULT 0,
                    `PF` double NOT NULL DEFAULT 0,
                    PRIMARY KEY (`id`,`timestamp`),
                    UNIQUE KEY `id_UNIQUE` (`id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"""

        cur.execute(sqlStr)
        conn.commit()

    except ProgrammingError as pe:
        if errorcode.ER_BAD_DB_ERROR == pe.errno:  # Exception if the schema does not exist
            logging.warning("ER_BAD_DB_ERROR")
            CreateSchema(schemaName)
            CreateTable(dataDict, schemaName, tblName)
            SaveToDB(dataDict, schemaName, tblName)

    finally:
        try:
            conn
            if conn is not None:
                conn.close()
        except:
            pass


def SaveToDB(dataDict, schemaName, tblName):
    '''Save data to the DB'''

    # Check if all values are here
    requiredKeys = ['WIn',
                    'WOut',
                    'PIn',
                    'POut',
                    'U1',
                    'U2',
                    'U3',
                    'I1',
                    'I2',
                    'I3',
                    'PF']

    for rk in requiredKeys:
        if not rk in dataDict.keys():
            logging.warning(
                f"At {datetime.fromtimestamp(dataDict['timestamp']['value'])} the key '{rk}' was not in dataDict, not storing.")
            return

    try:
        conn, cur = connectToDB()

        sqlStr = f"""INSERT INTO
                    `{schemaName}`.`{tblName}` (
                        `timestamp`,
                        `WIn`,
                        `WOut`,
                        `PIn`,
                        `POut`,
                        `U1`,
                        `U2`,
                        `U3`,
                        `I1`,
                        `I2`,
                        `I3`,
                        `PF`
                    )
                    VALUES (
                        {dataDict['timestamp']['value']},
                        {dataDict['WIn']['value']},
                        {dataDict['WOut']['value']},
                        {dataDict['PIn']['value']},
                        {dataDict['POut']['value']},
                        {dataDict['U1']['value']},
                        {dataDict['U2']['value']},
                        {dataDict['U3']['value']},
                        {dataDict['I1']['value']},
                        {dataDict['I2']['value']},
                        {dataDict['I3']['value']},
                        {dataDict['PF']['value']}
                    );
                    """

        cur.execute(sqlStr)
        conn.commit()

    except ProgrammingError as pe:
        if errorcode.ER_NO_SUCH_TABLE == pe.errno:  # Exception if the table does not exist
            logging.warning("ER_NO_SUCH_TABLE")
            CreateTable(dataDict, schemaName, tblName)
            SaveToDB(dataDict, schemaName, tblName)

    finally:
        try:
            conn
            if conn is not None:
                conn.close()
        except:
            pass
