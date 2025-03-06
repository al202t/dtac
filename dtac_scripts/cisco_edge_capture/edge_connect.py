""" FlexConnect Script.
"""

# ----------------------------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------------------------
from nettoolkit.nettoolkit_common import Multi_Execution, create_folders
from nettoolkit.nettoolkit_common import print_banner as display_banner
from dataclasses import dataclass, field
from collections import OrderedDict
from pathlib import Path

from .edge_login import EdgeLogin, cmd_output_to_file
from .common import get_output_from_capture, write_csv, write_interface_summary, write_cmd_exec_summary, print_report
from .colorprint import print_banner
from .validations import InteractiveOutputValidators, ExternalOutputValidators, Interface_Output_Capture_Validations, InterfaceOutputValidators
from .save_to_html import html_file_header, html_file_footer, html_file_h2_header


# ------------------------------------------------------------------------------------------------------------------
#  A single device executor function (used in MT)
# ------------------------------------------------------------------------------------------------------------------
@dataclass
class DeviceCapture():
	poller: str
	device: str
	device_ip: str
	device_auth_un: str = ''
	device_auth_pw: str = ''
	output_file: str = ''
	passphrase: str=''
	dyn_vars: dict = field(default_factory={})
	commands: list = field(default_factory=[])
	debug: bool = True

	def __post_init__(self):
		self.FL = None
		self.pc_jcp = True
		self.pc_nmte = True
		self.pc_velovm = True
		self.p = Path(self.output_file)
		self.output_file_html = str(self.p.parent.joinpath(self.p.stem + ".html"))
		self.captures_report_dict = OrderedDict()
		self.captures_report_dict['Status'] = 'Not Initiated'

	def __call__(self):
		# 1. Server connection
		server_init = self.initialize_jump_server_connection()
		if not server_init: return

		# 2 Device Login 
		_connection = self.connect_to_device()

		if _connection['connected']:
			self.captures_report_dict['Status'] = 'connected'

			html_file_header(self.device, file=self.output_file_html)


			# 2.1 Device Captures 
			if self.output_file:
				cmd_output_to_file(f" // Device {self.device} // ", output="", file=self.output_file)
				html_file_h2_header(f" // Device {self.device} // ", file=self.output_file_html)
			op_dict = self.get_commands_output_dict(at_prompt=_connection['prompt'])
			self.FL.captured_outputs[self.device_ip].update(op_dict)


			# 2.9 Exit Device
			try:
				self.FL.exit()                                 ## /// exit from device
			except OSError:
				self.write_debug_log(f"Premature Exited", pfx="[-]", onscreen=True)

			html_file_footer(file=self.output_file_html)

		else:
			pass

		# 8. Exit Server
		try:
			self.FL.exit()                                 ## /// exit from server
		except OSError:
			self.write_debug_log(f"Premature Exited", pfx="[-]", onscreen=True)

		#
		self.captures_report_dict['Status'] = 'Success'


	def initialize_jump_server_connection(self):
		try:
			self.FL = EdgeLogin(server           = self.poller,
								server_auth_user = self.dyn_vars['attuid'],
								server_auth_psk  = self.dyn_vars['key_file'],
								passphrase       = self.passphrase,
			)
		except:
			self.write_debug_log(f"Unable to Initialize Server {self.poller} instance", pfx="[-]", onscreen=True)
			return False
		try:
			self.FL.interactive_command_evaluator = InteractiveOutputValidators
			self.FL.instance_identifier = self.device
			self.FL.output_file = self.output_file
			self.FL.output_file_html = self.output_file_html
			self.FL.debug = self.debug
		except:
			self.write_debug_log(f"Unable to set Server {self.poller} Initial Parameters", pfx="[-]", onscreen=True)
			return False
		try:
			self.FL.connect_jump_server()
			return True
		except:
			self.write_debug_log(f"Unable to connect to Server {self.poller}", pfx="[-]", onscreen=True)
			return {'connected': False}

	def connect_to_device(self):
		# try:
			_connection = self.FL.connect_device(device=self.device_ip, 
												 username=self.device_auth_un, 
								  				 password=self.device_auth_pw)
			if not _connection['connected']:
				self.captures_report_dict['Status'] = "Unable to Login"
				self.write_debug_log(f"Unable to connect", pfx="[-]", onscreen=True)
			return _connection
		# except:
		# 	self.write_debug_log(f"Unable to connect", pfx="[-]", onscreen=True)
		# 	return {'connected': False}


	def get_commands_output_dict(self, at_prompt):
		return self.FL.execute_commands(self.commands, at_prompt=at_prompt)

	# print and/or write log message ( debug write controlled via local debug variable)
	def write_debug_log(self, msg, pfx="[+]", onscreen=True):
		s = f"{pfx} {self.device}: {msg}"
		if onscreen: print_banner(s)
		if self.debug:
			with open(f"{self.output_file}-debug.log", 'a') as f:
				f.write(s+"\n")

# ========================================== ========================================== #

# ------------------------------------------------------------------------------------------------------------------
#  Multithreaded Flex Connect and Capture class
# ------------------------------------------------------------------------------------------------------------------
class DevicesCapture(Multi_Execution):

	banner = 'edgeConnect'

	def __init__(self, AP):
		display_banner(self.banner, 'green')
		self.output_path = "."
		self.output_csv_report_file = None
		self.output_csv_report_file_col_seq=[]
		self.output_intf_summary_report_file = None
		self.output_cmds_exec_summary_report_file=None
		self.AP = AP		
		super().__init__(self.AP.dict_info)              ## Initialize with list of [{device, device_ip , server}, ]
		self.init_devices_reports()
		self.devices_interface_reports = {}
		self.devices_command_exec_summary = {}
		self.passphrase = AP.passphrase
		self.display_final_summary = True
		self.pc_jcp = True
		self.pc_nmte = True
		self.pc_velovm = True
		self.debug = False

	def __call__(self):
		create_folders([self.output_path,], silent=False)
		self.start()

	def init_devices_reports(self):
		self.devices_reports = {}
		for dev, dev_dict in self.AP.devices_report.items():
			self.devices_reports[dev] = dev_dict

	# Kick
	def execute(self, action_device_info):
		#
		device    = action_device_info['device'] 
		device_ip = action_device_info['device_ip']
		output_file = f"{self.output_path}/{device}.log"
		#
		DC = DeviceCapture(
			poller=action_device_info['server'],
			device=device,
			device_ip=device_ip,
			device_auth_pw=self.device_auth_pw,
			output_file=output_file,
			passphrase=self.passphrase,
			dyn_vars=self.dyn_vars,
			commands=self.commands,
			debug=self.debug,
		)
		DC()
		FL = DC.FL
		captures_report_dict = DC.captures_report_dict
		#
		if FL.captured_outputs[device_ip]:
			pass
			# ### collect reports
			# int_validation_dict, int_para_dict, int_to_sys_para = self.int_var_validator(output_file)
			# system_validation_dict = self.sys_var_validator(output_file)
			
			# ### update reports
			# self.devices_interface_reports[device] = int_para_dict

			# system_validation_dict.update(int_validation_dict)
			# system_validation_dict.update(int_to_sys_para)

			# # self.devices_reports[device] = {}
			# self.devices_reports[device].update(system_validation_dict)
			# # self.devices_reports[device].update(self.AP.devices_report[device])
			# self.devices_reports[device].update(captures_report_dict)
		else:
			self.devices_reports[device] = {'Hostname':device, 'Status': "Not Accessible"}
			print_banner(f"[-] {device}: Unable to Access Device.")

		if FL.command_exec_summary:
			self.devices_command_exec_summary[device] = FL.command_exec_summary


	# # a device system variable validations
	# @staticmethod
	# def sys_var_validator(output_file):
	# 	validation_dict = {}
	# 	for cmd, fn in ExternalOutputValidators.items():
	# 		output = get_output_from_capture(output_file, cmd)[cmd]
	# 		dic = fn(cmd, output)
	# 		if output:
	# 			validation_dict.update(dic)
	# 	return validation_dict

	# # a device interfaces variables validations
	# def int_var_validator(self, output_file):
	# 	int_validation_dict = {}
	# 	IOCV = Interface_Output_Capture_Validations()
	# 	for cmd, fn in InterfaceOutputValidators.items():
	# 		output = get_output_from_capture(output_file, cmd)[cmd]
	# 		if not output: continue
	# 		IOCV.__getattribute__(fn)(cmd, output)
	# 	flatten_int_para_dict = IOCV.flatten_int_para_dict
	# 	flatten_int_para_dict.update(IOCV.lan_connected_interfaces)
	# 	flatten_int_para_dict.update(IOCV.wan_connected_interfaces)
	# 	int_para_dict = IOCV.interfaces_parameter_dict
	# 	int_to_sys_para = IOCV.get_interfaces_to_system_para_dict()
	# 	self.add_additional_interface_validation_columns(IOCV)
	# 	return flatten_int_para_dict, int_para_dict, int_to_sys_para

	# def add_additional_interface_validation_columns(self, IOCV):
	# 	validation_cols = set(IOCV.INTERFACE_SUMMARY_REPORT_FILE_COLS)
	# 	_sequenced_cols = set(self.INTERFACE_SUMMARY_REPORT_FILE_COLS_SEQ)
	# 	missing_cols = validation_cols - _sequenced_cols 
	# 	if missing_cols:
	# 		self.INTERFACE_SUMMARY_REPORT_FILE_COLS_SEQ.add(missing_cols)

	### Reports write ###
	def reports_gen(self):
		if self.display_final_summary:
			self.print_summary_report()
		# self.write_csv()
		# self.write_interface_summary()
		self.write_cmd_exec_summary()

	def print_summary_report(self):
		display_banner('FC Summary', 'green')
		print_report(self.devices_reports)    


	# def write_csv(self):
	# 	try:
	# 		if self.output_csv_report_file:
	# 			write_csv(self.devices_reports, self.output_csv_report_file, 
	# 				report_cols=self.output_csv_report_file_col_seq
	# 			)
	# 	except:
	# 		print_banner(f"[-] Writing CSV Report Failed...")


	# def write_interface_summary(self):
	# 	try:
	# 		if self.output_intf_summary_report_file:
	# 			write_interface_summary(self.devices_interface_reports, self.output_intf_summary_report_file,
	# 				rows=self.INTERFACE_SUMMARY_REPORT_FILE_ROWS_SEQ, cols=self.INTERFACE_SUMMARY_REPORT_FILE_COLS_SEQ
	# 			)
	# 	except:
	# 		print_banner(f"[-] Writing Interface Summary Report Failed...")

	def write_cmd_exec_summary(self):
		try:
			if self.output_cmds_exec_summary_report_file:
				write_cmd_exec_summary(self.devices_command_exec_summary, self.output_cmds_exec_summary_report_file)
		except:
			print_banner(f"[-] Writing Command Execution Summary Report Failed...")

# ------------------------------------------------------------------------------------------------------------------
#  main
# ------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
	pass
# ------------------------------------------------------------------------------------------------------------------


