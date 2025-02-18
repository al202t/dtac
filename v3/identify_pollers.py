""" Action_Info command executions and retrives ip information
"""

# ----------------------------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------------------------
from netmiko import ConnectHandler
from dataclasses import dataclass, field
from collections import OrderedDict
from time import sleep
from nettoolkit.nettoolkit_common import print_banner as display_banner

from .common import print_banner, print_report

# ----------------------------------------------------------------------------------------
#  Some PreDefined Static Entries
# ----------------------------------------------------------------------------------------
POLLERS_LIST = (
	## # 'rlpv12148.gcsc.att.com',    ###  Issue with this poller, Do not use.
	'rlpv12149.gcsc.att.com',  
	'rlpv12150.gcsc.att.com',  
	'rlpv12151.gcsc.att.com',  
	'rlpv12152.gcsc.att.com',  
)
POLLER_TYPE = 'terminal_server'


# ----------------------------------------------------------------------------------------
#  Class that defines an object and property for action_info retrival 
# ----------------------------------------------------------------------------------------
@dataclass
class ActionPollers():                                # Instance variables....
	server_auth_user: str                             # login username (att uid)
	devices: list = field(default_factory=[])         # list of devices (Either - JDM/JZZ )
	server: str = ''                                  # Server from where action_info to be initiated (default first from servers list)
	server_auth_pass: str=''                          # Server authentication Method1: static password (RSA Token) 
	server_auth_psk : str=''                          # Server authentication Method2: PSK file (if already shared)
	passphrase: str=''

	## class variable
	servers_list = POLLERS_LIST
	banner = 'action-info'

	def __post_init__(self):	
		display_banner(self.banner, 'blue')
		self.conn = None
		self.display_progress = True
		self.devices_report = {}
		if not self.server: self.server = self.servers_list[0]
		self._set_jump_server_initial_parameters()

	def __call__(self):
		self.connect_jump_server()
		self.print_message(f"[+] Running `action_info` on provided devices to identify ip addresses")
		self.iterrate_over_devices()

	## SOME LOCAL HELPER FUNCTIONS ##

	def _set_jump_server_initial_parameters(self):
		self.jump_server_parameters = {
			'ip': self.server, 'device_type': POLLER_TYPE, 
			'username': self.server_auth_user, 'password': self.server_auth_pass, 'key_file': self.server_auth_psk,
			'port': 22, 'passphrase': self.passphrase
		}

	def find_prompt(self):
		if not self.conn: return "" 
		return self.conn.find_prompt()

	def read_channel(self):
		if not self.conn: return "" 
		return self.conn.read_channel()

	def write_channel(self, command):
		if not self.conn: return 
		return self.conn.write_channel(command)

	def get_output(self, cmd):
		if not self.conn: return "" 
		return self.conn.send_command(cmd, expect_string=f"{self.server.split('.')[0]}  :")

	# 1. Login to Jump Server and creates a connection obj
	def connect_jump_server(self):
		self.print_message(f"[+] Connecting to {self.server}")
		self.conn = ConnectHandler(**self.jump_server_parameters)
		self.print_message(f"[+] Connected to {self.server}")

	# 2. Go thru all provided devices
	def iterrate_over_devices(self):
		self.devices_updated = OrderedDict()
		for device in self.devices:
			self.devices_updated[device] = {}
			self.devices_updated[device]['jdm_device'] = self.change_JZZ_to_JDM(device)
			self.devices_updated[device]['device_ip'] = self.collect_ip(self.devices_updated[device]['jdm_device'])

	# 3. update device name from JZZ to JDM
	@staticmethod
	def change_JZZ_to_JDM(device):
		if device.upper()[16:19] == "JZZ": 
			device = device.upper().replace("JZZ", "JDM")
		return device

	# 4. collects ip address from action_info commmand output
	def collect_ip(self, device):
		self.devices_report[device] = {'Hostname': device}
		result_line = self.get_output(f"action_info {device}\n")
		for line in result_line.splitlines():
			if not line.strip(): continue
			spl = line.split(",")
			if len(spl) > 2:
				device_ip = spl[2].strip()
				if not self.is_ip_pinging(device, device_ip):  
					self.devices_report[device]['Status'] = 'Unreachable'
					return None
				self.devices_report[device]['Status'] = 'Reachable'
				self.print_message(f"[+] {device} OK")
				return device_ip
		self.devices_report[device]['Status'] = 'action_info failed'
		self.print_message( f"[-] Cannot identify Device {device}")
		return None

	# 4.5 checks if device ip is reachable or not, return False for 100% packet loss.
	def is_ip_pinging(self, device, device_ip):
		if not device_ip: return False
		self.write_channel(f"ping {device_ip}\r\n")
		sleep(4)                                                  ## Sleep Seconds
		self.write_channel("\003")
		sleep(1)
		result_line = self.read_channel()
		for line in result_line.splitlines():
			if not "packet loss" in line: continue
			if "100% packet loss" in line:
				self.print_message( f"[-] Device Unreachable: {device}, {device_ip}")
				return False
			return True
		self.print_message( f"[-] Device Unreachable: {device}, {device_ip}")
		return False

	## Exit out from Poller
	def exit(self, exit_delay=1, spl_char=None, display_change=True):
		self.print_message(f"[+] Exiting out")
		if display_change: current_prompt = self.find_prompt()
		self.write_channel("exit\n")
		sleep(exit_delay)
		if spl_char:
			self.write_channel(spl_char)
		if display_change: 
			try:
				new_prompt = self.find_prompt()
				self.print_message(f"[+] Prompt Changed: from {current_prompt} to {new_prompt}")
			except:
				pass

	# Local print function controlled by display_progress
	def print_message(self, msg):
		if not self.display_progress: return
		color = 'red' if msg[0:3] == "[-]" else 'blue'
		print_banner(msg, color)

	# object instance property that returns all devices, ip, and its pollers in list of dict.
	# Pollers are chose round robin base.
	# multiple pollers used to share load between provided pollers during multithred execution
	@property
	def dict_info(self):
		i = 0
		list_of_devices = []
		for v in self.devices_updated.values():
			if i >= len(self.servers_list): i = 0
			if v['device_ip']:
				list_of_devices.append({'server': self.servers_list[i], 'device': v['jdm_device'], 'device_ip': v['device_ip'] })
				i+=1
		return list_of_devices

	def print_summary_report(self):
		display_banner('Summary', 'magenta')
		print_report(self.devices_report)


# ----------------------------------------------------------------------------------------
#  main
# ----------------------------------------------------------------------------------------
if __name__ == '__main__':
	pass
# ----------------------------------------------------------------------------------------

