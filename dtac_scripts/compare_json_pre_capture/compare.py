
# ----------------------------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------------------------
from dataclasses import dataclass
from typing import Any
from pathlib import Path
from nettoolkit.nettoolkit_common import DIC

from .colorprint import print_banner

@dataclass
class Mapper():
	jd: Any
	dp: Any

	def __post_init__(self):
		self.hostnames_map = {}
		self.json_devices = list(self.jd.devices_parameters_dict.keys())
		self.capture_devices = list(self.dp.Devices.keys())

	def map_device(self, json_device, capture_device):
		if json_device not in self.json_devices:
			print_banner(f"[-] Invalid input: {json_device} not found in Json Devices - {self.json_devices}")
			return
		if capture_device not in self.capture_devices:
			print_banner(f"[-] Invalid input: {capture_device} not found in Json Devices - {self.capture_devices}")
			return
		self.hostnames_map[json_device] = capture_device

	@property
	def get_map(self):
		return self.hostnames_map




# ----------------------------------------------------------------------------------------
#  Verification class
# ----------------------------------------------------------------------------------------
@dataclass
class Verify():
	jd: Any
	dp: Any

	def __call__(self) -> Any:
		self.all_results = {}
		self.op_file_name = ''
		for device, device_dict in  self.jd.devices_parameters_dict.items():	
			if not self.op_file_name:
				self.op_file_name = device[:11]
			results={'[+] matches':{}, '[-] issues':{}}
			if self.hostnames_map[device] not in self.dp.Devices:
				self.all_results[device] = {'[+] matches':{}, '[-] issues':{'inputError':f'Capture file Not found for Device {device}'}}
				continue
			DIC.merge_dict(results, self.compare_system_info(device, device_dict))
			DIC.merge_dict(results, self.compare_wan_interfaces_info(device, device_dict))
			DIC.merge_dict(results, self.verify_nm_profice(device, device_dict))
			self.all_results[device] = results

	# ---------------------------- [ System Parameters Comparision ] ---------------------------- # 

	# Comparision of system parameters..
	def compare_system_info(self, device, device_dict):
		result = {}
		system_identifiers = [ "uCPEModelNumber", "serialNumber","uCPEImageFileName"]
		for si in system_identifiers:
			for para, value in self.dp.Devices[self.hostnames_map[device]].system_para.items():
				if para != si: continue
				if para not in device_dict['system_para_dict'].keys():
					print_banner(f"[-] Information not found in JSON {para}")
					continue
				DIC.merge_dict(result, self._verify_model(para, value, device, device_dict))
				DIC.merge_dict(result, self._verify_serial(para, value, device, device_dict))
				DIC.merge_dict(result, self._verify_image(para, value, device, device_dict))
		return result

	# ---------------------------- [ Interfaces Parameters Comparision ] ---------------------------- # 

	# Comparision of interfaces - wan only
	def compare_wan_interfaces_info(self, device, device_dict):
		result = {'[+] matches':{}, '[-] issues':{}}
		WAN_INTF_END_WITH = ( '0/8', '0/9', '0/10', '0/11')           ### WAN INTERFACES DEFINED FIXED
		for jdk, jd_int_para in device_dict['intf_para_dict'].items():
			if not jdk.endswith(WAN_INTF_END_WITH): continue
			if not self.dp.Devices[self.hostnames_map[device]].interfaces_status.get(jdk): continue
			dp_int_para = self.dp.Devices[self.hostnames_map[device]].interfaces_status[jdk]
			if dp_int_para['oper_status'] != 'up': continue
			for jd_para, dp_para in self._int_field_map.items():
				DIC.merge_dict(result, self._int_para(jdk, jd_int_para, dp_int_para, jd_para, dp_para))
		return result

	# ---------------------------- [ System Parameters Comparision functions ] ---------------------------- # 

	# partial match
	def _verify_model(self, para, value, device, device_dict):
		d = {'[+] matches':{}, '[-] issues':{}}
		if para != 'uCPEModelNumber' :return {}
		if device_dict['system_para_dict'][para] in self.dp.Devices[self.hostnames_map[device]].system_para[para]:
			msg = f"[+] Device [Model] {device_dict['system_para_dict'][para]}:  is `inline` with {self.dp.Devices[self.hostnames_map[device]].system_para[para]} between JSON and Device"
			d['[+] matches']['Model'] = msg
		else:
			msg = f"[-] Device [Model] {device_dict['system_para_dict'][para]}: is `not inline` with {self.dp.Devices[self.hostnames_map[device]].system_para[para]} between JSON and Device"
			d['[-] issues']['Model'] = msg
		return d

	# exact match
	def _verify_serial(self, para, value, device, device_dict):
		d = {'[+] matches':{}, '[-] issues':{}}
		if para != 'serialNumber': return {}
		if device_dict['system_para_dict'][para] == value:
			msg = f"[+] [Serial Number] between JSON <--> Device inventory : `Match`"
			d['[+] matches']['Serial Number'] = msg
		else:
			msg = f"[-] [Serial Number] between JSON {device_dict['system_para_dict'][para]} <--> Device inventory {value} : `Not Match`"
			d['[-] issues']['Serial Number'] = msg
		return d

	# availability and integrity check
	def _verify_image(self, para, value, device, device_dict):
		d = {'[+] matches':{}, '[-] issues':{}}
		if para != 'uCPEImageFileName' : return {}
		junos_image = device_dict['system_para_dict'][para]
		dev_obj = self.dp.Devices[self.hostnames_map[device]]
		dev_obj.junos_image = junos_image
		dev_obj.junos_available = dev_obj.is_junos_available()
		dev_obj.junos_md5 = dev_obj.check_junos_md5()
		if dev_obj.junos_available and dev_obj.junos_md5:
			msg = f"[+] ({junos_image}): Match between JSON and Device, `Available` in device and `MD5 Good`"
			d['[+] matches']['Junos image'] = msg
		elif dev_obj.junos_available and not dev_obj.junos_md5:		
			msg = f"[-] ({junos_image}): Match between JSON and Device, `Available` in device but `MD5 Error`"
			d['[-] issues']['Junos image'] = msg
		elif not dev_obj.junos_available:
			msg = f"[-] ({junos_image}): Not match between JSON and Device, `Not Available` in device"
			d['[-] issues']['Junos image'] = msg
		return d

	# ---------------------------- [ Interface Parameters Comparision functions ] ---------------------------- # 

	_int_field_map = {
		# jinja : device
		'portSpeed': 'speed',
		'portDuplex': 'duplex',
		'portMode': 'mode',
		'vlanIdInner': 'vlan numbers',   ## set instance
	}

	def _int_para(self, jdk, jd_int_para, dp_int_para, jd_para, dp_para):
		d = {'[+] matches':{}, '[-] issues':{}}
		if not jd_int_para.get(jd_para) and dp_int_para.get(dp_para):
			d['[-] issues'][f'WAN Interface {jdk} [{dp_para}]'] = f'[-] {jd_para}: Variable not found in JSON'
			return d
		if jd_int_para.get(jd_para) and not dp_int_para.get(dp_para):
			d['[-] issues'][f'WAN Interface {jdk} [{dp_para}]'] = f'[-] {dp_para}: not found in capture'
			return d
		if not jd_int_para.get(jd_para) and not dp_int_para.get(dp_para): return

		if ((jd_para == 'vlanIdInner' and set(jd_int_para[jd_para]) == dp_int_para[dp_para]) or
			(jd_para != 'vlanIdInner' and jd_int_para[jd_para] == dp_int_para[dp_para])):
			msg = f"[+] Match between JSON and Device"
			d['[+] matches'][f'WAN Interface {jdk} [{dp_para}]'] = msg
		else:
			msg = f"[-] Not match JSON:{jd_int_para[jd_para]}, Device:{dp_int_para[dp_para]}"
			d['[-] issues'][f'WAN Interface {jdk} [{dp_para}]'] = msg
		return d

	# ---------------------------- [ Static Parameters Comparision functions ] ---------------------------- # 

	def verify_nm_profice(self, device, device_dict):
		d = {'[+] matches':{}, '[-] issues':{}}
		if device_dict['other_para_dict']['nmProfileName'].startswith("NM_PROFILE_ATTNFV"):
			msg = f"[+] Name OK [{device_dict['other_para_dict']['nmProfileName']}]"
			d['[+] matches'][f'NM Profile'] = msg
		else:
			msg = f"[-] Name Error: [{device_dict['other_para_dict']['nmProfileName']}]"
			d['[-] issues'][f'NM Profile'] = msg
		return d

	# ---------------------------- [ OUTPUT Functions ] ---------------------------- # 

	# Returns output string
	def result_string(self, display=False):
		s = ''
		single_line = f'# {"-"*120} #\n'
		double_line = f'# {"="*120} #\n\n'
		main_header = f"{single_line}#\t DIFFERENCE BETWEEN \n#\t JSON [{self.jd.json_file}] & \n#\t PRE-CAPTURE FILES \n{single_line}\n"
		s += main_header
		print_banner(main_header, 'white')
		for hostname, results in self.all_results.items():
			hostname_header = f"{single_line}#\t\t\t{hostname}\n{single_line}"
			s += hostname_header
			print_banner(hostname_header, 'cyan')

			for key, result_items in results.items():
				if key == '[+] matches': color = 'green'
				if key == '[-] issues': color = 'red'
				key_header = f"{single_line}# {key}\n{single_line}"
				s += key_header
				print_banner(key_header, color)

				if len(result_items) > 0 :
					max_len = max([len(x) for x in result_items.keys()])
				for k, v in result_items.items():
					result_line = f"  {k.ljust(max_len)}: {v}\n"
					s += result_line
					print_banner(result_line.rstrip(), color)
				s+="\n"
				print_banner("\n", None)
			s += double_line
			print_banner(double_line, None)

		return s

	# writes output string to a file
	def results_to_file(self, folder=None, result_string=''):
		filename = self.op_file_name if self.op_file_name else "pre-json_comparision_result"
		file = f"{folder}/{filename}.txt"
		with open(file, 'w') as f:
			f.write(result_string)


# ----------------------------------------------------------------------------------------
#  Main
# ----------------------------------------------------------------------------------------
if __name__ == "__main__":
	pass
# ----------------------------------------------------------------------------------------





















