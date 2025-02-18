
# -----------------------------------------------------------------------------------
#  Import form items from nettoolkit
# -----------------------------------------------------------------------------------
import PySimpleGUI as sg
from nettoolkit.nettoolkit.forms.formitems import *
from nettoolkit.nettoolkit_common import open_text_file, open_folder
from nettoolkit import NGui
from collections import OrderedDict
import datetime as dt

from .flex_connect import FlxConnectCapture
from .identify_pollers import ActionPollers
from .common import pull_variables, pull_cmds_lists_dict

# -----------------------------------------------------------------------------------
#  Static 
# -----------------------------------------------------------------------------------
OUTPUT_FOLDER = 'C:/NFV-PreCheck'

# -----------------------------------------------------------------------------------
#  Define all your frames here 
# -----------------------------------------------------------------------------------

def dtac_pre_capture():
	return sg.Frame(title=None, 
					relief=sg.RELIEF_SUNKEN, 
					layout=[

		[sg.Text('Pre-Capture',  font=('TimesNewRoman', 12), text_color="orange"),], 
		[sg.Text('Creds file:\t', text_color="black"), 
	     sg.InputText(get_cache(CACHE_FILE, 'pc_creds_file'), size=(30,1),  key='pc_creds_file', change_submits=True,), 
	     sg.FileBrowse(button_color="grey"), sg.Button("open file", change_submits=True, key='pc_creds_file_open', button_color="darkgrey"),
	    ],
		[sg.Text('Commands file:\t', text_color="black"), 
	     sg.InputText(get_cache(CACHE_FILE, 'pc_cmds_file'), size=(30,1),  key='pc_cmds_file', change_submits=True,), 
	     sg.FileBrowse(button_color="grey"), sg.Button("open file", change_submits=True, key='pc_pc_cmds_file_open', button_color="darkgrey"),
	    ],
		[sg.Text('output folder:\t', text_color="black"), 
		 sg.InputText(OUTPUT_FOLDER, key='pc_output_path', size=(30,1)),  
		 sg.FolderBrowse(button_color="orange"), 
		 sg.Button("open", change_submits=True, key='pc_output_path_open', button_color="darkgrey"),
		],
		[sg.Text("Device(s) List", text_color="black"),], 
		[sg.Multiline("", key='pc_device_list', autoscroll=True, size=(30,6), disabled=False),],
		[sg.Text("Public Key Pass-phrase", text_color="black"), sg.InputText("", password_char='*', key='pc_passphrase', size=(15,1)),],
		[sg.Text('Concurrent connections throttle', text_color="black"), 
		 sg.InputText(50,  key='pc_max_connections', size=(5,1) ), sg.Text('Use 1 for sequential', text_color="white"), 
		],
		[sg.Checkbox('JCP', key='pc_jcp', default=True, text_color='black'),
		 sg.Checkbox('NMTE', key='pc_nmte', default=True, text_color='black'),
		 sg.Checkbox('VeloVM', key='pc_velovm', default=True, text_color='black'),
		 sg.Checkbox('FlexConnect Summary', key='pc_fc_summary', default=False, text_color='black'),
		 sg.Checkbox('Debug', key='pc_debug', default=False, text_color='black'),
		],
		under_line(80),
		[sg.Button("Start", change_submits=True, key='pc_start')],
		under_line(80),
	])

## ... Define more as needed

# ---------------------------------- #
#         EVENT UPDATERS             #
#   list down variables which triggers an event function call -- exec_fn(i)
# ---------------------------------------------------------------------------------------
EVENT_UPDATORS = {'pc_start',}
# ---------------------------------------------------------------------------------------

# --------------------------------------- #
#         EVENT ITEM UPDATERS             #
#   list down variables which triggers an item update event function -- exec_fn(obj, i)
# ---------------------------------------------------------------------------------------
EVENT_ITEM_UPDATORS = set()


# ---------------------------------- #
#        RETRACTABLE KEYS            #
#  sets of retractable variables , which should be cleared up on clicking clear button
# ---------------------------------------------------------------------------------------
RETRACTABLES = { 'pc_passphrase', 'pc_device_list',}


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
BUTTUN_PALLETE_DIC = OrderedDict()
BUTTUN_PALLETE_DIC["btn_grp_precap"] = {'key': 'btn1',  'frames': FPC_FRAMES_GRP,  "button_name": "Pre-Captures"}
# ... Add more buttons as necessary


# ================================== #
#  // EVENT_ITEM_UPDATORS //
#    these functions will accept two arguments. first is NGui object iself and
#    second will be [i] item list of object
# ================================================================================

@activity_finish_popup
def pc_start_executor(obj, i):
	try:
		# -----------------------------------------------------
		#  VERIFICATION
		# -----------------------------------------------------
		CRED_FILE = i['pc_creds_file']
		if not CRED_FILE:
			print("[-] Mandatory Input missing Creds file")
			print("")
			return None

		COMMANDS_FILE = i['pc_cmds_file']
		if not COMMANDS_FILE:
			print("[-] Mandatory Input missing Commands file")
			print("")
			return None

		if not i['pc_device_list']:
			print("[-] Mandatory Input missing Device(s) List")
			print("")
			return None

		# -----------------------------------------------------
		#  START EXECUTIONS
		# -----------------------------------------------------
		## Pull all variables from creds.txt ##
		DYN_VARS = pull_variables(CRED_FILE)
		COMMANDS = pull_cmds_lists_dict(COMMANDS_FILE)

		## Output Path :  Sample path will be  ==> "C:/NFV-PreCheck/date/time LT" 
		CAPTURED_DATE_TIME = str(dt.datetime.today()).split(".")[0].replace(":", ".") 
		CAPTURED_DATE = CAPTURED_DATE_TIME.split()[0]
		CAPTURED_TIME = CAPTURED_DATE_TIME.split()[1][:5] + " LT"
		OUTPUT_PATH = i['pc_output_path'] + '/' + CAPTURED_DATE + '/' + CAPTURED_TIME
		obj.event_update_element(pc_output_path={'value': OUTPUT_PATH})	

		# ---------- 1. Identify device ips
		AP = ActionPollers(
			devices          = i['pc_device_list'].splitlines(),
			server_auth_user = DYN_VARS['attuid'],
			server_auth_psk  = DYN_VARS['key_file_1024bit'],
			passphrase       = i['pc_passphrase'],
		)
		AP()
		AP.exit()
		AP.print_summary_report()

		# ----------- 2. Define Capture Parameters
		FCC = FlxConnectCapture(AP)
		FCC.dyn_vars = DYN_VARS
		FCC.commands = COMMANDS
		FCC.output_path = OUTPUT_PATH
		FCC.max_connections = int(i['pc_max_connections'])
		FCC.display_final_summary = i['pc_fc_summary']
		FCC.pc_jcp = i['pc_jcp']
		FCC.pc_nmte = i['pc_nmte']
		FCC.pc_velovm = i['pc_velovm']
		FCC.debug = i['pc_debug']
		# ----------- 3. Capture
		FCC()
		# ----------- 4. Gen Reports
		FCC.reports_gen()

		print(f"[+] All Activity Finished", 'white')

	except KeyboardInterrupt:
		print(f"[-] Activity Cancelled", 'white')


# ================================== #
#  // EVENT_UPDATOR Functions //     #
#   Such functions accept only [i] item list of NGui object. 
# ================================================================================

def update_cache_pc(i):
	update_cache(CACHE_FILE, pc_creds_file=i['pc_creds_file'])
	update_cache(CACHE_FILE, pc_cmds_file=i['pc_cmds_file'])
	update_cache(CACHE_FILE, cmp_json_pc_json_file=i['cmp_json_pc_json_file'])
	update_cache(CACHE_FILE, cmp_json_pc_pc_files=i['cmp_json_pc_pc_files'])

def exec_pc_creds_file_open(i):
	open_text_file(i['pc_creds_file'])
def exec_pc_cmds_file_open(i):
	open_text_file(i['pc_cmds_file'])
def exec_pc_output_path_open(i):
	if i['pc_output_path']:
		open_folder(i['pc_output_path'])
def exec_cmp_json_pc_output_path_open(i):
	if i['cmp_json_pc_output_path']:
		open_folder(i['cmp_json_pc_output_path'])


# ================================== #
#   // EVENT_FUNCTIONS MAPPING  //   #
#    these functions will accept only argument i.e. [i] item list of object
# ================================================================================

FPC_EVENT_FUNCTIONS = {
	'pc_start' : pc_start_executor,
	'pc_creds_file': update_cache_pc,
	'pc_cmds_file': update_cache_pc,
	'pc_creds_file_open': exec_pc_creds_file_open,
	'pc_cmds_file_open': exec_pc_cmds_file_open,
	'pc_output_path_open': exec_pc_output_path_open,
}
