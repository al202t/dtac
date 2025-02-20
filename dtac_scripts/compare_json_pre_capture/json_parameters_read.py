
# ----------------------------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------------------------
from dataclasses import dataclass
import json

# ----------------------------------------------------------------------------------------
#  JSON FILE READ AND EXTRACT PARAMETERS
# ----------------------------------------------------------------------------------------
@dataclass
class JsonData():
	json_file: str

	## System parameters to extract from JSON File
	system_identifiers = [
		"uCPEModelNumber",
		"uCPEImageFileName",
		"uCPEDeploymentMode",
		"serialNumber",
		"vnfImageFileName",
		"uCPEHostName",
	]

	# Interface parameters to extract from JSON File
	interface_identifiers =  [
		"portSpeed", 
		"portDuplex", 
		"vlanIdInner", 
		"vlanNameList", 
		"portMode"
	] 

	# Other static information parameters to extract from JSON file
	other_identifiers = ['nmProfileName', ]

	def __call__(self):
		self.convert_json_to_dict()
		self.retrive_device_data_dict()
		self.devices_parameters_dict = { hostname: self.retrive_device_parameters(hostname, device_dict)
									for hostname, device_dict in self.device_data_dict.items() }
			
	# read json file and store data in dictionary
	def convert_json_to_dict(self):
		with open(self.json_file, 'r') as f:
			s = f.read()
			d = json.loads(s)
		self.complete_data_dict = d

	def retrive_device_data_dict(self):
		self.device_data_dict = {}
		for device_dict in self.complete_data_dict['childItems']:
			system_para_dict = self.retrive_system_parameters(device_dict)
			_hostname = system_para_dict['uCPEHostName']
			self.device_data_dict[_hostname] = device_dict

	def retrive_device_parameters(self, hostname, device_dict):
		return {
			'system_para_dict': self.retrive_system_parameters(device_dict),
			'intf_para_dict': self.retrive_interface_parameters(device_dict),
			'other_para_dict': self.retrive_other_parameters(device_dict),
		}

	# Retrive identified/mentioned system parameters from JSON/Dictionary
	def retrive_system_parameters(self, d):
		matched_items = {}
		if isinstance(d, dict):
			for k, v in d.items():
				if k in self.system_identifiers:
					matched_items[k] = v
				elif isinstance(v, str):
					continue
				matched_items.update(self.retrive_system_parameters(v))
		elif isinstance(d, (list, set, tuple)):
			for x in d: 
				matched_items.update(self.retrive_system_parameters(x))
		return matched_items

	# Retrive identified/mentioned parameters for all interfaces from JSON/Dictionary
	def retrive_interface_parameters(self, d):
		matched_ifs = {}
		if isinstance(d, dict):
			if "interface1" in d.keys():
				if not matched_ifs.get(d["interface1"]) :
					matched_ifs[d["interface1"]] = {}
				if_dict = matched_ifs[d["interface1"]]
				for identifier in self.interface_identifiers:
					if identifier in d.keys():
						if identifier == 'vlanIdInner':
							if d[identifier] == 'default': continue
							if_dict[identifier] = [int(_) for _ in d[identifier].split(",")]
						else:
							if_dict[identifier] = d[identifier]
			else:
				for k, v in d.items():
					matched_ifs.update(self.retrive_interface_parameters(v))
		elif isinstance(d, (list, set, tuple)):
			for x in d: 
				matched_ifs.update(self.retrive_interface_parameters(x))
		return matched_ifs

	# Retrive other additional static informational parameters from JSON/Dictionary
	def retrive_other_parameters(self, d):
		matched_items = {}
		if isinstance(d, dict):
			for k, v in d.items():
				if k in self.other_identifiers:
					matched_items[k] = v
				elif isinstance(v, str):
					continue
				matched_items.update(self.retrive_other_parameters(v))
		elif isinstance(d, (list, set, tuple)):
			for x in d: 
				matched_items.update(self.retrive_other_parameters(x))
		return matched_items

# ----------------------------------------------------------------------------------------
#  Main
# ----------------------------------------------------------------------------------------
if __name__ == "__main__":
	pass
# ----------------------------------------------------------------------------------------
