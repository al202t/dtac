""" Define Validation functions/classes here
If getting more clumsy, devide it to multiple files.
"""

# ----------------------------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------------------------
from collections import OrderedDict
from nettoolkit.nettoolkit_common import flatten

from .common import get_vnf_type_id, get_digits

# ----------------------------------------------------------------------------------------
#  Some PreDefined Static Entries
# ----------------------------------------------------------------------------------------
WAN_INTFS = {'ge-0/0/8', 'ge-0/0/9', 'ge-0/0/10', 'ge-0/0/11',}
LAN_INTFS = {'ge-0/0/0', 'ge-0/0/1', 'ge-0/0/2', 'ge-0/0/3', 'ge-0/0/4', 'ge-0/0/5', 'ge-0/0/6', 'ge-0/0/7',}
ALL_INTFS = WAN_INTFS.union(LAN_INTFS)

JUNOS_VER_STATUS_MSGS = {
	'18.4R1-S7.1' : 'OK',
	'15.1X53-D470': "Warning: BlueJackets OS ['15.1X53-D470'] Release Detected. Please do cleanup...",
	'15.1X49-D78' : "Critical: BlueJackets.GA OS ['15.1X49-D78'] Release Detected. Cannot continue...",
	'15.1X53-D46' : "Critical: BlackHawks.4 OS ['15.1X53-D46'] Release Detected. Cannot continue...",
}
NEW_JUNOS_IMAGE_FILE = "jinstall-host-nfx-3-x86-64-22.4R2-S2.6-secure-signed.tgz"
JUNOS_MD5_DICT ={
	"jinstall-host-nfx-3-x86-64-22.4R2-S2.6-secure-signed.tgz": 'd69ee4c9b2f0ca7dd4f40d33436e52e2',
	'jinstall-host-nfx-3-x86-64-22.4R2.8-secure-signed.tgz': '7f9fe241eaa13252b5342c6c6ce99a3f',
}
JUNOS_SHORTNAME_DICT = {
	"jinstall-host-nfx-3-x86-64-22.4R2-S2.6-secure-signed.tgz": "(22.4R2-S2.6)",
	'jinstall-host-nfx-3-x86-64-22.4R2.8-secure-signed.tgz': "(22.4R2-S2.8)",
}

# ----------------------------------------------------------------------------------------
#  Some common Functions
# ----------------------------------------------------------------------------------------

# ====================================================== #
# ////////////////// SYSTEM PARAMETERS ///////////////// #
# ====================================================== #

# verify if appropriate OS is present or not 
# from show version local command and its output
def current_os_check(cmd, output):	
	for line in output:
		for junos_ver, message in JUNOS_VER_STATUS_MSGS.items():
			if junos_ver in line: 
				return {'Junos Version': junos_ver, 'Junos Version Status': message }
	## Any Other IMAGES --> Returns respective Warning String..
	return {"Junos Version Status": "OS Number Not Detected", "Junos Version": "Not detected"}

# returns device serial number
# from show chassis hardware command its output
def get_device_hardware_serial(cmd, output):
	for line in output:
		if not line.startswith("Chassis"): continue
		return {'Device Serial Number': line.split()[1]}
	return {'Device Serial Number': 'Not Detected'}

# verification of NEW JUNOS image existance in /var/tmp folder.
def verify_image_existance(cmd, output):
	for line in output:
		## file exist, returns True
		if NEW_JUNOS_IMAGE_FILE in line: 
			return {f'Image Availability {JUNOS_SHORTNAME_DICT[NEW_JUNOS_IMAGE_FILE]}': 'Available'}
	## file not exist, returns Error string. ##
	return {f'Image Availability {JUNOS_SHORTNAME_DICT[NEW_JUNOS_IMAGE_FILE]}': 'Not Available'}

# verification of MD5 for image for whichever command its called.
def verify_os_md5(cmd, output):
	image = cmd.split()[-1].split("/")[-1]
	md5 = JUNOS_MD5_DICT[image]
	return {f'MD5 Check {JUNOS_SHORTNAME_DICT[NEW_JUNOS_IMAGE_FILE]}': _compare_os_md5(image, md5, output)}

# comparision of MD5 for provided image with its pre calculated MD5 hash.
def _compare_os_md5(image, md5, output):
	for line in output:
		# return image Missing string, if image doesn't exist
		if 'No such file or directory' in line:
			return "Image ["+image+"] missing"
		# return True, if image exist and MD5 matches
		if image in line and md5 in line: return "Success"
	# return MD5 checking Error otherwise
	return "Error checking md5"


# ----------------------------------------------------------------------------------------

# ========================================================== #
# ////////////////// INTERFACE PARAMETERS ////////////////// #
# ========================================================== #

# retrives configured interfaces and its operation status 
# from show interface terse command and its output
def get_interfaces_oper_status(cmd, output):
	int_parameter_dict = OrderedDict()
	if not isinstance(output, list):
		output = output.splitlines() 
	for _int in ALL_INTFS:
		int_parameter_dict[_int] = {'oper status': 'undefined'}
		for line in output:
			spl = line.split()
			if len(spl)<=2: continue
			if spl[0] == _int:
				int_parameter_dict[_int]['oper status'] =  spl[2]
				break
	return int_parameter_dict

# retrive the additional show commands for all interfaces.
# -- unnecessary, can be added statically to creds.txt --
# -- useful only if some condition set to capture only up interfaces --
def get_connected_intfses_additional_commands(cmd, output):
	return [f"show configuration interfaces {intf} | display set" for intf in ALL_INTFS]

# ----------------------------------------------------------------------------------------

# ========================================================== #
#  INTERFACES VALIDATIONS OVER DIFFERENT INTERFACE COMMANDS  #
# ========================================================== #
class Interface_Output_Capture_Validations():

	wan_intfs = WAN_INTFS
	lan_intfs = LAN_INTFS
	INTERFACE_SUMMARY_REPORT_FILE_COLS = ['oper status', 'speed', 'duplex', 'auto_neg', 'mode', 'vlans', 'HA Neighbor']

	def __init__(self):
		self.int_para_dict = OrderedDict()
		self.int_to_sys_dict = {}

	# --- NIU - prepared initially to include all int para in csv. TBD check and remove  *2
	@property
	def flatten_int_para_dict(self):
		return {k: v for k, v in flatten(self.int_para_dict).items() if not k.endswith("oper status") or v == "up"}

	@property
	def interfaces_parameter_dict(self):
		return self.int_para_dict

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	#     show interfaces terse command evaluation for getting Operation status
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# get the operation status for each defined interfaces from sh int terse command and its output.
	# updates operation status to `int_para_dict`
	# separate out LAN/WAN up interfaces ( Assumption LAN/WAN interfaces are LAN_INTFS/WAN_INTFS respectively )
	def get_connected_intfses(self, cmd, output):
		self.interfaces_oper_status = get_interfaces_oper_status(cmd, output)
		self.int_para_dict.update(self.interfaces_oper_status)
		#
		self.up_interfaces = {k:v for k, v in self.interfaces_oper_status.items() if v['oper status'] == 'up'}
		self.wan_connected_interfaces = {'Wan Interfaces (UP)' : "; ".join(set(self.up_interfaces.keys()).intersection(self.wan_intfs))}
		self.lan_connected_interfaces = {'Lan Interfaces (UP)' : "; ".join(set(self.up_interfaces.keys()).intersection(self.lan_intfs))}

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	#     show config interface command evaluation
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# get interface parameters from - show configuration interfaces ge-0/0/x | display set command and its output
	# add those to `int_para_dict`
	def interface_validations_set_commands(self, cmd, output):
		intf = cmd.split()[3]
		int_parameters = { 'mode': 'undefined', 'vlans': [], 'auto_neg': 'undefined', 
						   'speed': 'undefined', 'duplex': 'undefined' }
		for line in output:
			int_parameters['mode'] 		= 	self._intf_mode(line, int_parameters['mode'])
			int_parameters['vlans'].extend( self._intf_vlans(line) )
			int_parameters['auto_neg'] 	= 	self._intf_negotiation(line, int_parameters['auto_neg'])
			int_parameters['speed'] 	= 	self._intf_speed(line, int_parameters['speed'])
			int_parameters['duplex'] 	= 	self._intf_duplex(line, int_parameters['duplex'])
		if not self.int_para_dict.get(intf):
			self.int_para_dict[intf] = {}
		self.int_para_dict[intf].update(int_parameters)

	def _intf_mode(self, line, mode):
		if "interface-mode" in line: return line.split()[-1]
		return mode

	def _intf_vlans(self, line):
		if "vlan members" in line and not line.strip().endswith("default"): return [line.split()[-1], ]
		return []

	def _intf_negotiation(self, line, auto_neg):
		if "no-auto-negotiation" in line or "no auto-negotiation" in line: return "No"
		elif "auto-negotiation" in line: return "Yes"
		return auto_neg

	def _intf_speed(self, line, speed):
		if "speed" in line: return line.split()[-1]
		return speed

	def _intf_duplex(self, line, duplex):
		if " link-mode " in line or "duplex" in line : return line.split()[-1]
		return duplex

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	#                    HA PORT VALIDATIONS
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

	# this function updates `int_to_sys_dict` to update with HA Port Validation columns informations
	# Ex:  'HA Neighbor', 'HA Port VLANS', 'WAN VLANS', 'Remarks'
	# Returns `int_to_sys_dict` dictionary..
	def get_interfaces_to_system_para_dict(self):
		self.int_to_sys_dict.update(self.get_ha_port_vlans_ext())
		self.int_to_sys_dict.update(self.get_wan_port_vlans_ext())		
		self.int_to_sys_dict.update(self.get_remarks_ext())
		return self.int_to_sys_dict


	# get lldp neighbor informations for all ports (where available) from show lldp neighbour output.
	# adds it to int_para_dict
	def get_lldp_neighbour(self, cmd, output):
		for line in output:
			spl = line.strip().split()
			if len(spl) < 2: continue
			if not spl[0][1:].startswith("e-0/0/"): continue
			self.int_para_dict[spl[0]] ['HA Neighbor'] = spl[-1]

	# get HA port vlans and HA Neighbor device name from int_para_dict.
	# Assumption: Port3 is HA port
	# Replaces identified HA device name from JSW to JDM for better comparision 
	def get_ha_port_vlans_ext(self):
		ha_port = 'e-0/0/3'
		ha_port_vlans = set()
		ha_port_neighbor = "N.A."
		for _intf, intf_dict in self.int_para_dict.items():
			if not _intf.endswith(ha_port): continue
			_vlans = { get_digits(v) for v in intf_dict['vlans']}
			ha_port_vlans = ha_port_vlans.union(_vlans)
			if self.int_para_dict.get(_intf) and not self.int_para_dict[_intf].get("HA Neighbor"):
				self.int_para_dict[_intf]['HA Neighbor'] = ''
			if self.int_para_dict.get(_intf) and self.int_para_dict[_intf].get("HA Neighbor"):
				ha_port_neighbor = self.int_para_dict[_intf]['HA Neighbor']
				ha_port_neighbor = ha_port_neighbor.replace("JSW", "JDM")
		return {'HA Port VLANS': set(ha_port_vlans), 'HA Neighbor': ha_port_neighbor}

	# get WAN Port vlans list from int_para_dict
	# Assumption : wan interfaes = WAN_INTFS
	def get_wan_port_vlans_ext(self):
		wan_vlans = set()
		for _intf, intf_dict in self.int_para_dict.items():
			if _intf not in self.wan_intfs: continue
			_vlans = { get_digits(v) for v in intf_dict['vlans']}
			wan_vlans = wan_vlans.union(_vlans)
		return {'WAN VLANS': wan_vlans}

	# evaluates => 1. HA_neighbor 2. wan_vlans 3. forward_vlans 4. HA_port_vlans 
	# returns remarks based on defined logic
	# Assumption:  site WAN Links vlans should not be identical and it should be in HA Port vlans.  
	def get_remarks_ext(self):
		d = self.int_to_sys_dict
		remark = ''	
		wan_vlans = { get_digits(v) for v in self.int_to_sys_dict['WAN VLANS']}
		forward_vlan = set(range(3980, 3985))
		vlans_to_exclude = {4000,}.union(wan_vlans).union(forward_vlan)
		other_side_vlans = d['HA Port VLANS'].difference(vlans_to_exclude)
		if other_side_vlans and d['HA Neighbor'] != "N.A.":
			remark = "HA Available"
		elif other_side_vlans and d['HA Neighbor'] == "N.A.":
			remark = "Lookout for HA"
		elif not other_side_vlans and d['HA Neighbor'] != "N.A.":
			remark = "Lookout WAN VLANS (Identical Found)"			
		return {'Remarks' : remark}

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -



## ============================================================================ ##
## //////////////////  COMMANDS AND ITS VALIDATOR FUNCTIONS  ////////////////// ##
## ============================================================================ ##

InteractiveOutputValidators = {}
InteractiveOutputValidators['virsh list'] = get_vnf_type_id
InteractiveOutputValidators['show interfaces terse | no-more'] = get_connected_intfses_additional_commands   ## *2

ExternalOutputValidators = {}
ExternalOutputValidators['show version local'] = current_os_check
ExternalOutputValidators['show chassis hardware'] = get_device_hardware_serial
ExternalOutputValidators['file list /var/tmp detail'] = verify_image_existance
ExternalOutputValidators[f'file checksum md5 /var/tmp/{NEW_JUNOS_IMAGE_FILE}'] = verify_os_md5

InterfaceOutputValidators = OrderedDict()
InterfaceOutputValidators['show interfaces terse | no-more'] = 'get_connected_intfses'
InterfaceOutputValidators['show lldp neighbors | no-more'] = 'get_lldp_neighbour'
InterfaceOutputValidators[f'show configuration interfaces ge-0/0/0 | display set'] = 'interface_validations_set_commands'
InterfaceOutputValidators[f'show configuration interfaces ge-0/0/1 | display set'] = 'interface_validations_set_commands'
InterfaceOutputValidators[f'show configuration interfaces ge-0/0/2 | display set'] = 'interface_validations_set_commands'
InterfaceOutputValidators[f'show configuration interfaces ge-0/0/3 | display set'] = 'interface_validations_set_commands'
InterfaceOutputValidators[f'show configuration interfaces ge-0/0/4 | display set'] = 'interface_validations_set_commands'
InterfaceOutputValidators[f'show configuration interfaces ge-0/0/5 | display set'] = 'interface_validations_set_commands'
InterfaceOutputValidators[f'show configuration interfaces ge-0/0/6 | display set'] = 'interface_validations_set_commands'
InterfaceOutputValidators[f'show configuration interfaces ge-0/0/7 | display set'] = 'interface_validations_set_commands'
InterfaceOutputValidators[f'show configuration interfaces ge-0/0/8 | display set'] = 'interface_validations_set_commands'
InterfaceOutputValidators[f'show configuration interfaces ge-0/0/9 | display set'] = 'interface_validations_set_commands'
InterfaceOutputValidators[f'show configuration interfaces ge-0/0/10 | display set'] = 'interface_validations_set_commands'
InterfaceOutputValidators[f'show configuration interfaces ge-0/0/11 | display set'] = 'interface_validations_set_commands'
# Only ge interfaces expected...

# ----------------------------------------------------------------------------------------
#  main
# ----------------------------------------------------------------------------------------
if __name__ == '__main__':
	pass
# ----------------------------------------------------------------------------------------

