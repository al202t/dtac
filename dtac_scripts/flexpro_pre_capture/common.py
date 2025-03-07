""" Define common functions/classes which cannot be uniquely categorized anywhere else
"""
# ----------------------------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------------------------
import pandas as pd
from tabulate import tabulate
from nettoolkit.nettoolkit_db import write_to_xl

from .colorprint import print_banner

# ----------------------------------------------------------------------------------------
#  Some PreDefined Static Entries
# ----------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------
#  Some common Functions
# ----------------------------------------------------------------------------------------

# ------------------------ [ READ/INPUT ] ------------------------ #


# read a text file, and returns content as list of lines
def text_file_content(file):
	with open(file, 'r') as f: 
		lines = f.readlines()
	return lines

# Returns All kinds of commands in dictionary format ( lines are coming from text files)
def get_cmds_dict(lines):
	d = {}
	for line in lines:
		line = line.strip()
		if not line: continue
		if  not line.startswith("::") and line.endswith("::"):  # // 1st LEVEL ( JDM/JCP/NMTE... )
			k = line.split("::")[0]
			if not d.get(k): d[k] = {}
			d2 = d[k]
		elif line.startswith("::") and line.endswith("::"):     # // 2nd LEVEL ( CLI/SHELL )
			k = line.split("::")[1]
			d2[k] = []
			d3 = d2[k]
		else:                                                   # // 3rd LEVEL ( COMMANDS )
			d3.append(line) 
	return d

# Retrives the contents of creds.txt file, and and executes each lines to convert it to `variable = value`
# creds file content which starts at first columns will be considered, 
#   rest all indented lines will be considered as remarks.
def pull_variables(cred_file):
	creds_variables = {}
	try:
		tfc = text_file_content(cred_file)
	except Exception as e:
		print_banner(f"[-] Creds File read error\n{e}")
		return {}
	for l in tfc: 
		if l.startswith('Enter your credentials'): continue
		line = l.lstrip()
		if line != l: continue
		if not line.strip() : continue
		try:
			spl = l.split("=")
			s = f"creds_variables['{spl[0].strip()}'] = {spl[1]} "
			exec(s)															## pull un, pws defined in creds.txt
		except:
			# pass
			print_banner("[-] variable pull failed for: " + l)

	return creds_variables

# reads mentioned commands file  an convert its content to dictionary format
def pull_cmds_lists_dict(pre_capture_command_file):
	try:
		tfc = text_file_content(pre_capture_command_file)
	except Exception as e:
		print_banner(f"[-] Commands File read error\n{e}")
		return {}
	try:
		DEVICE_TYPE_TO_CMDS_DICT_MAP =  get_cmds_dict(tfc)
	except Exception as e:
		print_banner(f"[-] Commands File data error\nPossible Reason incorrect format.\n{e}")
		return {}
	return DEVICE_TYPE_TO_CMDS_DICT_MAP

# ------------------------ [ OPERATIONS ] ------------------------ #

# returns list of vnf list (except vjunos0) containing its (type, index) tuple
# requires output of commands "show virsh list" to retrive the same.
def get_vm_device_n_type(op):
	lines = op.splitlines()
	start = False
	vnf_list = []
	for line in lines:
		if not line.strip(): continue
		if line.strip().startswith("-------"): 
			start = True
			continue
		if not start: continue
		if line.find('vjunos0') > -1: continue
		spl = line.strip().split()
		if len(spl) > 2:
			#  TUPLE OF      ( VNF_TYPE    , VNF_ID  )
			vnf_list.append( (spl[1][16:19], spl[0]) )      ## (3 Characters from 16th Position, ID)
	if not vnf_list:
		return [(None, None)]
	return vnf_list

# returns dictionary of vnf type and respective vnf ids
# requires command and output of commands "show virsh list" to retrive the same.
def get_vnf_type_id(cmd, output):
	if cmd != "virsh list": return {}
	VNF_TYPE_ID = {}
	vnf_type_id_list = get_vm_device_n_type(output)
	for (vnf_type, vnf_id) in vnf_type_id_list:
		if vnf_type == None or vnf_id == None: continue
		VNF_TYPE_ID[vnf_type] = vnf_id 
	return VNF_TYPE_ID

# convert string repr of vlan numbers to integer Ex: Vlan3001 to 3001
def get_digits(s):
	if isinstance(s, int): return s
	t = ''
	for d in s:
		if d.isdigit(): t+=d
	return int(t)


# ------------------------ [ RETRIVE OUTPUT ] ------------------------ #

# get output dictionary from command
def get_output_from_capture(file, cmd=None):
	if not cmd: return {}
	with open(file, 'r') as f:
		lines = f.readlines()
	cmd_op_dict = {}
	if isinstance(cmd, str):
		cmd_op_dict[cmd] = get_a_cmd_output_from_capture(cmd, lines)
	elif isinstance(cmd, (list, set, tuple)):
		for _cmd in cmd:
			cmd_op_dict[cmd] = get_a_cmd_output_from_capture(cmd, lines)
	return cmd_op_dict

# get a single command output in list format from full capture lines list
def get_a_cmd_output_from_capture(cmd, lines):
	start = False
	cmd_list = []
	for line in lines:
		if line.startswith(f"# Output For command: {cmd}"):
			start = True
			continue
		if start and line.startswith("# Output For command: "):
			break
		if not start: continue
		cmd_list.append(line)
	return cmd_list


# ------------------------ [ WRITE / OUTPUT ] ------------------------ #

# write captured dictionary output to given file.  (Deprycated)
# Writes all at once at last.
# output should be in 3 leveled nested dictionary format( device: console: command: output) 
def write_output_to_file(captured_outputs, file):
	s = ""
	singe_line = f"# {'-'*80}\n"
	dbl_line = f"# {'='*80}\n"
	for device, device_dict in captured_outputs.items():
		for consoletype, cmds_dict in  device_dict.items():
			s += f"\n\n{singe_line}# \t\t\t{device} - OUTPUT\n{singe_line}"
			s += f"# \t\t\t{consoletype} Mode OUTPUT\n{singe_line}"
			for cmd, output in cmds_dict.items():
				s += f"\n{dbl_line}# Output For command: {cmd}\n{dbl_line}\n{output}"
	with open(file, 'w') as f:
		f.write(s)	

# prints summary results in given table format.
def print_report(result, tablefmt=None, color='magenta'):
	if not tablefmt: tablefmt = "rounded_outline"
	df = pd.DataFrame(result).fillna("")
	if len(df.columns) > len(df): df = df.T
	printable = tabulate(df, headers='keys', tablefmt=tablefmt)
	print_banner(printable, color=color)
	print_banner("", color='white')

# write device summary result to csv file at given output path
def write_csv(result, output_csv_report_file, report_cols=[]):
	print_banner(f"[+] Preparing CSV Report...")
	## Add all columns if report_cols is missing
	if not report_cols: 
		for _, device_objects_dict in result.items():			
			report_cols = device_objects_dict.keys()
			break
	## retrive string to write to
	s = ""
	header = ",".join(report_cols)
	s += header + "\n"
	for device, device_objects_dict in result.items():
		for i, col in enumerate(report_cols):
			value = device_objects_dict[col] if device_objects_dict.get(col) else ""
			if i > 0:
				if isinstance(value, str):                              ## Normal String values
					s += "," + value
				elif isinstance(value, (list, set, tuple)):             ## Club Interfaces
					str_value = [ str(v) for v in value]
					ifs = "," + "; ".join(str_value)
					s += ifs
				continue
			s += value
		s += "\n"
	## write out
	print_banner(f"[+] Writing CSV Report...")
	with open(output_csv_report_file, 'w') as f:
		f.write(s)
	print_banner(f"[+] Writing CSV Report Completed...")

# write interfaces summary results to excel file at given output path.
def write_interface_summary(device_int_dict, output_intf_summary_report_file, rows=[], cols=[]):
	print_banner(f"[+] Preparing Interfaces Summary Report...")
	d = {}
	for k, v in device_int_dict.items():
		try:
			df = pd.DataFrame(v).fillna('')[rows]
			df = df.T[cols]
			d[k] = df
		except:
			d[k] = pd.DataFrame({'Result': ['Error',]})
	print_banner(f"[+] Writing Interfaces Summary Report...")
	write_to_xl(output_intf_summary_report_file, d, index=True, overwrite=False)

# write commands execution summary results to excel file at given output path.
def write_cmd_exec_summary(devices_command_exec_summary, output_cmds_exec_summary_report_file):
	print_banner(f"[+] Writing Command Execution Summary Report...")
	write_to_xl(output_cmds_exec_summary_report_file, 
		{'CmdExecSummary': pd.DataFrame(devices_command_exec_summary).fillna('')}, index=True, overwrite=False)

# ----------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------
#  main
# ----------------------------------------------------------------------------------------
if __name__ == "__main__":
	pass
# ----------------------------------------------------------------------------------------


