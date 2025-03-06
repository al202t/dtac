
# -----------------------------------------------------------------------------------
#  Import form items from nettoolkit
# -----------------------------------------------------------------------------------
import PySimpleGUI as sg
from nettoolkit.nettoolkit.forms.formitems import *
from nettoolkit.nettoolkit_common import open_text_file, open_folder
from collections import OrderedDict
import datetime as dt

from .flex_connect import FlxConnectCapture
from .identify_pollers import ActionPollers
from .common import pull_variables, pull_cmds_lists_dict
from .colorprint import print_banner

# -----------------------------------------------------------------------------------
#  Static 
# -----------------------------------------------------------------------------------
CREDS_FILE = 'C:/PreQA6/creds.txt'
CMDS_FILE  = 'C:/PreQA6/flexware_pre_capture_commands.txt'
OUTPUT_FOLDER = 'C:/NFV-PreCheck'
POLLERS = [
	'rlpv12149.gcsc.att.com',
	'rlpv12150.gcsc.att.com',
	'rlpv12151.gcsc.att.com',
	'rlpv12152.gcsc.att.com',
]

# -----------------------------------------------------------------------------------
#  Define all your frames here 
# -----------------------------------------------------------------------------------

def dtac_pre_capture():
	devices_col = sg.Column([
		[sg.Text("Device(s) List", text_color="black"),], 
		[sg.Multiline("", key='pc_device_list', autoscroll=True, size=(30,6), disabled=False),],
	], pad=0)
	pollers_col = sg.Column([
		[sg.Text("Pollers(s) List", text_color="black"),], 
		[sg.Multiline("\n".join(POLLERS), key='pc_pollers_list', autoscroll=True, size=(30,6), disabled=False),],
	], pad=0)
	return sg.Frame(title=None, 
					relief=sg.RELIEF_SUNKEN, 
					layout=[

		[sg.Text('Pre-Capture',  font=('TimesNewRoman', 12), text_color="orange"),], 
		[sg.Text('Creds file:\t', text_color="black"), 
	     sg.InputText(CREDS_FILE, size=(40,1),  key='pc_creds_file', readonly=True, disabled_readonly_background_color='brown'), 
	     # sg.FileBrowse(button_color="grey"), 
	     sg.Button("open file", change_submits=True, key='pc_creds_file_open', button_color="darkgrey"),
	    ],
		[sg.Text('Commands file:\t', text_color="black"), 
	     sg.InputText(CMDS_FILE, size=(40,1),  key='pc_cmds_file', readonly=True, disabled_readonly_background_color='brown'), 
	     # sg.FileBrowse(button_color="grey"), 
	     sg.Button("open file", change_submits=True, key='pc_cmds_file_open', button_color="darkgrey"),
	    ],
		[sg.Text('Output folder:\t', text_color="black"), 
		 sg.InputText(OUTPUT_FOLDER, key='pc_output_path', size=(40,1), readonly=True, disabled_readonly_background_color='brown'),  
		 # sg.FolderBrowse(button_color="orange"), 
		 sg.Button("open", change_submits=True, key='pc_output_path_open', button_color="darkgrey"),
		],
		#
		[pollers_col, sg.VerticalSeparator(), devices_col],
		#
		[sg.Text("Pass-phrase:\t\t", text_color="black"), sg.InputText("", password_char='*', key='pc_passphrase', size=(15,1)),],
		[sg.Text('Concurrent connections:\t', text_color="black"), 
		 sg.InputText(12,  key='pc_max_connections', size=(5,1) ), sg.Text('Use 1 for sequential', text_color="white"), 
		],
		# [sg.Checkbox('JCP', key='pc_jcp', default=True, text_color='black'),
		#  sg.Checkbox('NMTE', key='pc_nmte', default=True, text_color='black'),
		#  sg.Checkbox('VeloVM', key='pc_velovm', default=True, text_color='black'),
		#  sg.Checkbox('FlexConnect Summary', key='pc_fc_summary', default=True, text_color='black'),
		#  sg.Checkbox('Debug', key='pc_debug', default=False, text_color='black'),
		# ],
		under_line(80),
		[sg.Button("Start", change_submits=True, key='pc_start')],
	])

## ... Define more as needed

# ---------------------------------- #
#         EVENT UPDATERS             #
#   list down variables which triggers an event function call -- exec_fn(obj, i)
# ---------------------------------------------------------------------------------------
FPC_EVENT_UPDATORS = {'pc_start',}
# ---------------------------------------------------------------------------------------

# --------------------------------------- #
#         EVENT ITEM UPDATERS             #
#   list down variables which triggers an item update event function -- exec_fn(obj, i, event)
# ---------------------------------------------------------------------------------------
FPC_EVENT_ITEM_UPDATORS = set()


# ---------------------------------- #
#        RETRACTABLE KEYS            #
#  sets of retractable variables , which should be cleared up on clicking clear button
# ---------------------------------------------------------------------------------------
FPC_RETRACTABLES = { 'pc_passphrase', 'pc_device_list',}


# ---------------------------------- #
#        FRAMES DICTIONARY           #
#  Create Frame groups and ascociate frame descriptions for each frames definition to it
# ---------------------------------------------------------------------------------------
FPC_FRAMES_GRP = {
	'DTAC Pre Captures': dtac_pre_capture(),
}

# ... Add more Frame_Groups as necessary

# ---------------------------------------------------------------------------------------
#   Creating 'Buttons' and ascociate each with a group name
# ---------------------------------------------------------------------------------------
FPC_BUTTUN_PALLETE_DIC = OrderedDict()
FPC_BUTTUN_PALLETE_DIC["btn_grp_precap"] = {'key': 'btn1',  'frames': FPC_FRAMES_GRP,  "button_name": "Pre-Captures"}
# ... Add more buttons as necessary


# ================================== #
#  // EVENT_ITEM_UPDATORS //
#    these functions will accept two arguments. first is NGui object iself and
#    second will be [i] item list of object
# ================================================================================

# @activity_finish_popup
def pc_start_executor(obj, i):
	try:
		# -----------------------------------------------------
		#  VERIFICATION
		# -----------------------------------------------------
		CRED_FILE = i['pc_creds_file']
		if not CRED_FILE:
			print_banner("[-] Mandatory Input missing Creds file")
			print_banner("")
			return None

		COMMANDS_FILE = i['pc_cmds_file']
		if not COMMANDS_FILE:
			print_banner("[-] Mandatory Input missing Commands file")
			print_banner("")
			return None

		if not i['pc_device_list']:
			print_banner("[-] Mandatory Input missing Device(s) List")
			print_banner("")
			return None

		if not i['pc_pollers_list']:
			print_banner("[-] Mandatory Input missing Pollers(s) List")
			print_banner("")
			return None

		# -----------------------------------------------------
		#  START EXECUTIONS
		# -----------------------------------------------------
		## Pull all variables from creds.txt ##
		DYN_VARS = pull_variables(CRED_FILE)
		COMMANDS = pull_cmds_lists_dict(COMMANDS_FILE)
		if not COMMANDS or not DYN_VARS: return None

		## Output Path :  Sample path will be  ==> "C:/NFV-PreCheck/date/time LT" 
		CAPTURED_DATE_TIME = str(dt.datetime.today()).split(".")[0].replace(":", ".") 
		CAPTURED_DATE = CAPTURED_DATE_TIME.split()[0]
		CAPTURED_TIME = CAPTURED_DATE_TIME.split()[1][:5] + " LT"
		op_folder = get_output_folder(i)
		OUTPUT_PATH = f"{op_folder}/{CAPTURED_DATE}/{CAPTURED_TIME}"
		obj.event_update_element(pc_output_path={'value': OUTPUT_PATH})	
		CSV_REPORT_FILE_NAME = f"{OUTPUT_PATH}/{obj.custom_var_dict['CSV_REPORT_FILE_NAME']}"
		INTERFACE_SUMMARY_REPORT_FILE_NAME = f"{OUTPUT_PATH}/{obj.custom_var_dict['INTERFACE_SUMMARY_REPORT_FILE_NAME']}"
		CMDS_EXEC_SUMMARY_REPORT_FILE_NAME = f"{OUTPUT_PATH}/{obj.custom_var_dict['CMDS_EXEC_SUMMARY_REPORT_FILE_NAME']}"
		CSV_REPORT_COLS_SEQ = obj.custom_var_dict['CSV_REPORT_COLS_SEQ']

		try:
			# ---------- 1. Identify device ips
			AP = ActionPollers(
				devices          = i['pc_device_list'].splitlines(),
				servers_list     = i['pc_pollers_list'].splitlines(),
				server_auth_user = DYN_VARS['attuid'],
				server_auth_psk  = DYN_VARS['key_file_1024bit'],
				passphrase       = i['pc_passphrase'],
			)
			AP()
			AP.exit()
			AP.print_summary_report()
		except Exception as e:
			print_banner(f"[-] Error Accessing Poller..\n{e}")
			print_banner("")
			return

		try:
			# ----------- 2. Define Capture Parameters
			FCC = FlxConnectCapture(AP)
			FCC.dyn_vars = DYN_VARS
			FCC.commands = COMMANDS
			FCC.output_path = OUTPUT_PATH
			FCC.output_csv_report_file = CSV_REPORT_FILE_NAME
			FCC.output_csv_report_file_col_seq = CSV_REPORT_COLS_SEQ
			FCC.output_intf_summary_report_file = INTERFACE_SUMMARY_REPORT_FILE_NAME
			FCC.output_cmds_exec_summary_report_file = CMDS_EXEC_SUMMARY_REPORT_FILE_NAME
			FCC.max_connections = min(int(i['pc_max_connections']) , 12)
			# FCC.display_final_summary = i['pc_fc_summary']
			# FCC.pc_jcp = i['pc_jcp']
			# FCC.pc_nmte = i['pc_nmte']
			# FCC.pc_velovm = i['pc_velovm']
			# FCC.debug = i['pc_debug']
			# ----------- 3. Capture
			FCC()
		except Exception as e:
			print_banner(f"[-] Error Capturing output..\n{e}")
			print_banner("")
			return

		try:
			# ----------- 4. Gen Reports
			FCC.reports_gen()
		except Exception as e:
			print_banner(f"[-] Error while Generating Report..\n{e}")
			print_banner("")
			return

		print_banner(f"[+] All Activity Finished")
		print_banner("")

	except KeyboardInterrupt:
		print_banner(f"[-] Activity Cancelled")
		print_banner("")


# ================================== #
#  // EVENT_UPDATOR Functions //     #
#   Such functions accept only [i] item list of NGui object. 
# ================================================================================

def update_cache_pc(i):
	try:
		update_cache(CACHE_FILE, pc_creds_file=i['pc_creds_file'])
		update_cache(CACHE_FILE, pc_cmds_file=i['pc_cmds_file'])
		update_cache(CACHE_FILE, cmp_json_pc_json_file=i['cmp_json_pc_json_file'])
		update_cache(CACHE_FILE, cmp_json_pc_pc_files=i['cmp_json_pc_pc_files'])
	except:
		pass

def exec_pc_creds_file_open(i):
	try:
		open_text_file(i['pc_creds_file'])
	except Exception as e:
		print(f"[-] Unable to open file.")
		return False
def exec_pc_cmds_file_open(i):
	try:
		open_text_file(i['pc_cmds_file'])
	except Exception as e:
		print(f"[-] Unable to open file.")
		return False
def exec_pc_output_path_open(i):
	try:
		if i['pc_output_path']:
			open_folder(i['pc_output_path'])
	except Exception as e:
		print(f"[-] Unable to open folder.")
		return False

# ================================== #
#   // EVENT_FUNCTIONS MAPPING  //   #
#    these functions will accept only argument i.e. [i] item list of object
# ================================================================================

FPC_EVENT_FUNCTIONS = {
	'pc_start' : pc_start_executor,
	# 'pc_creds_file': update_cache_pc,
	# 'pc_cmds_file': update_cache_pc,
	'pc_creds_file_open': exec_pc_creds_file_open,
	'pc_cmds_file_open': exec_pc_cmds_file_open,
	'pc_output_path_open': exec_pc_output_path_open,
}


# ================================== #
#   // Other Local Functions  //   #
# ================================== #
## Remove the trailing Date/Time stamp from the provided path.
def get_output_folder(i):
	if not i['pc_output_path']:  return "."
	if i['pc_output_path'].endswith(" LT"):
		return "/".join(i['pc_output_path'].split("/")[:-2])
	return i['pc_output_path']

# ================================================================================
if __name__ == "__main__":
	pass
# ================================================================================
