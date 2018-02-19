# This file is old and outdated. A first rushed attempt at decoding AIS data.
# I just want to hang into it in case there is anything useful in here I've
# forgotten about.
#-----------------------------------------------------------------------------

import struct
import random
import re
import os

# Useful AIS, AIVDM information.
# http://catb.org/gpsd/AIVDM.html#_ais_payload_interpretation

def convertAMSSentences():

	'''Generate CSV formatted data for use in AMS DE-RISC trials.
	'''
	
	#Name of AIS data file (generated using Java app and IMIST data recorder)
	aisInFileName = "AIS_Data_2018_02_09.dat"
	aisOutFileName = aisInFileName.replace(".dat","_converted.csv")
	
	ais_data = GetData(aisInFileName)
	
	#Get list of all sentences to be decoded.
	extractedAivdmSentences = aisDataParser(ais_data,44)

	# Stop execution if no lines collected.
	if len(extractedAivdmSentences) == 0:
		print("No valid lines extracted!")
		return

	#List of dictionaries holding decoded data.
	decoded_data = []
	
	#For each AIVDM line decode the payload and add the decoded data to a list.
	for sentence in extractedAivdmSentences:
		
		#Process encoded payload.
		keyInfo = decodePayload(sentence[5])
		decoded_data.append(keyInfo)	
		
	#Loop over decoded data and add additional information (for AMS DE-RISC trial)
	decoded_data = GenAddFields(decoded_data)
	
	#Get list of fields to write to output file.
	fieldList = createFieldOrder()
	
	#Write decoded AIVDM data to CSV file.
	with open(aisOutFileName,"w") as outputFile:
		for item in decoded_data:
			
			#Define empty string to be populated.
			protoString = ''
			
			#Add in data from all chosen fields.
			for field in fieldList:
				protoString += '{0},'.format(item[field])
				
			#Delete final comma.
			outputString = protoString[0:len(protoString)-1]
				
			#Add new line.
			outputString += '\n'
			
			#Write line to output file.
			outputFile.write(outputString)

	return

def GetData(file_name):
	try:
		# Load AIS data from file.
		with open(file_name,"r") as input_file:
			ais_data = input_file.read()
	except OSError:
		print(file_name + " was not found!")
		return

	return(ais_data)

def StripTimeStamps(ais_data, search_string):

	''' Strip timestamps out of synthetic AIS data
	'''
	
	# Construct regular expression.
	regex = re.compile("1518" + "\d\d\d\d\d\d\d\d\d")
	
	# Find all timestamps.
	find_list = regex.findall(ais_data)

	# Remove all timestamps.
	for match in find_list:
		ais_data = ais_data.replace(match,"")

	return(ais_data)

def aisDataParser(ais_data, starIndex):

	'''Parses modified AIS data from DisAisToFile.
	
	Function input from DisAisToFile must first have timestamps removed.

	Pulls out specified lines.

	Lines should start with !AIVDM

	Lines should have a * in a given position.

	Star should be the last character.

	'''

	#Pull out !AIVDM lines. 
	aivdmList = []
	tempList = ais_data.split("\n")
	
	linesCollected = 0
	
	#Scan through all data and add lines to list for processing.
	for line in tempList:
	
		#Check line starts with !AIVDM and star is at expected index.
		if (line[0:6] == "!AIVDM" and len(line) > starIndex and line[starIndex] == "*"):
		
			#Split sentence into parts based on comma.
			splitLine = line.split(",")
			
			#Add to list
			aivdmList.append(splitLine)
			
			linesCollected += 1
	
	print("Lines collected: {0}".format(linesCollected))
	
	return(aivdmList)
	
def decodePayload(sentence):

	'''Decodes AIVDM payload.
	'''

	# Convert string to 6 bit binary string.
	sentenceBin = ''
	for char in sentence:
		charInt = ord(char) - 48
		if charInt > 40:
			charInt = charInt - 8
		
		charBin = format(charInt,"0>6b")
		sentenceBin += charBin
	
	msgtypeBin = sentenceBin[0:6]# msg type
	msgType = int(msgtypeBin,base=2)
	
	repIndBin = sentenceBin[6:8]# repeat indicator
	repInd = int(repIndBin,base=2)
	
	mmsiBin = sentenceBin[8:38]# mmsi
	mmsi = int(mmsiBin,base=2)
	
	navStatBin = sentenceBin[38:42]# navigation status
	navStat = int(navStatBin,base=2)
	
	rotBin = sentenceBin[42:50]# rate of turn
	rot = int(rotBin,base=2)
	
	sogBin = sentenceBin[50:60]# sog
	sog = int(sogBin,base=2)
	
	posAccBin = sentenceBin[60:61]# position accuracy
	posAcc = int(posAccBin,base=2)
	
	lonBin = sentenceBin[61:89]# longitude
	lon = twoComp(lonBin)
	
	latBin = sentenceBin[89:116]# latitude
	lat = twoComp(latBin)
	
	cogBin = sentenceBin[116:128]# cog
	cog = int(cogBin,base=2)
	
	hdgBin = sentenceBin[128:137]# heading
	hdg = int(hdgBin,base=2)
	
	timeStampBin = sentenceBin[137:143]# time stamp
	timeStamp = int(timeStampBin,base=2)
	
	manIndBin = sentenceBin[143:145]# maneuver indicator
	manInd = int(manIndBin,base=2)
	
	spareBin = sentenceBin[145:148]# spare (not used)
	spare = int(spareBin,base=2)
	
	raimFlagBin = sentenceBin[148:149]# RAIM flag.
	raimFlag = int(raimFlagBin,base=2)
	
	radStatBin = sentenceBin[149:168]# RAIM flag.
	radStat = int(radStatBin,base=2)
	
	decodedInfo = {
		"Message Type":msgType,			# Constant from 1-3
		"Repeat Indicator":repInd,		# Message repeat count (tells other transceivers whether or not to rebroadcast)
		"MMSI":"{:0>9}".format(mmsi),	# A unique 9 digit code identifying the vessel
		"Navigation Status":navStat,	# 0 - 15, state of the vessel. 15 = Not defined.
		"ROT":rot,						# Rate of turn, -128 - 128.
		"SOG":sog,						# 0 - 1023, speed over ground in 0.1 knot resolution.
		"Position Accuracy":posAcc,		# 0 or 1. 1, fix precision < 10 ms. 0, fix precision > 10 ms.
		"Longitude":lon,				# 
		"Latitude":lat,					# 
		"COG":cog,						# Course over ground. 0.1 degree resolution.
		"Heading":hdg,					# True heading, 0 to 359, 511 = not available.
		"Time Stamp":timeStamp,			# Seconds in UTC time stamp. 0 - 59 second values, 60 - 63 reserved for other cases.
		"Spare":spare,					# Spare, not currently used.
		"Maneuver Indicator":manInd,	# 0 - 3
		"RAIM Flag":raimFlag,			# 0 or 1
		"Radio Status":radStat			# Diagnostic radio information.
	}
	
	return(decodedInfo)
	

def twoComp(binaryString):

	decimalPlaces = 6

	#Resolve number for two's complement
	if binaryString[0] == '1':
		integer = (int(binaryString,2) - (1 << len(binaryString)))
	else:
		integer = int(binaryString,2)
	return(integer)


def convertShortSentences(ais_data):

	#Get list of all sentences to be decoded.
	shortAivdmMessages = aisDataParser("AIS_Data.dat",44)

	#List to hold decoded data.
	decodedData = []
	
	#For each AIVDM line decode the payload and add the decoded data to a list.
	for sentence in shortAivdmMessages:
	
		#Process information not in encoded payload.
		#sentenceType = sentence[1]
		#sentenceFragments
		
		#Process encoded payload.
		keyInfo = decodePayload(sentence[5])
		decodedData.append(keyInfo)
	
	#Write decoded AIVDM data to csv file.
	with open('aivdmDecoded_short.csv','w') as outputFile:
		for item in decodedData:
				
				outputStringProto = '{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15}\n'
				
				outputString = outputStringProto.format(
				item['Message Type'],
				item['Repeat Indicator'],
				item['MMSI'],
				item['Navigation Status'],
				item['ROT'],
				item['SOG'],
				item['Position Accuracy'],
				item['Longitude'],
				item['Latitude'],
				item['COG'],
				item['Heading'],
				item['Time Stamp'],
				item['Spare'],
				item['Maneuver Indicator'],
				item['RAIM Flag'],
				item['Radio Status']
				)
				
				outputFile.write(outputString)

def CreateAddFieldsTemplate(decoded_data):

	''' 

	Given a set of decoded AIS data generates a template for fill in
	additional data.

	'''

	# Get unique list of MMSI numbers.
	mmsi_list = []
	for entry in decoded_data:
		mmsi_list.append(int(entry["MMSI"]))
	mmsi_list.sort()
	unique_mmsi_list = set(mmsi_list)

	with open("Ship Details TEMPLATE.csv","w") as temp_file:

		temp_file.write("REMOVE THIS LINE AND REMOVE \"TEMPLATE\" FROM FILE NAME WHEN FINISHED\n")

		for mmsi in unique_mmsi_list:

			temp_file.write("Old MMSI:" + str(mmsi).zfill(9) + ",")
			temp_file.write("IMO:" + "XXXXXXX" + ",")
			temp_file.write("Name:" + "XXXXXXXXXXXXXX" + ",")
			temp_file.write("Callsign:" + "XXXXXXX" + ",")
			temp_file.write("Type:" + "XX" + ",")
			temp_file.write("New MMSI:" + "XXXXXXXXX" + "\n")

	return
				
def GenAddFields(decoded_data):

	'''Append additional fields to decoded AIS data.
	
	This function takes in decoded AIS data and adds additional fields to the dictionaries so that
	the data can be used in the AMS DE-RISC trials.

	'''
	
	input_filename = "Ship Details.csv"

	# Check if file exists.
	if (os.path.isfile(input_filename)):
		pass
	else:
		print(input_filename + " file not found. Generating template file.")
		CreateAddFieldsTemplate(decoded_data)
		return

	#Import additional data from CSV file.
	with open(input_filename,"r") as addDataFile:
			data = addDataFile.read()
		
	#Create list from additional data.
	addDataList = []
	dataLines = data.split('\n')
	for line in dataLines:
		if line != '':			
			current_dict = {}
			line_parts = line.split(",")
			for part in line_parts:
				key_value = part.split(":")
				current_dict[key_value[0]] = key_value[1]
			addDataList.append(current_dict)			
			
	# Match MMSI in data to MMSI in additional data and add entries.
	for entry in decoded_data:	

		# Get MMSI of entry in decoded data.
		currentMMSI = entry['MMSI']
		
		# Find location of MMSI in additional data.
		for item in addDataList:			
			if item["Old MMSI"] == currentMMSI:
				dict_match = item
				break
		
		# Add data from corresponding MMSI in additional data.
		entry['IMO'] = dict_match["IMO"]
		entry['Name'] = dict_match["Name"]
		entry['Callsign'] = dict_match["Callsign"]
		entry['Type'] = dict_match["Type"]
		
	return(decoded_data)
					
def createFieldOrder():

	''' Chooses correct fields for AMS DE-RISC

	'''

	# Change this depending on what is required in output file.
	fieldList = [
	'MMSI',
	'Time Stamp',
	'Latitude',
	'Longitude',
	'COG',
	'SOG',
	'Heading',
	'Navigation Status',
	'IMO',
	'Name',
	'Callsign',
	'Type',
	]
	
	protoString = ''
	
	for index,field in enumerate(fieldList):
		protoString += '{' + str(index) + '},'
		
	protoString = protoString[0:len(protoString)-1]
	protoString += '\n'
	return(fieldList)
	
				
				
def convertLongSentences():

	#Get list of all sentences to be decoded.
	longAivdmMessages = aisDataParser("AIS_Data.dat",87)

	#List to hold decoded data.
	decodedData = []
	
	#Process each line in the aivdmList.
	for sentence in longAivdmMessages:
	
		#Process information not in encoded payload.
		#sentenceType = sentence[1]
		#sentenceFragments
		
		#Process encoded payload.
		keyInfo = decodePayload(sentence[5])
		decodedData.append(keyInfo)
		
	
	#Write decoded AIVDM data to csv file.
	with open('aivdmDecoded_long.csv','w') as outputFile:
		for item in decodedData:
				
				outputStringProto = '{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15}\n'
				
				outputString = outputStringProto.format(
				item['Message Type'],
				item['Repeat Indicator'],
				item['MMSI'],
				item['Navigation Status'],
				item['ROT'],
				item['SOG'],
				item['Position Accuracy'],
				item['Longitude'],
				item['Latitude'],
				item['COG'],
				item['Heading'],
				item['Time Stamp'],
				item['Spare'],
				item['Maneuver Indicator'],
				item['RAIM Flag'],
				item['Radio Status']
				)
				
				outputFile.write(outputString)

def  genRandCallsigns(numCallsigns):

	callsigns = []

	for x in range(numCallsigns):
	
		#Decide how long callsign will be.
		callsignLength = random.randint(4,7)
	
		currentCallsign = ''
	
		for y in range(callsignLength):
		
			#Decide if char will be number or letter.
			charType = random.randint(0,1)
			
			#0 is character.
			if charType == 0:
				currentChar = chr(random.randint(65,90))
			else:
				currentChar = str(random.randint(0,9))
		
			currentCallsign += currentChar
		
		callsigns.append(currentCallsign)
		
	return(callsigns)
		
		
#convertLongSentences()
#convertShortSentences1()
#createFieldOrder()
convertAMSSentences()
#for callsign in genRandCallsigns(38):
#	print(callsign)
		
		
		
		
		
		
		
		
		
		
		
		