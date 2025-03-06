
# -----------------------------------------------------------------------------------
#  Import form items from nettoolkit
# -----------------------------------------------------------------------------------
import PySimpleGUI as sg
from nettoolkit.nettoolkit.forms.formitems import *
from nettoolkit.nettoolkit_common import open_text_file, open_folder
from collections import OrderedDict
import datetime as dt

from .edge_connect import DevicesCapture
from .identify_pollers import ActionPollers
from .common import pull_variables, pull_cmds_lists_dict
from .colorprint import print_banner

# -----------------------------------------------------------------------------------
#  Static 
# -----------------------------------------------------------------------------------
CREDS_FILE = 'C:/PreQA6/creds.txt'
cEG_CMDS_FILE  = 'C:/PreQA6/cEdge_check_commands.txt'
vEG_CMDS_FILE  = 'C:/PreQA6/vEdge_check_commands.txt'
OUTPUT_FOLDER = 'C:/NFV-PreCheck'
POLLERS = [
	'rlpv13447.gcsc.att.com',
]

# -----------------------------------------------------------------------------------
#  Define all your frames here 
# -----------------------------------------------------------------------------------

def dtac_edge_capture():
	devices_col = sg.Column([
		[sg.Text("Device(s) List", text_color="black"),], 
		[sg.Multiline("", key='ec_device_list', autoscroll=True, size=(30,6), disabled=False),],
		[sg.Text("User:", text_color="black"), sg.InputText("", password_char='*', key='ec_gtac_id', size=(6,1)),
		 sg.Text("Password:", text_color="black"), sg.InputText("", password_char='*', key='ec_gtac', size=(6,1)),],
		[sg.Text('Concurrent connections:', text_color="black"), 
		 sg.InputText(12,  key='ec_max_connections', size=(6,1) ),],
	], pad=0)
	pollers_col = sg.Column([
		[sg.Text("Pollers(s) List", text_color="black"),], 
		[sg.Multiline("\n".join(POLLERS), key='ec_pollers_list', autoscroll=True, size=(30,7), disabled=False),],
		[sg.Text("Pass-phrase:", text_color="black"), sg.InputText("", password_char='*', key='ec_passphrase', size=(8,1)),],
	], pad=0)
	return sg.Frame(title=None, 
					relief=sg.RELIEF_SUNKEN, 
					layout=[

		[ sg.Text('Pre-Capture\t',  font=('TimesNewRoman', 12), text_color="orange"),
		  sg.Radio('vEdge', group_id=1, key='ec_vedge', change_submits=True, default=True), 
		  sg.Radio('cEdge', group_id=1, key='ec_cedge', change_submits=True, ),
		], 
		[sg.Text('Creds file:\t', text_color="black"), 
	     sg.InputText(CREDS_FILE, size=(30,1),  key='ec_creds_file' ), 
	     sg.FileBrowse(button_color="grey"), 
		 sg.Button("open file", change_submits=True, key='ec_creds_file_open', button_color="darkgrey"),
	    ],
		[sg.Text('Commands file:\t', text_color="black"), 
	     sg.InputText(vEG_CMDS_FILE, size=(30,1),  key='ec_cmds_file'), 
	     sg.FileBrowse(button_color="grey"), 
		 sg.Button("open file", change_submits=True, key='ec_cmds_file_open', button_color="darkgrey"),
	    ],
		[sg.Text('Output folder:\t', text_color="black"), 
		 sg.InputText(OUTPUT_FOLDER, key='ec_output_path', size=(30,1)),  
		 sg.FolderBrowse(button_color="orange"), 
		 sg.Button("open", change_submits=True, key='ec_output_path_open', button_color="darkgrey"),
		],
		under_line(80),
		#
		[pollers_col, sg.VerticalSeparator(), devices_col],
		#
		under_line(80),
		[sg.Button("Start", change_submits=True, key='ec_start')],
	])

## ... Define more as needed

# ---------------------------------- #
#         EVENT UPDATERS             #
#   list down variables which triggers an event function call -- exec_fn(obj, i)
# ---------------------------------------------------------------------------------------
CEC_EVENT_UPDATORS = {'ec_start', 'ec_cedge', 'ec_vedge'}
# ---------------------------------------------------------------------------------------

# --------------------------------------- #
#         EVENT ITEM UPDATERS             #
#   list down variables which triggers an item update event function -- exec_fn(obj, i, event)
# ---------------------------------------------------------------------------------------
CEC_EVENT_ITEM_UPDATORS = set()


# ---------------------------------- #
#        RETRACTABLE KEYS            #
#  sets of retractable variables , which should be cleared up on clicking clear button
# ---------------------------------------------------------------------------------------
CEC_RETRACTABLES = { 'ec_passphrase', 'ec_device_list', 'ec_gtac'}


# ---------------------------------- #
#        FRAMES DICTIONARY           #
#  Create Frame groups and ascociate frame descriptions for each frames definition to it
# ---------------------------------------------------------------------------------------
CEC_FRAMES_GRP = {
	'Cisco Edge Captures': dtac_edge_capture(),
}

# ... Add more Frame_Groups as necessary

# ---------------------------------------------------------------------------------------
#   Creating 'Buttons' and ascociate each with a group name
# ---------------------------------------------------------------------------------------
CEC_BUTTUN_PALLETE_DIC = OrderedDict()
CEC_BUTTUN_PALLETE_DIC["btn_grp_edge_capture"] = {'key': 'btn3',  'frames': CEC_FRAMES_GRP,  "button_name": "Viptela/Cisco"}
# ... Add more buttons as necessary


# ================================== #
#  // EVENT_ITEM_UPDATORS //
#    these functions will accept two arguments. first is NGui object iself and
#    second will be [i] item list of object
# ================================================================================


def exec_ec_vedge(obj, i):
	obj.event_update_element(ec_cmds_file={'value': vEG_CMDS_FILE})	
def exec_ec_cedge(obj, i):
	obj.event_update_element(ec_cmds_file={'value': cEG_CMDS_FILE})	

# @activity_finish_popup
def ec_start_executor(obj, i):
	# try:
		# -----------------------------------------------------
		#  VERIFICATION
		# -----------------------------------------------------
		CRED_FILE = i['ec_creds_file']
		if not CRED_FILE:
			print_banner("[-] Mandatory Input missing Creds file")
			print_banner("")
			return None

		COMMANDS_FILE = i['ec_cmds_file']
		if not COMMANDS_FILE:
			print_banner("[-] Mandatory Input missing Commands file")
			print_banner("")
			return None

		if not i['ec_device_list']:
			print_banner("[-] Mandatory Input missing Device(s) List")
			print_banner("")
			return None

		if not i['ec_pollers_list']:
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
		COMMANDS = ['show lic udi', 'show sdwan run', ]

		## Output Path :  Sample path will be  ==> "C:/NFV-PreCheck/date/time LT" 
		CAPTURED_DATE_TIME = str(dt.datetime.today()).split(".")[0].replace(":", ".") 
		CAPTURED_DATE = CAPTURED_DATE_TIME.split()[0]
		CAPTURED_TIME = CAPTURED_DATE_TIME.split()[1][:5] + " LT"
		op_folder = get_output_folder(i)
		OUTPUT_PATH = f"{op_folder}/{CAPTURED_DATE}/{CAPTURED_TIME}"
		obj.event_update_element(ec_output_path={'value': OUTPUT_PATH})	
		CSV_REPORT_FILE_NAME = f"{OUTPUT_PATH}/{obj.custom_var_dict['CSV_REPORT_FILE_NAME']}"
		INTERFACE_SUMMARY_REPORT_FILE_NAME = f"{OUTPUT_PATH}/{obj.custom_var_dict['INTERFACE_SUMMARY_REPORT_FILE_NAME']}"
		CMDS_EXEC_SUMMARY_REPORT_FILE_NAME = f"{OUTPUT_PATH}/{obj.custom_var_dict['CMDS_EXEC_SUMMARY_REPORT_FILE_NAME']}"
		CSV_REPORT_COLS_SEQ = obj.custom_var_dict['CSV_REPORT_COLS_SEQ']

		try:
			# ---------- 1. Identify device ips
			AP = ActionPollers(
				devices          = i['ec_device_list'].splitlines(),
				servers_list     = i['ec_pollers_list'].splitlines(),
				server_auth_user = DYN_VARS['attuid'],
				server_auth_psk  = DYN_VARS['key_file'],
				passphrase       = i['ec_passphrase'],
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
			FCC = DevicesCapture(AP)
			FCC.device_auth_un = i['ec_gtac_id']
			FCC.device_auth_pw = i['ec_gtac']
			FCC.dyn_vars = DYN_VARS
			FCC.commands = COMMANDS
			FCC.output_path = OUTPUT_PATH
			FCC.output_csv_report_file = CSV_REPORT_FILE_NAME
			FCC.output_csv_report_file_col_seq = CSV_REPORT_COLS_SEQ
			FCC.output_intf_summary_report_file = INTERFACE_SUMMARY_REPORT_FILE_NAME
			FCC.output_cmds_exec_summary_report_file = CMDS_EXEC_SUMMARY_REPORT_FILE_NAME
			FCC.max_connections = min(int(i['ec_max_connections']) , 12)
			FCC.debug = True 

			# ----------- 3. Capture
			# FCC()
		except Exception as e:
			print_banner(f"[-] Error Capturing output..\n{e}")
			print_banner("")
			return
		FCC()

		try:
			# ----------- 4. Gen Reports
			FCC.reports_gen()
		except Exception as e:
			print_banner(f"[-] Error while Generating Report..\n{e}")
			print_banner("")
			return

		print_banner(f"[+] All Activity Finished")
		print_banner("")

	# except KeyboardInterrupt:
	# 	print_banner(f"[-] Activity Cancelled")
	# 	print_banner("")


# ================================== #
#  // EVENT_UPDATOR Functions //     #
#   Such functions accept only [i] item list of NGui object. 
# ================================================================================

def update_cache_pc(i):
	try:
		update_cache(CACHE_FILE, ec_creds_file=i['ec_creds_file'])
		update_cache(CACHE_FILE, ec_cmds_file=i['ec_cmds_file'])
	except:
		pass

def exec_ec_creds_file_open(i):
	try:
		open_text_file(i['ec_creds_file'])
	except Exception as e:
		print(f"[-] Unable to open file.")
		return False
def exec_ec_cmds_file_open(i):
	try:
		open_text_file(i['ec_cmds_file'])
	except Exception as e:
		print(f"[-] Unable to open file.")
		return False
def exec_ec_output_path_open(i):
	try:
		if i['ec_output_path']:
			open_folder(i['ec_output_path'])
	except Exception as e:
		print(f"[-] Unable to open folder.")
		return False

# ================================== #
#   // EVENT_FUNCTIONS MAPPING  //   #
#    these functions will accept only argument i.e. [i] item list of object
# ================================================================================

CEC_EVENT_FUNCTIONS = {
	'ec_start' : ec_start_executor,
	'ec_creds_file_open': exec_ec_creds_file_open,
	'ec_cmds_file_open': exec_ec_cmds_file_open,
	'ec_output_path_open': exec_ec_output_path_open,
	'ec_cedge': exec_ec_cedge,
	'ec_vedge': exec_ec_vedge,
}


# ================================== #
#   // Other Local Functions  //   #
# ================================== #
## Remove the trailing Date/Time stamp from the provided path.
def get_output_folder(i):
	if not i['ec_output_path']:  return "."
	if i['ec_output_path'].endswith(" LT"):
		return "/".join(i['ec_output_path'].split("/")[:-2])
	return i['ec_output_path']

# ================================================================================
if __name__ == "__main__":
	pass
# ================================================================================
