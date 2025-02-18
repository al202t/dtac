""" Flex Login base Script.
"""

# ------------------------------------------------------------------------------------------------------
#   IMPORTS
# ------------------------------------------------------------------------------------------------------
from dataclasses import dataclass
from netmiko import ConnectHandler, redispatch
import netmiko
from time import sleep
from collections import OrderedDict

from .common import print_banner

# ----------------------------------------------------------------------------------------
#  Some PreDefined Static Entries
# ----------------------------------------------------------------------------------------
SERVER_TYPE = 'terminal_server'
CTRL_C = '\003'

# ------------------------------------------------------------------------------------------------------
#  Local Functions
# ------------------------------------------------------------------------------------------------------

# writes provided command and its output to given file (append mode)
def cmd_output_to_file(cmd, output, file):
	dbl_line = f"# {'='*80}\n"
	s = f"\n{dbl_line}# Output For command: {cmd}\n{dbl_line}\n{output}\n"
	with open(file, 'a') as f:
		f.write(s)

# writes provided command and its output to given file (append mode)
def cmd_output_to_html_file(cmd, output, file):
	s = f"""
<details>
<summary>{cmd}</summary>
<pre>
{output}
</pre>
</details>
"""
	with open(file, 'a') as f:
		f.write(s)

# ------------------------------------------------------------------------------------------------------
#   FLEX LOGIN BASE CLASS
# ------------------------------------------------------------------------------------------------------
@dataclass
class FlexLogin():
	server: str                                 # poller
	server_auth_user: str                       # poller user name to login (att uid)
	server_auth_pass: str=''                    # poller auth password (RSA Token) 
	server_auth_psk : str=''                    # poller auth via PSK (if shared already, Preffered over auth_pass)
	instance_identifier: str=''                 # Instance identifier name (preferably device hostname)
	passphrase: str=''

	# Class variables
	read_timeout_override = 18                  ## overriding netmiko `read_timeout` from 10 to 18 seconds for sluggish output (ex. MD5 check)
	GS = "\x1D"                                 ## hex code of CTRL+"]"

	def __post_init__(self):
		# other instance variables initializations
		self.conn = None
		self.debug = True
		self.captured_outputs = {}
		self.display_progress = True
		self.interactive_command_evaluator = None
		self.output_file = None
		self.command_evaluation_results = {}
		self.max_connections = 100
		self.command_exec_summary = {}
		self._set_jump_server_initial_parameters()

	## ~~~~~~~~~~~~~~~~~~~~~~~~ Locals ~~~~~~~~~~~~~~~~~~~~~~~~ ##

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
		return self.conn.send_command(cmd)

	## ~~~~~~~~~~~~~~~~~~~~~~~~ internals ~~~~~~~~~~~~~~~~~~~~~~~~ ##

	def _set_jump_server_initial_parameters(self):
		self.jump_server_parameters = {
			'ip': self.server, 'device_type': SERVER_TYPE, 
			'username': self.server_auth_user, 'password': self.server_auth_pass, 'key_file': self.server_auth_psk,
			'port': 22, 'passphrase': self.passphrase,
		}

	def _is_to_connect_msg(self, device, output):
		return "(yes/no)" in output

	def _is_fingerprint_msg(self, device, output):
		return "(yes/no/[fingerprint])" in output

	def _is_device_login_banner(self, device, output):
		if " Could not resolve" in output:
			err = f"Device {device}, Unable to resolve, unable to login"
			return False
		return True

	def _is_password_prompt(self, output):
		return "asscode" in output or 'sword' in output

	def redispatch(self, device_type):
		if device_type:
			redispatch(self.conn, device_type)

	def _connect_vnf_prompts(self, expected_string, enter_string):
		RETRY_COUNT= 2
		expected_string_appear = False
		for x in range(RETRY_COUNT):
			output = self.read_channel()
			if expected_string in str(output):
				self.write_channel(f"{enter_string}\n")
				sleep(1)
				expected_string_appear = True
				break
			self.write_channel("\n")
			sleep(1)
		return expected_string_appear or not enter_string

	def connect_vnf_login_username(self, username):
		return self._connect_vnf_prompts('login', username)

	def connect_vnf_login_password(self, password):
		return self._connect_vnf_prompts('assword', password)


	## ~~~~~~~~~~~~~~~~~~~~~~~~ Connections ~~~~~~~~~~~~~~~~~~~~~~~~ ##

	# Login to Jump Server
	def connect_jump_server(self):
		self.write_debug_log(f"Connecting to {self.server}", pfx="[+]")
		self.conn = ConnectHandler(**self.jump_server_parameters)
		self.write_debug_log(f"Connected to {self.server}", pfx="[+]")

	# pinging device (3 attempts default)
	def ping_device(self, device, timer=3):
		self.write_debug_log(f"Pinging device {device}", pfx="[+]")
		command = f"ping {device}\n"
		self.write_channel(command)
		sleep(timer)
		output = self.read_channel()
		self.write_channel(CTRL_C)
		self.write_debug_log(output, pfx="[+]", onscreen=False)

	# connecting to device, manipulate delays if disconnect happen prematurely
	def connect_device(self, device, username, password, device_type='', pass_prompt_delay=5, device_login_delay=1):
		self.device = device
		html_file_header(device)
		self.captured_outputs[self.device] = {"shell": {}}
		if username:
			self.ping_device(device)
			sleep(1)
			command = f"ssh {username}@{device}\n" 
		else:
			command = f"ssh {device}\n"
		#
		for x in range(3):
			self.write_debug_log(f"Connecting to device {device}, attempt {x+1}", pfx="[+]")
			self.write_debug_log(f"SENDING CMD >>>>\n{command}", pfx="[+]", onscreen=False)
			current_prompt = self.find_prompt()
			self.write_channel(command)
			sleep(pass_prompt_delay)
			output = self.read_channel()
			self.write_debug_log(f"GOT OUTOUT >>>>\n{output}", pfx="[+]", onscreen=False)
			if output.strip().endswith(device):
				self.write_channel(CTRL_C)
				continue
			break
		#
		if self._is_fingerprint_msg(device, output) or self._is_to_connect_msg(device, output):
			self.write_debug_log(f"sending 'yes'", pfx="[+]", onscreen=False)
			self.write_channel(f"yes\n")
			sleep(1)
			output = self.read_channel()
		self.write_debug_log(f"GOT OUTOUT >>>>\n{output}", pfx="[+]", onscreen=False)
		if not self._is_device_login_banner(device, output): 
			self.write_debug_log(f"Unable to Connected to device {device}", pfx="[-]", onscreen=False)
			return {'connected': False, 'prompt': False}
		if self._is_password_prompt(output):
			self.write_debug_log(f"password Prompt appeared entering password", pfx="[+]", onscreen=False)
			self.write_debug_log(f"Trying for known password to connect to device {device}")
			self.write_channel(f"{password}\n")
		sleep(device_login_delay)

		try:
			self.write_debug_log(f"checking prompt", pfx="[+]", onscreen=False)
			new_prompt = self.find_prompt()
			self.write_debug_log(f"new prompt {new_prompt}", pfx="[+]", onscreen=False)
			self.write_debug_log(f"updating device type {device_type}", pfx="[+]", onscreen=False)
			self.redispatch(device_type)
			self.write_debug_log(f"updating device type {device_type}", pfx="[+]", onscreen=False)
			self.write_debug_log(f"Connected to device {device}")
			return {'connected': True, 'prompt': new_prompt}
		except:
			self.write_debug_log(f"Unable to Connect to device {device}", pfx="[-]")
			return {'connected': False, 'prompt': False}

	# change device mode to cli mode
	def change_mode_to_cli(self, device_type='', prompt_delay=2, display_change=False):
		self.write_debug_log(f"Changing mode to CLI ")
		self.captured_outputs[self.device]['cli'] = {}
		current_prompt = self.find_prompt()
		self.write_channel(f"cli\n")
		sleep(prompt_delay)
		output = self.read_channel()
		self.redispatch(device_type)
		new_prompt = self.find_prompt()
		self.write_debug_log(f"Prompt Changed: from {current_prompt} to {new_prompt}")
		self.write_debug_log(f"mode changed to CLI")
		return {'connected': True, 'prompt': new_prompt}

	# connect to other sub-device from main devie. tweak delays if need more wait time for next prompt.
	def connect_device_other(self, login_string, device, username='', password='', device_type='', user_prompt_delay=2, pass_prompt_delay=2, display_change=True):
		self.device = device
		self.captured_outputs[device] = {"shell": {}}
		enter_user, enter_pass = False, False
		##
		self.write_debug_log(f"connecting to device via custom string {login_string}")
		self.write_channel(f"{login_string}\n")
		sleep(user_prompt_delay)
		##
		self.write_debug_log(f"Trying {username} user login")
		enter_user = self.connect_vnf_login_username(username)
		##
		if enter_user: 
			self.write_debug_log(f"Trying with known password to login")
			enter_pass = self.connect_vnf_login_password(password)
			if not enter_pass:
				self.write_debug_log(f"No Login Password Prompt appeared")
		else:
			self.write_debug_log(f"No Login User Prompt appeared")
		##
		new_prompt = self.find_prompt()
		if new_prompt.strip().find("edge") > -1:
			self.redispatch(device_type)
			self.write_debug_log(f"connected to device with custom string {login_string}")
			return {'connected': True, 'prompt': new_prompt}
		else:
			self.write_debug_log(f"connection failed to device with custom string {login_string}", pfx="[-]")
			return {'connected': False, 'prompt': False}

	## ~~~~~~~~~~~~~~~~~~~~~~~~ Commands ~~~~~~~~~~~~~~~~~~~~~~~~ ##

	# execute list of commands on active connection
	def execute_commands(self, cmds, at_prompt, failed_retry=2, increase_read_timeout_by=5):
		self.write_debug_log(f"Start Executing list of commands")
		command_exec_dict = OrderedDict()
		all_ok = True
		for cmd in cmds:
			# _prompt = self.find_prompt()
			self.write_debug_log(f"  capturing command: {cmd}")
			cmd_exec = False
			for _ in range(failed_retry):
				try:
					command_exec_dict[cmd] = self.get_output(cmd)
					if self.output_file:
						cmd_output_to_file(cmd, output=command_exec_dict[cmd], file=self.output_file)
						cmd_output_to_html_file(cmd, output=command_exec_dict[cmd], file=self.output_file+".html")
					self.run_command_evaluator(cmd, command_exec_dict[cmd])
					cmd_exec = True
					self.command_exec_summary[cmd] = 'Success'
					break
				except netmiko.exceptions.ReadTimeout:
					self.conn.read_timeout_override = self.read_timeout_override
			if not cmd_exec:
				self.command_exec_summary[cmd] = 'Failed'
				self.write_debug_log(f"  capturing command {cmd}.. failed", pfx="[-]")
				command_exec_dict[cmd] = "failed"
				all_ok = False
		self.write_debug_log(f"Completed Executing list of commands")
		return command_exec_dict

	# Command evaluations 
	# `interactive_command_evaluator` requires to be provided from outside first 
	# in order to map cmd with validation function
	# This will dynamically selects command and its validation functions
	def run_command_evaluator(self, cmd, output):
		if not self.interactive_command_evaluator: return
		if not self.interactive_command_evaluator.get(cmd): return
		self.command_evaluation_results[cmd] = self.interactive_command_evaluator[cmd](cmd, output)

	## ~~~~~~~~~~~~~~~~~~~~~~~~ Terminations ~~~~~~~~~~~~~~~~~~~~~~~~ ##

	# exit out from current session, 
	# send additional spl_character if need to terminate via different key codes.
	def exit(self, exit_delay=1, spl_char=None):
		self.write_debug_log(f"Exiting out")
		try:
			current_prompt = self.find_prompt()
		except:
			new_prompt = None
		###			
		if spl_char: 
			self.write_channel(spl_char)
		else:
			self.write_channel("exit\n")
		sleep(exit_delay)
		###			
		try:
			new_prompt = self.find_prompt()
		except:
			new_prompt = None
		self.write_debug_log(f"Prompt Changed: from {current_prompt} to {new_prompt}")

	# exit out completely.
	def bye(self, display_change=False):
		self.write_debug_log(f"Pulling out")
		while True:
			try:
				self.write_channel("exit\n")
				sleep(1)
				prompt = self.find_prompt()
			except:
				break
			if display_change: print_banner(prompt)
			if prompt == 'logout':
				self.write_debug_log(f"logout success")
				break
		return True

	# print and/or write log message ( debug write controlled via local debug variable )
	def write_debug_log(self, msg, pfx="[+]", onscreen=True):
		s = f"{pfx} {self.instance_identifier}: {msg}"
		if onscreen: print_banner(s)
		if self.debug:
			with open(f"{self.output_file}-debug.log", 'a') as f:
				f.write(s)

# ------------------------------------------------------------------------------------------------------
#   MAIN
# ------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
	pass
# ------------------------------------------------------------------------------------------------------

