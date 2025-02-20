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

from .flex_login import FlexLogin, cmd_output_to_file
from .common import get_output_from_capture, write_csv, write_interface_summary, write_cmd_exec_summary, print_report
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
	output_file: str
	passphrase: str=''
	dyn_vars: dict = field(default_factory={})
	commands: dict = field(default_factory={})
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
		self.captures_report_dict['JDM'] = 'Not Initiated'
		self.captures_report_dict['JCP'] = 'Not Initiated'
		self.captures_report_dict['NMTE'] = 'Not Initiated'
		self.captures_report_dict['VNF-VRT'] = 'Not Initiated'

	def __call__(self):
		# 1. Server connection
		server_init = self.initialize_jump_server_connection()
		if not server_init: return

		# 2 JDM Shell Login 
		jdm_shell_connection = self.connect_to_jdm()
		if jdm_shell_connection['connected']:

			html_file_header(self.device, file=self.output_file_html)

			# 2.1 JDM CLI Captures 
			mode = 'shell'
			if self.output_file:
				cmd_output_to_file(" // JDM SHELL // ", output="", file=self.output_file)
				html_file_h2_header(" // JDM SHELL // ", file=self.output_file_html)
			op_dict = self.get_commands_output_dict(dev='JDM', mode=mode, at_prompt=jdm_shell_connection['prompt'])
			self.FL.captured_outputs[self.device_ip][mode].update(op_dict)

			# 2.2 JDM CLI Login 
			jdm_cli_connection = self.change_to_jdm_cli()
			if jdm_cli_connection['connected']:

				# 2.2.1 JDM CLI Captures
				mode = 'cli'
				if self.output_file:
					cmd_output_to_file(" // JDM CLI // ", output="", file=self.output_file)
					html_file_h2_header(" // JDM CLI // ", file=self.output_file_html)
				op_dict = self.get_commands_output_dict(dev='JDM', mode=mode, at_prompt=jdm_cli_connection['prompt'])
				self.FL.captured_outputs[self.device_ip][mode].update(op_dict)
				self.captures_report_dict['JDM'] = 'OK'

				# 2.2.2 JCP Login 
				if self.pc_jcp:
					self.jcp_login()

				# 2.2.3 NMTE Login 
				if self.pc_nmte:
					self.nmte_login()

				# 2.2.9 come out of cli
				try:
					self.FL.exit()                                 ## /// exit from jdm cli
				except OSError:
					self.write_debug_log(f"Premature Exited", pfx="[-]", onscreen=True)

			# 2.3 VNFS Login
			if self.pc_velovm:
				self.vnfs_login()

			# 2.9 Exit jdm shell
			try:
				self.FL.exit()                                 ## /// exit from jdm shell
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


	def initialize_jump_server_connection(self):
		try:
			self.FL = FlexLogin(server           = self.poller,
								server_auth_user = self.dyn_vars['attuid'],
								server_auth_psk  = self.dyn_vars['key_file_1024bit'],
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

	def connect_to_jdm(self):
		try:
			jdm_shell_connection = self.FL.connect_device(device=self.device_ip, 
														 username=self.dyn_vars['username'], 
										  				 password=self.dyn_vars['jdm_pw'])
			if not jdm_shell_connection['connected']:
				self.captures_report_dict['Status'] = "Unable to Login"
				self.write_debug_log(f"Unable to connect to JDM", pfx="[-]", onscreen=True)
			return jdm_shell_connection
		except:
			self.captures_report_dict['JDM'] = "Login Failed"
			self.write_debug_log(f"Unable to connect to JDM", pfx="[-]", onscreen=True)
			return {'connected': False}

	def change_to_jdm_cli(self):
		try:
			jdm_cli_connection = self.FL.change_mode_to_cli()
			if not jdm_cli_connection['connected']:
				self.captures_report_dict['Status'] = "Partial Captures"
				self.write_debug_log(f"Unable to connect to JDM CLI", pfx="[-]", onscreen=True)
			return jdm_cli_connection
		except:
			self.captures_report_dict['JDM'] = "CLI Failed"
			self.write_debug_log(f"Unable to connect to JDM CLI", pfx="[-]", onscreen=True)
			return {'connected': False}


	#  Login to Switch (JCP) from JDM session and capturing output
	def jcp_login(self):
		login_string = "vjunos0"

		### Connect to switch ###
		try:
			jcp_shell_connection = self.FL.connect_device(device=login_string, 
														  username='', 
														  password=self.dyn_vars['jcp_pw'])
			if not jcp_shell_connection['connected']: 
				self.captures_report_dict['Status'] = "Partial Captures"
				self.write_debug_log(f"Unable to connect to JCP", pfx="[-]", onscreen=True)
		except:
			self.captures_report_dict['JCP'] = "Login Failed"
			self.write_debug_log(f"Unable to connect to JCP", pfx="[-]", onscreen=True)
			return {'connected': False}

		### Change to CLI ###
		try:
			jcp_cli_connection = self.FL.change_mode_to_cli()
			if not jcp_cli_connection['connected']:
				self.captures_report_dict['Status'] = "Partial Captures"
				self.write_debug_log(f"Unable to connect to JCP CLI", pfx="[-]", onscreen=True)
		except:
			self.captures_report_dict['JCP'] = "CLI Failed"
			self.write_debug_log(f"Unable to connect to JCP CLI", pfx="[-]", onscreen=True)
			return {'connected': False}

		## Captures from CLI ##
		if jcp_cli_connection['connected']:
			mode = 'cli'
			if self.output_file:
				cmd_output_to_file(" // JCP - SWITCH CLI // ", output="", file=self.output_file)
				html_file_h2_header(" // JCP - SWITCH CLI // ", file=self.output_file_html)
			op_dict = self.get_commands_output_dict(dev='JCP', mode=mode, at_prompt=jcp_cli_connection['prompt'])
			self.FL.captured_outputs[self.device_ip][mode].update(op_dict)
			# ------------------------------------------------------------------------------------------------------ #
			# # --- custom / additional - commands 
			# ------------------------------------------------------------------------------------------------------ #
			# --------------- REMOVED SINCE STATICALLY ADDED ALL INTERFACES IN COMMAND FILE ------------------------ #
			# if self.FL.command_evaluation_results.get('show interfaces terse | no-more'): 
			# 	additional_show_int_commands = self.FL.command_evaluation_results['show interfaces terse | no-more']
			# 	self.FL.captured_outputs[login_string][mode].update(self.FL.execute_commands( additional_show_int_commands, at_prompt=jcp_cli_connection['prompt'] ))
			# ------------------------------------------------------------------------------------------------------ #
			self.captures_report_dict['JCP'] = 'OK'
			self.FL.exit()                             ## /// exit from jcp cli
		#
		self.FL.exit()                                 ## /// exit from jcp shell

	#  Login to NMTE from JDM session and capturing output
	def nmte_login(self):
		login_string = "ipsec-nm"

		### Connect to NMTE ###
		try:
			nmte_shell_connection = self.FL.connect_device(device=login_string, 
														  username='', 
														  password=self.dyn_vars['nm_te_pw'])
			if not nmte_shell_connection['connected']: 
				self.captures_report_dict['Status'] = "Partial Captures"
				self.write_debug_log(f"Unable to connect to NMTE", pfx="[-]", onscreen=True)
		except:
			self.captures_report_dict['NMTE'] = "Login Failed"
			self.write_debug_log(f"Unable to connect to NMTE", pfx="[-]", onscreen=True)
			return False

		### Change to CLI ###
		try:
			nmte_cli_connection = self.FL.change_mode_to_cli()
			if not nmte_cli_connection['connected']:
				self.captures_report_dict['Status'] = "Partial Captures"
				self.write_debug_log(f"Unable to connect to NMTE CLI", pfx="[-]", onscreen=True)
		except:
			self.captures_report_dict['NMTE'] = "CLI Failed"
			self.write_debug_log(f"Unable to connect to NMTE CLI", pfx="[-]", onscreen=True)
			return False

		## Captures from CLI ##
		if nmte_cli_connection['connected']:
			mode = 'cli'
			if self.output_file:
				cmd_output_to_file(" // NMTE CLI // ", output="", file=self.output_file)
				html_file_h2_header(" // NMTE CLI // ", file=self.output_file_html)
			op_dict = self.get_commands_output_dict(dev='NMTE', mode=mode, at_prompt=nmte_cli_connection['prompt'])
			self.FL.captured_outputs[self.device_ip][mode].update(op_dict)
			self.captures_report_dict['NMTE'] = 'OK'
			self.FL.exit()                             ## /// exit from nmte cli
		#
		self.FL.exit()                                 ## /// exit from nmte shell

	#  VELO VNF Login and command capture from existing session
	def velo_vm_login(self, vnf_type, vnf_id):
		# // VNF - Velo Login and capture //
		GS = "\x1D"                                 	## ==> CTRL+"]"
		try:
			velo_console = self.FL.connect_device_other(login_string=f"virsh console {vnf_id}\n\n", 
													device='VRT',
													username=self.dyn_vars['vrt_un'], 
													password=self.dyn_vars['vrt_pw'])
		except:
			self.captures_report_dict['VNF-VRT'] = "Console Connect Failed"
			self.write_debug_log(f"Unable to connect to VNF-Velo Console", pfx="[-]", onscreen=True)
			return False
		#
		if velo_console['connected']:
			mode = 'shell'                          ## default
			if self.output_file:
				cmd_output_to_file(" // VELO VM CONSOLE // ", output="", file=self.output_file)
				html_file_h2_header(" // VELO VM CONSOLE // ", file=self.output_file_html)
			op_dict = self.FL.execute_commands(self.commands[vnf_type][mode], at_prompt=velo_console['prompt'])
			self.FL.captured_outputs[vnf_type][mode].update()
			self.captures_report_dict['VNF-VRT'] = 'OK'
			self.FL.exit()                             ## /// exit from nmte cli
			self.FL.exit(spl_char=GS)
			return True
		else:
			self.captures_report_dict['Status'] = "Partial Captures"
			self.write_debug_log(f"Unable to connect to Velo-VNF", pfx="[-]", onscreen=True)
			self.captures_report_dict['VNF-VRT'] = "Console Failed"
			return False



	## Add more vm_login methods as and when identified


	#  Retrive VNF Types and VNF IDs from virsh list output
	#  Login to VNFS from existing session
	def vnfs_login(self):
		# ---- RETRIVE VM TYPE AND ID LIST
		try:
			VNF_TYPE_ID = {}
			if self.FL.command_evaluation_results.get('virsh list'):
				VNF_TYPE_ID = self.FL.command_evaluation_results['virsh list']
		except:
			self.write_debug_log(f"Unable to parse `virsh list` output, VNFs unidentified", pfx="[-]", onscreen=True)
			return False
		##
		if not VNF_TYPE_ID:
			self.write_debug_log(f"No VNFs unidentified", pfx="[-]", onscreen=True)
			return False
		#
		# ---- Capture of VMs
		for vnf_type, vnf_id in VNF_TYPE_ID.items():
			if vnf_type == 'VRT':
				self.velo_vm_login(vnf_type, vnf_id)
			### ---- ADD MORE AS NEED ---- ####
			else:
				self.write_debug_log(f"No Commands defined yet for VNF {vnf_type}", pfx="[-]", onscreen=True)


	def get_commands_output_dict(self, dev, mode, at_prompt):
		return self.FL.execute_commands(self.commands[dev][mode], at_prompt=at_prompt)

	# print and/or write log message ( debug write controlled via local debug variable)
	def write_debug_log(self, msg, pfx="[+]", onscreen=True):
		s = f"{pfx} {self.device}: {msg}"
		if onscreen: print(s)
		if self.debug:
			with open(f"{self.output_file}-debug.log", 'a') as f:
				f.write(s)

# ========================================== ========================================== #

# ------------------------------------------------------------------------------------------------------------------
#  Multithreaded Flex Connect and Capture class
# ------------------------------------------------------------------------------------------------------------------
class FlxConnectCapture(Multi_Execution):

	banner = 'FlexConnect'
	INTERFACE_SUMMARY_REPORT_FILE_ROWS_SEQ = [
		'ge-0/0/0', 'ge-0/0/1', 'ge-0/0/2', 'ge-0/0/3', 'ge-0/0/4', 'ge-0/0/5', 'ge-0/0/6', 'ge-0/0/7', 
		'ge-0/0/8', 'ge-0/0/9', 'ge-0/0/10', 'ge-0/0/11'
	]
	INTERFACE_SUMMARY_REPORT_FILE_COLS_SEQ = [
		'oper status', 'speed', 'duplex', 'auto_neg', 'mode', 'vlans', 'HA Neighbor'
	]

	def __init__(self, AP):
		display_banner(self.banner, 'green')
		self.output_path = "."
		self.output_csv_report_file = None
		self.output_csv_report_file_col_seq=[]
		self.output_intf_summary_report_file = None
		self.output_cmds_exec_summary_report_file=None
		self.AP = AP		
		super().__init__(self.AP.dict_info)              ## Initialize with list of [{device, device_ip , server}, ]
		self.devices_reports = {}
		self.devices_interface_reports = {}
		self.devices_command_exec_summary = {}
		self.passphrase = AP.passphrase
		self.display_final_summary = False
		self.pc_jcp = True
		self.pc_nmte = True
		self.pc_velovm = True
		self.debug = True

	def __call__(self):
		create_folders([self.output_path,], silent=False)
		self.start()

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
			output_file=output_file,
			passphrase=self.passphrase,
			dyn_vars=self.dyn_vars,
			commands=self.commands,
			debug=self.debug,
		)
		DC.pc_jcp = self.pc_jcp
		DC.pc_nmte = self.pc_nmte
		DC.pc_velovm = self.pc_velovm
		DC()
		FL = DC.FL
		captures_report_dict = DC.captures_report_dict
		#
		if FL.captured_outputs[device_ip]['shell']:

			### collect reports
			int_validation_dict, int_para_dict, int_to_sys_para = self.int_var_validator(output_file)
			system_validation_dict = self.sys_var_validator(output_file)
			
			### update reports
			self.devices_interface_reports[device] = int_para_dict

			system_validation_dict.update(int_validation_dict)
			system_validation_dict.update(int_to_sys_para)

			self.devices_reports[device] = {}
			self.devices_reports[device].update(system_validation_dict)
			self.devices_reports[device].update(self.AP.devices_report[device])
			self.devices_reports[device].update(captures_report_dict)
		else:
			self.devices_reports[device] = {'Hostname':device, 'Status': "Not Accessible"}
			print(f"[-] {device}: Unable to Access Device.")

		if FL.command_exec_summary:
			self.devices_command_exec_summary[device] = FL.command_exec_summary


	# a device system variable validations
	@staticmethod
	def sys_var_validator(output_file):
		validation_dict = {}
		for cmd, fn in ExternalOutputValidators.items():
			output = get_output_from_capture(output_file, cmd)[cmd]
			dic = fn(cmd, output)
			if output:
				validation_dict.update(dic)
		return validation_dict

	# a device interfaces variables validations
	def int_var_validator(self, output_file):
		int_validation_dict = {}
		IOCV = Interface_Output_Capture_Validations()
		for cmd, fn in InterfaceOutputValidators.items():
			output = get_output_from_capture(output_file, cmd)[cmd]
			if not output: continue
			IOCV.__getattribute__(fn)(cmd, output)
		flatten_int_para_dict = IOCV.flatten_int_para_dict
		flatten_int_para_dict.update(IOCV.lan_connected_interfaces)
		flatten_int_para_dict.update(IOCV.wan_connected_interfaces)
		int_para_dict = IOCV.interfaces_parameter_dict
		int_to_sys_para = IOCV.get_interfaces_to_system_para_dict()
		self.add_additional_interface_validation_columns(IOCV)
		return flatten_int_para_dict, int_para_dict, int_to_sys_para

	def add_additional_interface_validation_columns(self, IOCV):
		validation_cols = set(IOCV.INTERFACE_SUMMARY_REPORT_FILE_COLS)
		_sequenced_cols = set(self.INTERFACE_SUMMARY_REPORT_FILE_COLS_SEQ)
		missing_cols = validation_cols - _sequenced_cols 
		if missing_cols:
			self.INTERFACE_SUMMARY_REPORT_FILE_COLS_SEQ.add(missing_cols)

	### Reports write ###
	def reports_gen(self):
		if self.display_final_summary:
			self.print_summary_report()
		self.write_csv()
		self.write_interface_summary()
		self.write_cmd_exec_summary()

	def print_summary_report(self):
		display_banner('FC Summary', 'green')
		print_report(self.devices_reports)    


	def write_csv(self):
		try:
			if self.output_csv_report_file:
				write_csv(self.devices_reports, self.output_csv_report_file, 
					report_cols=self.output_csv_report_file_col_seq
				)
		except:
			print(f"[-] Writing CSV Report Failed...")


	def write_interface_summary(self):
		try:
			if self.output_intf_summary_report_file:
				write_interface_summary(self.devices_interface_reports, self.output_intf_summary_report_file,
					rows=self.INTERFACE_SUMMARY_REPORT_FILE_ROWS_SEQ, cols=self.INTERFACE_SUMMARY_REPORT_FILE_COLS_SEQ
				)
		except:
			print(f"[-] Writing Interface Summary Report Failed...")

	def write_cmd_exec_summary(self):
		try:
			if self.output_cmds_exec_summary_report_file:
				write_cmd_exec_summary(self.devices_command_exec_summary, self.output_cmds_exec_summary_report_file)
		except:
			print(f"[-] Writing Command Execution Summary Report Failed...")

# ------------------------------------------------------------------------------------------------------------------
#  main
# ------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
	pass
# ------------------------------------------------------------------------------------------------------------------


