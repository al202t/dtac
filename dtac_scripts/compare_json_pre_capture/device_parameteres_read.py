
# ----------------------------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------------------------
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

# ----------------------------------------------------------------------------------------
#  LOCAL FUNCTIONS
# ----------------------------------------------------------------------------------------
def to_digit(s):
	n = ''
	for d in s:
		if d.isdigit():
			n += d
	return int(n)

@dataclass
class DevicesPara():
	log_files: list = field(default_factory=[])

	def __call__(self):
		self.get_log_files_objs()

	def get_log_files_objs(self):
		self.Devices = {}
		for file in self.log_files:
			p = Path(file)
			host = p.stem.split("_")[0]
			DP = DevPara(file)
			DP()
			self.Devices[host] = DP


# ----------------------------------------------------------------------------------------
#  DEVICE CAPTURE PARAMETERS READ
# ----------------------------------------------------------------------------------------
@dataclass
class DevPara():
	log_file: str

	# //// list of commands for which output to be read from configuration ////
	captured_cmds =[
		"show chassis hardware",
		"file list /var/tmp detail",
		"file checksum md5 /var/tmp/jinstall-host-nfx-3-x86-64-22.4R2-S2.6-secure-signed.tgz",
		"file checksum md5 /var/tmp/jinstall-host-nfx-3-x86-64-22.4R2.8-secure-signed.tgz",
		"show chassis hardware",
		"show interfaces terse | no-more",
		"show chassis hardware",
		"show interfaces terse | no-more",
		"show configuration interfaces ge-0/0/8 | display set",
		"show configuration interfaces ge-0/0/9 | display set",
		"show configuration interfaces ge-0/0/10 | display set",
		"show configuration interfaces ge-0/0/11 | display set",
	]


	# Junos MD5 hash values.
	junos_md5_dict ={
		'jinstall-host-nfx-3-x86-64-22.4R2-S2.6-secure-signed.tgz': 'd69ee4c9b2f0ca7dd4f40d33436e52e2',
		'jinstall-host-nfx-3-x86-64-22.4R2.8-secure-signed.tgz': '7f9fe241eaa13252b5342c6c6ce99a3f',
	}

	def __post_init__(self):
		self.commands_list_dict = OrderedDict()
		# junos image file to be check in outputs - for availability and integrity
		# ----- change it to S2.8 if checking for 2.8
		self.junos_image = "jinstall-host-nfx-3-x86-64-22.4R2-S2.6-secure-signed.tgz"

	def __call__(self):
		self.get_commands_list_dict(self.read_logfile())
		#
		self.model = self.get_model()
		self.serial = self.get_serial()
		self.junos_available = self.is_junos_available()
		self.junos_md5 = self.check_junos_md5()
		self.set_system_para()
		#
		self.interfaces_status = self.get_interfaces()      # seq 1
		self.add_ints_para()                                # seq 2

	# reads log file and returns its content in list format
	def read_logfile(self):
		with open(self.log_file, 'r') as f:
			lines = f.readlines()
		return lines

	# store the output of defined commands in dictionary format, stores to self.commands_list_dict
	def get_commands_list_dict(self, lines):
		d = None
		for line in lines:
			for cmd in self.captured_cmds:
				if line.find(cmd) > -1:
					self.commands_list_dict[cmd] = []
					d = self.commands_list_dict[cmd]
				elif " show " in line:
					cmd = f"show {line.split(' show ')[-1].rstrip()}"
					self.commands_list_dict[cmd] = []
					d = self.commands_list_dict[cmd]
				elif d is not None:
					d.append(line)

	# --------------------- [ system parameters extraction ] --------------------- #

	# club system parameters in  system_para dictionary / prop
	def set_system_para(self):
		self.system_para = {
			'serialNumber': self.serial,
			'uCPEImageFileName': self.junos_available and self.junos_md5,
			'uCPEModelNumber': self.model,
		}

	def get_model(self):
		for line in self.commands_list_dict['show chassis hardware']:
			if not line.startswith("Routing Engine 0"): continue
			spl = line.strip().split()
			model = spl[-1].replace("ATT-", "")
			return model

	def get_serial(self):
		for line in self.commands_list_dict['show chassis hardware']:
			if not line.startswith("Chassis "): continue
			spl = line.strip().split()
			serial = spl[1]
			return serial

	def is_junos_available(self):
		for line in self.commands_list_dict['file list /var/tmp detail']:
			if line.find(self.junos_image) == -1: continue
			return True
		return False

	def check_junos_md5(self):
		if not self.commands_list_dict.get(f'file checksum md5 /var/tmp/{self.junos_image}'):
			return False
		for line in self.commands_list_dict[f'file checksum md5 /var/tmp/{self.junos_image}']:
			if 'MD5' in line and '=' in line and f'/var/tmp/{self.junos_image}' in line:
				return self.junos_md5_dict[self.junos_image] in line
		return False

	# --------------------- [ system parameters extraction ] --------------------- #

	# 1. extract interfaces operational status
	def get_interfaces(self):
		int_stat = {}
		for line in self.commands_list_dict['show interfaces terse | no-more']:
			spl = line.strip().split()
			if len(spl) > 2:
				intf = spl[0]
				oper_status = spl[2]
				int_stat[intf] = {'oper_status': oper_status}
		return int_stat

	# 2. extract other interfaces parameters ( speed. duplex. mode. vlans )
	def add_ints_para(self):
		for intf, intf_dict in self.interfaces_status.items():
			intf_dict['speed'] = 'auto'
			intf_dict['duplex'] = 'auto'
			if not self.commands_list_dict.get(f'show configuration interfaces {intf} | display set'): continue
			for line in self.commands_list_dict[f'show configuration interfaces {intf} | display set']:
				spl = line.strip().split()
				if ' speed ' in line:
					intf_dict['speed'] = spl[-1]
				elif ' link-mode ' in line or ' duplex ' in line:
					intf_dict['duplex'] = spl[-1]
				elif ' interface-mode ' in line:
					intf_dict['mode'] = spl[-1]
				elif ' vlan members ' in line:
					if 'vlan members default' in line: continue
					if not intf_dict.get('vlan names'):
						intf_dict['vlan names'] = set()
						intf_dict['vlan numbers'] = set()
					intf_dict['vlan names'].add(spl[-1])
					intf_dict['vlan numbers'].add( to_digit(spl[-1]) )

# ----------------------------------------------------------------------------------------
#  Main
# ----------------------------------------------------------------------------------------
if __name__ == "__main__":
	pass
# ----------------------------------------------------------------------------------------

