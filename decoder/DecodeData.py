#!/usr/bin/env python
# coding: utf-8

# This algorithm is based on the work of https://github.com/ric-geek/DLMS-APDU-Encrypter-Decrypter
# It is extended by features for converting the raw hex values into readable power units

# # Version 1.0 - 2022-10-12
# - ) Adapted from Node Red version

from binascii import unhexlify
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

security_control_byte = ["30", "10"]
authentication_key = ""

init_stuff_len = 8
string_len = 24  # String is of len 24 ???
obis_len = 12
uint32_len = 8
uint16_len = 4
int16_len = 4
int8_len = 2
enum_len = 2

enum_lookup_dict = {
    "1e": "Wh",
    "1b": "W",
    "23": "V",
    "21": "A",
    "ff": "1"
}


def create_iv(self, frame_counter):
    '''This function create init vector'''
    return self.ui.txt_system_title.text() + frame_counter


def decryptADPU(key, systemTitle, frameCount, apdu):
    # Based on https://github.com/ric-geek/DLMS-APDU-Encrypter-Decrypter

    cipher_apdu = apdu.replace("\n", "").replace(
        " ", "")  # Remove newline and space
    string_chiper_apdu = unhexlify(cipher_apdu)
    encryption_key = unhexlify(key)

    # Create the AAD
    aad = unhexlify(security_control_byte[0] + authentication_key)

    # Create init vector
    init_vector = unhexlify(systemTitle + frameCount)

    # Decrypt
    aesgcm = AESGCM(encryption_key)
    apdu = aesgcm.encrypt(init_vector, string_chiper_apdu, aad)
    apdu_to_string = apdu.hex()

    decryptedDict = {
        "APDU": apdu_to_string[:-32],
        "TAG": apdu_to_string[-32:-8]
    }

    return decryptedDict


def extractString(pt, iLocal):
    extractedString = pt[iLocal:iLocal+string_len]
    iLocal += string_len

    return extractedString, iLocal


def twos_complement(hexstr, bits):
    value = int(hexstr, 16)
    if value & (1 << (bits-1)):
        value -= 1 << bits
    return value


def extractValues(pt):
    i = 0

    data = {}

    #data['apdu'] = pt
    data['extractedlist'] = []

    # First, get the initial stuff (len 8)

    data['init_stuff'] = pt[i:i+init_stuff_len]
    i = init_stuff_len

    # 12:00 bug: Dispose the starting strings, details see below
    i = 68

    dataframe = None

    while i < len(pt):
        data_type_slice = pt[i:i+6]

        # Todo: Bug, if the hour is 12:00 noon, then two strings are wrongly detected before the first OBIS value at "Starting 0906 at position 68"
        # Add in ProcessSmartmeter.py pt = {'APDU': '0f800713dc0c07e60a0b020c0c3700ff88820223090c07e60a0b020c0c3700ff888209060100010800ff060099862102020f00161e09060100020800ff06000000db02020f00161e09060100010700ff06000000b902020f00161b09060100020700ff060000000002020f00161b09060100200700ff12094002020fff162309060100340700ff12093102020fff162309060100480700ff12093402020fff1623090601001f0700ff12002102020ffe162109060100330700ff12003902020ffe162109060100470700ff12002b02020ffe1621090601000d0700ff10035f02020ffd16ff090c313738323e16c1b4676bc82e655ea5020c67237c1afcf5', 'TAG': '997beb4f12a21db08f1853d6'}
        if "0c" == data_type_slice[-2:].lower():  # String
            i += 4
            strData, i = extractString(pt, i)
            data['extractedlist'].append(strData)

        # OBIS-Desciptor / Entry into a dataframe
        elif "0906" == data_type_slice[:4].lower():
            i += 4

            # The dataframe start with the OBIS descriptor
            obis = pt[i:i+obis_len]
            i += obis_len

            obis_lookup_dict = {
                "0100010800ff": "WIn",
                "0100020800ff": "WOut",
                "0100010700ff": "PIn",
                "0100020700ff": "POut",
                "0100200700ff": "U1",
                "0100340700ff": "U2",
                "0100480700ff": "U3",
                "01001f0700ff": "I1",
                "0100330700ff": "I2",
                "0100470700ff": "I3",
                "01000d0700ff": "PF"
            }

            if obis in obis_lookup_dict.keys():
                obis = obis_lookup_dict[obis]
            else:
                obis = "Unknown " + str(obis)

            dataframe = {
                "obis": obis
            }

        # UINT32
        elif dataframe is not None and "06" == data_type_slice[:2].lower():
            i += 2
            uint32value = pt[i:i+uint32_len]
            i += uint32_len

            uint32value = int(uint32value, 16)

            dataframe["intvalue"] = uint32value

        # UINT16
        elif dataframe is not None and "12" == data_type_slice[:2].lower():
            i += 2
            uint16value = pt[i:i+uint16_len]
            i += uint16_len

            uint16value = int(uint16value, 16)

            dataframe["intvalue"] = uint16value

        # INT16 ?? - not sure, used at powerfactor
        elif dataframe is not None and "10" == data_type_slice[:2].lower():
            i += 2
            int16value = pt[i:i+int16_len]
            i += int16_len

            int16value = twos_complement(int16value, 16)

            dataframe["intvalue"] = int16value

        # INT8
        elif dataframe is not None and "02020f" == data_type_slice.lower():
            i += 6

            scaleExponent = pt[i:i+int8_len]
            i += int8_len

            scaleExponent = twos_complement(scaleExponent, 8)

            dataframe["scaleExponent"] = scaleExponent

        # Enum for value unit
        elif dataframe is not None and "16" == data_type_slice[:2].lower():
            i += 2

            enum = pt[i:i+enum_len]
            i += enum_len

            if enum in enum_lookup_dict.keys():
                enum = enum_lookup_dict[enum]
            else:
                enum = "Unknown " + str(enum)

            # Todo: convert to string
            dataframe["unit"] = enum

            # As the enum is the last element of the dataframe, a value conversion can be done
            if "intvalue" in dataframe and "scaleExponent" in dataframe:
                dataframe["floatValue"] = round(float(
                    dataframe["intvalue"]) * 10**dataframe["scaleExponent"], 3)

            data['extractedlist'].append(dataframe)
            dataframe = None

        else:
            i += 1

    # Convert into data dict
    dataDict = {}

    for df in data['extractedlist']:
        if 'obis' in df:
            dataDict[df['obis']] = {
                "value": df['floatValue'],
                "unit": df['unit'],
            }

    return dataDict


def ExtractRawValueSlice(rawUTFString, iStart, breakString, fixedLen=-1):
    # Extract the mbusstart frame

    sliceStr = ""
    while (iStart < len(rawUTFString)):
        # Break conditions
        if (fixedLen == len(sliceStr)):  # Break at fixed len (only works if fixedLen is bigger/equal 0)
            break

        if (len(breakString) < len(sliceStr)):  # Break at breakString
            if(breakString == sliceStr[-len(breakString):]):
                break

        sliceStr = sliceStr + rawUTFString[iStart]
        iStart += 1

        # Todo: Raise error if end has been reached without finding breakString

    return sliceStr, iStart


def rawByteStringToFeatureDict(rawByteString):
    rawUTFString = rawByteString.decode("utf-8")

    featureDict = {}
    i = 0

    # Extract the mbusstart frame
    breakString = "68"
    dictKey = "mbusstart"
    featureDict[dictKey], i = ExtractRawValueSlice(
        rawUTFString, i, breakString)

    # Extract the myst1 frame
    breakLen = 14
    dictKey = "myst1"
    featureDict[dictKey], i = ExtractRawValueSlice(
        rawUTFString, i, "", breakLen)

    # Extract the systemTitle frame
    breakLen = 16
    dictKey = "systemTitle"
    featureDict[dictKey], i = ExtractRawValueSlice(
        rawUTFString, i, "", breakLen)

    # Extract the myst2 frame
    breakLen = 6
    dictKey = "myst2"
    featureDict[dictKey], i = ExtractRawValueSlice(
        rawUTFString, i, "", breakLen)

    # Extract the framecount frame
    breakLen = 8
    dictKey = "frameCount"
    featureDict[dictKey], i = ExtractRawValueSlice(
        rawUTFString, i, "", breakLen)

    # Extract the adpu frame
    # Four digits have to remain at the end for checksum and mbus stop
    breakLen = len(rawUTFString) - i - 4
    dictKey = "adpu"
    featureDict[dictKey], i = ExtractRawValueSlice(
        rawUTFString, i, "", breakLen)

    # Extract the checksum frame
    breakLen = 2
    dictKey = "checksum"
    featureDict[dictKey], i = ExtractRawValueSlice(
        rawUTFString, i, "", breakLen)

    # Extract the mbusstop frame
    breakLen = 2
    dictKey = "mbusstop"
    featureDict[dictKey], i = ExtractRawValueSlice(
        rawUTFString, i, "", breakLen)

    return featureDict
