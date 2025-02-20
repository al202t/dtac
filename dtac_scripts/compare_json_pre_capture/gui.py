

# -----------------------------------------------------------------------------------
#  Import form items from nettoolkit
# -----------------------------------------------------------------------------------
import PySimpleGUI as sg
from nettoolkit.nettoolkit.forms.formitems import *
from nettoolkit.nettoolkit_common import open_text_file, open_folder
from collections import OrderedDict
import datetime as dt
from itertools import zip_longest

from .device_parameteres_read import DevPara, DevicesPara
from .json_parameters_read    import JsonData
from .compare                 import Verify, Mapper

# -----------------------------------------------------------------------------------
#  Static 
# -----------------------------------------------------------------------------------
OUTPUT_FOLDER = 'C:/NFV-PreCheck'


# -----------------------------------------------------------------------------------
#  Define all your frames here 
# -----------------------------------------------------------------------------------

def dtac_compare_json_data():
	devices_col = sg.Column([
		[sg.Text("Json Devices List", text_color="black"),], 
		[sg.Multiline("", key='cj_json_devices_list', autoscroll=True, size=(30,6), disabled=False),],
	], pad=0)
	pollers_col = sg.Column([
		[sg.Text("Pre-Capture Devices", text_color="black"),], 
		[sg.Multiline("", key='cj_devices_list', autoscroll=True, size=(30,6), disabled=False),],
	], pad=0)
	return sg.Frame(title=None, 
					relief=sg.RELIEF_SUNKEN, 
					layout=[

		[sg.Text('Compare Json Data with Pre-Captures',  font=('TimesNewRoman', 12), text_color="orange"),], 

		[sg.Text('Json file:\t\t', text_color="black"), 
	     sg.InputText(get_cache(CACHE_FILE, 'cj_json_file'), size=(30,1),  key='cj_json_file', change_submits=True,), 
	     sg.FileBrowse(button_color="grey"), sg.Button("open file", change_submits=True, key='cj_json_file_open', button_color="darkgrey"),
	    ],
		[sg.Text('Pre-Capture file(s):\t', text_color="black"), 
	     sg.InputText(get_cache(CACHE_FILE, 'cj_devices_files'), size=(30,1),  key='cj_devices_files', change_submits=True, ), 
	     sg.FileBrowse(button_color="grey"), sg.Button("open file", change_submits=True, key='cj_devices_files_open', button_color="darkgrey"),
	    ],
		[sg.Text('output folder:\t', text_color="black"), 
		 sg.InputText(OUTPUT_FOLDER, key='cj_output_path', size=(30,1)),  
		 sg.FolderBrowse(button_color="orange"), 
		 sg.Button("open", change_submits=True, key='cj_output_path_open', button_color="darkgrey"),
		],
		[sg.Button("Pull Devices", change_submits=True, key='cj_pull_devices')],
		under_line(80),
		#
		[sg.Text('Align/Map the devices', text_color="black"),], 
		[pollers_col, sg.VerticalSeparator(), devices_col],
		[sg.Checkbox('OnScreen Display', key='cj_display', default=True, text_color='black'),
		 sg.Checkbox('Save to File', key='cj_write', default=True, text_color='black'),
		],
		#
		under_line(80),
		[sg.Button("Compare", change_submits=True, key='cj_start')],
		under_line(80),
	])

## ... Define more as needed

# ---------------------------------- #
#         EVENT UPDATERS             #
#   list down variables which triggers an event function call -- exec_fn(obj, i)
# ---------------------------------------------------------------------------------------
CJ_EVENT_UPDATORS = {'cj_pull_devices',}
# ---------------------------------------------------------------------------------------

# --------------------------------------- #
#         EVENT ITEM UPDATERS             #
#   list down variables which triggers an item update event function -- exec_fn(obj, i, event)
# ---------------------------------------------------------------------------------------
CJ_EVENT_ITEM_UPDATORS = set()


# ---------------------------------- #
#        RETRACTABLE KEYS            #
#  sets of retractable variables , which should be cleared up on clicking clear button
# ---------------------------------------------------------------------------------------
CJ_RETRACTABLES = { 'cj_json_file', 'cj_devices_files', 'cj_json_devices_list', 'cj_devices_list'}


# ---------------------------------- #
#        FRAMES DICTIONARY           #
#  Create Frame groups and ascociate frame descriptions for each frames definition to it
# ---------------------------------------------------------------------------------------
CJ_FRAMES_GRP = {
	'Compare Json': dtac_compare_json_data(),
}

# ... Add more Frame_Groups as necessary

# ---------------------------------------------------------------------------------------
#   Creating 'Buttons' and ascociate each with a group name
# ---------------------------------------------------------------------------------------
CJ_BUTTUN_PALLETE_DIC = OrderedDict()
CJ_BUTTUN_PALLETE_DIC["btn_grp_comparejason"] = {'key': 'btn2',  'frames': CJ_FRAMES_GRP,  "button_name": "Compare Json"}
# ... Add more buttons as necessary


# ================================== #
#  // EVENT_ITEM_UPDATORS //
#    these functions will accept two arguments. first is NGui object iself and
#    second will be [i] item list of object
# ================================================================================

# @activity_finish_popup
def exec_cj_pull_devices(obj, i):
	try:
		#  VERIFICATION
		json_file = i['cj_json_file']
		if not json_file:
			print("[-] Mandatory Input missing Json file")
			print("")
			return None

		capture_files = i['cj_devices_files']
		if not capture_files:
			print("[-] Mandatory Input missing Pre-Capture file(s)")
			print("")
			return None

		#  START EXECUTIONS
		try:
			JD = JsonData(json_file)
			DP = DevicesPara(capture_files.split(';'))
			JD()
			DP()
			M = Mapper(jd=JD, dp=DP)
			json_devices = M.json_devices
			capture_devices = M.capture_devices
			obj.event_update_element(cj_json_devices_list={'value': "\n".join(json_devices)})	
			obj.event_update_element(cj_devices_list={'value': "\n".join(capture_devices)})	
		except Exception as e:
			print(f"[-] Error creating device maps")
			return
		print(f"[+] All Activity Finished")

	except KeyboardInterrupt:
		print(f"[-] Activity Cancelled")


# ================================== #
#  // EVENT_UPDATOR Functions //     #
#   Such functions accept only [i] item list of NGui object. 
# ================================================================================

def update_cache_cj(i):
	try:
		update_cache(CACHE_FILE, cj_json_file=i['cj_json_file'])
		update_cache(CACHE_FILE, cj_devices_files=i['cj_devices_files'])
	except:
		pass

def exec_cj_json_file_open(i):
	try:
		open_text_file(i['cj_json_file_open'])
	except Exception as e:
		print(f"[-] Unable to open file.")
		return False
def exec_cj_devices_files_open(i):
	try:
		open_text_file(i['cj_devices_files_open'])
	except Exception as e:
		print(f"[-] Unable to open file.")
		return False

def exec_cj_output_path_open(i):
	try:
		if i['cj_output_path']:
			open_folder(i['cj_output_path'])
	except Exception as e:
		print(f"[-] Unable to open folder.")
		return False

def exec_cj_start(i):
	try:
		#  VERIFICATION
		json_file = i['cj_json_file']
		if not json_file:
			print("[-] Mandatory Input missing Json file")
			print("")
			return None

		capture_files = i['cj_devices_files']
		if not capture_files:
			print("[-] Mandatory Input missing Pre-Capture file(s)")
			print("")
			return None

		#  START EXECUTIONS
		try:
			JD = JsonData(json_file)
			DP = DevicesPara(capture_files.split(';'))
			JD()
			DP()

			hostnames_map = {json_dev: cap_dev 
							 for json_dev, cap_dev in zip_longest(i['cj_json_devices_list'].splitlines(), i['cj_devices_list'].splitlines())}
			folder = i['cj_output_path'] if i['cj_output_path'] else "."

			# // -- Verify Instance -- // #
			V = Verify(jd=JD, dp=DP)
			V.hostnames_map = hostnames_map
			V()
			if i['cj_display']:
				print(V.result_string)                          ## Display result on console
			if i['cj_write']:
				V.results_to_file(folder=folder)                ## send results to file


		except Exception as e:
			print(f"[-] Error creating device maps\n{e}")
			return
		print(f"[+] All Activity Finished")

	except KeyboardInterrupt:
		print(f"[-] Activity Cancelled")

# ================================== #
#   // EVENT_FUNCTIONS MAPPING  //   #
#    these functions will accept only argument i.e. [i] item list of object
# ================================================================================

CJ_EVENT_FUNCTIONS = {
	'cj_pull_devices' : exec_cj_pull_devices,
	'cj_json_file_open': exec_cj_json_file_open,
	'cj_devices_files_open': exec_cj_devices_files_open,
	'cj_start': exec_cj_start,

	'cj_json_file': update_cache_cj,
	'cj_devices_files': update_cache_cj,
	'cj_output_path_open': exec_cj_output_path_open,

}


# ================================== #
#   // Other Local Functions  //   #
# ================================== #
# ## Remove the trailing Date/Time stamp from the provided path.
# def get_output_folder(i):
# 	if not i['pc_output_path']:  return "."
# 	if i['pc_output_path'].endswith(" LT"):
# 		return "/".join(i['pc_output_path'].split("/")[:-2])
# 	return i['pc_output_path']

# ================================================================================
if __name__ == "__main__":
	pass
# ================================================================================
