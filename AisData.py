# Use static & voyage data to construct list of vessels seen in this data set.
# Parse position messages.
# Add additional data to position messages.

import re
import binascii


# Data.
VesselList = []		# List of vessel information.
PosList = []		# List of AIS position reports. Supplemented with vessel information.

# Temp data.
MmsiList = []

# Functions

def AisParser():

	''' Decodes synthetic AIS to CSV format for AMS DE-RISC project.
	'''

	# Specify input file name.
	input_file_name = "AIS_Data_2018_02_09.dat"	
	output_file_name = input_file_name.replace(".dat", "_decoded.csv")

	print("Input file: " + input_file_name)
	print("Output file: " + output_file_name)

	ais_data = ReadData(input_file_name)
	ais_data = RemoveTimestamps(ais_data)
	ais_sentence_list = ais_data.split("\n")

	# Parse AIS sentences.
	for sentence in ais_sentence_list:
		if sentence != "":
			ParseSentence(sentence)		

	# Supplement position reports with static/voyage data.
	SuppPosReports()

	# Write decoded data to file.
	WriteOutputFile(output_file_name)	

	return


def ReadData(file_name):

	''' Reads AIS data from file into string.
	'''

	with open(file_name,"r") as input_file:
		ais_data = input_file.read()

	return ais_data

def WriteOutputFile(output_file_name):

	''' Writes decoded AIS data to csv file.
	'''

	data_fields_order = [	"MMSI",
							"Timestamp",
							"Latitude",
							"Longitude",
							"COG",
							"SOG",
							"Heading",
							"Navigation Status",
							"IMO",
							"Vessel Name",
							"Call Sign",
							"Ship Type"
						]									

	#Write output file
	with open(output_file_name,"w") as output_file:

		for pos_report in PosList:

			for data_type in data_fields_order:

				output_file.write(str(pos_report[data_type]))

				if data_type != data_fields_order[-1]:
					output_file.write(",")

			output_file.write("\n")



def RemoveTimestamps(ais_data):

	''' Removes timestamps from AIS data.

	Synthetic AIS generated in the TTL is interspersed with timestamps
	which should be removed before processing.

	'''

	# Construct regular expression.
	regex = re.compile("15181" + "\d\d\d\d\d\d\d\d")
	
	# Find all timestamps.
	find_list = regex.findall(ais_data)

	# Remove all timestamps.
	for match in find_list:
		ais_data = ais_data.replace(match,"")

	return(ais_data)


def ParseSentence(ais_sentence):

	''' Generic function to parse AIS setences.
	'''

	# Split sentence into parts.
	sentence_parts = ais_sentence.split(",")

	# Collect parts.
	payload = sentence_parts[5]

	# Type 1, 2 and 3: Position Report Class A.
	if len(payload) == 28:
		payload_noarmour = RemovePayloadArmour(payload)
		ParsePositionReport(payload_noarmour)

	# Type 5: Static and Voyage Related Data
	elif len(payload) == 71:		
		payload_noarmour = RemovePayloadArmour(payload)
		ParseStaticData(payload_noarmour)

	# Anything else.
	else:
		print("Unsupported payload length! " + str(len(payload)))


	return

def ParsePositionReport(payload_noarmour):

	''' Type 1, 2 and 3: Position Report Class A.
	'''
	
	# Get details from payload.

	msg_type = BinStringExtractInt(payload_noarmour,0,6)
	repeat_ind = BinStringExtractInt(payload_noarmour,6,8)

	mmsi = BinStringExtractInt(payload_noarmour,8,38)
	nav_status = BinStringExtractInt(payload_noarmour,38,42)
	rot = BinStringExtractInt(payload_noarmour,42,50)
	sog = BinStringExtractInt(payload_noarmour,50,60)
	
	pos_accuracy = BinStringExtractInt(payload_noarmour,60,61)

	longitude = BinStringExtractLatLon(payload_noarmour,61,89)
	latitude = BinStringExtractLatLon(payload_noarmour,89,116)

	cog = BinStringExtractInt(payload_noarmour,116,128)
	heading = BinStringExtractInt(payload_noarmour,128,137)
	timestamp = BinStringExtractInt(payload_noarmour,137,143)
	man_ind = BinStringExtractInt(payload_noarmour,143,145)
	spare = BinStringExtractInt(payload_noarmour,145,148)
	raim = BinStringExtractInt(payload_noarmour,148,149)
	rad_stat = BinStringExtractInt(payload_noarmour,149,168)	

	details = {	"Message Type": msg_type,
				"Repeat Indicator": repeat_ind,
				"MMSI": mmsi,
				"Navigation Status": nav_status,
				"ROT": rot,
				"SOG": sog,
				"Position Accuracy": pos_accuracy,
				"Latitude": latitude,
				"Longitude": longitude,
				"COG": cog,
				"Heading": heading,
				"Timestamp": timestamp,
				"Maneuver Indicator": man_ind,
				"Spare": spare,
				"RAIM Flag": raim,
				"Radio Status": rad_stat
				}

	

	PosList.append(details)	
	return


def ParseStaticData(payload_noarmour):

	''' Type 5: Static and Voyage Related Data
	'''

	# Get details from payload.
	mmsi = BinStringExtractInt(payload_noarmour,8,38)
	imo = BinStringExtractInt(payload_noarmour,40,70)	
	call_sign = BinStringExtractString(payload_noarmour,70,112)	
	vessel_name = BinStringExtractString(payload_noarmour,112,232)
	ship_type = BinStringExtractInt(payload_noarmour,232,240)

	# Check if vessel has already been added. If not, add it.	
	if mmsi in MmsiList:
		pass
	else:
		MmsiList.append(mmsi)
		VesselList.append({	"MMSI": mmsi,
							"IMO": imo,
							"Call Sign": call_sign,
							"Vessel Name": vessel_name,
							"Ship Type": ship_type
							})
		
	return

def RemovePayloadArmour(payload):

	''' Remove payload armouring ready for parsing.
	'''

	# Convert 6 bit ascii to binary string.
	sentence_bin = ''
	for char in payload:
		char_int = ord(char) - 48
		if char_int > 40:
			char_int = char_int - 8
		
		char_bin = format(char_int,"0>6b")
		sentence_bin += char_bin	

	return sentence_bin

def BinStringExtractInt(payload_noarmour, start, end):

	''' Extract int from unarmoured payload
	'''

	data_bin = payload_noarmour[start:end]
	data = int(data_bin,base=2)

	return data

def BinStringExtractString(payload_noarmour, start, end):

	''' Extract 6 bit text from binary string.

	THIS NEEDS MORE WORK!

	'''

	length = end - start
	data = payload_noarmour[start:end]

	start = 0
	new_string = ""
	while start != length:
		char_bin = data[start:start+6]

		if char_bin != "000000":
			char_bin = "01" + char_bin
			char_int = int(char_bin,2)			
			char = chr(char_int)			
			new_string += char			
		else:
			new_string += " "
		start += 6

	return new_string

def BinStringExtractLatLon(payload_noarmour, start, end):

	''' Extract Lat/Lon from payload encoded as Twos compliment.
	'''	

	data_bin = payload_noarmour[start:end]

	#Resolve number for two's complement
	if data_bin[0] == '1':
		integer = (int(data_bin,2) - (1 << len(data_bin)))
	else:
		integer = int(data_bin,2)
	return(integer)

def SuppPosReports():

	''' Supplement position reports with static/voyage data.
	'''

	# Go through all position reports.
	for pos_report in PosList:

		# Find relevant data.
		for vessel in VesselList:

			if pos_report["MMSI"] == vessel["MMSI"]:

				pos_report["IMO"] = vessel["IMO"]
				pos_report["Call Sign"] = vessel["Call Sign"]
				pos_report["Vessel Name"] = vessel["Vessel Name"]
				pos_report["Ship Type"] = vessel["Ship Type"]

AisParser()