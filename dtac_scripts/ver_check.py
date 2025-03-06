
# ===============================================================================
#   IMPORTS
# ===============================================================================
from dataclasses import dataclass
import paramiko
import os
import errno
from pathlib import Path
import stat
import win32com
import requests

# ===============================================================================
#   Local Functions
# ===============================================================================
def get_version(init_file):
	with open(init_file, 'r') as f:
		lines = f.readlines()
	for line in lines:
		if line.startswith("__version__"):
			return float(line.split("=")[-1].strip())

@dataclass
class SFTP_Session():
	server: str
	username: str
	key_filename: str
	passphrase: str
	remote_project_path: str

	def __call__(self):
		self.init_file = "__init__.py"
		self.get_sftp_connection()
		self.tmp_folder = self.get_a_tmp_folder()
		self.get_tmp_int_file()


	def get_sftp_connection(self):
		try:
			self.ssh = paramiko.SSHClient()
			self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			self.ssh.connect(self.server, username=self.username, key_filename=self.key_filename, passphrase=self.passphrase)
			self.sftp = self.ssh.open_sftp()
		except:
			return None

	def get_a_tmp_folder(self):
		return Path(str(win32com.__gen_path__))

	def get_tmp_int_file(self):
		self.tmp_int_file = self.tmp_folder.joinpath(self.init_file)

	def get_tmp_remote_init_file(self):
		self.sftp.get(os.path.join(self.remote_project_path, self.init_file), self.tmp_int_file)
		return self.tmp_int_file

	def download_files(self, remote_dir, local_dir):
		if not self.exists_remote(remote_dir):
			return

		if not os.path.exists(local_dir):
			os.mkdir(local_dir)

		for filename in self.sftp.listdir(remote_dir):
			if filename.endswith(".exe"): continue
			if stat.S_ISDIR(self.sftp.stat(remote_dir + filename).st_mode):
				self.download_files(remote_dir + filename + '/', os.path.join(local_dir, filename))
			else:
				if not os.path.isfile(os.path.join(local_dir, filename)):
					self.sftp.get(remote_dir + filename, os.path.join(local_dir, filename))

	def download_exe_file(self, version, local_dir):
		localp = Path(local_dir).absolute()
		if not self.exists_remote(self.remote_project_path):
			return

		if not os.path.exists(local_dir):
			os.mkdir(local_dir)

		for filename in self.sftp.listdir(self.remote_project_path):
			if filename.endswith(f"dtac_script_gui_v{version}.exe"):
				self.sftp.get(os.path.join(self.remote_project_path, filename), os.path.join(localp, filename))


	def exists_remote(self, path):
		try:
			self.sftp.stat(path)
		except IOError as e:
			if e.errno == errno.ENOENT:
				return False
			raise
		else:
			return True

	def get_max_available_exec_version(self):
		versions = set()
		for file in self.sftp.listdir(self.remote_project_path):
			if not file.endswith(".exe"): continue
			if not "dtac_script_gui_v" in file: continue
			version = file.split("dtac_script_gui_v")[-1].split(".")[0]
			if not version: continue
			try:
				versions.add(float(version))
			except:
				continue
		if not versions:
			return 0
		return max(versions)


# ===============================================================================
#   DO
# ===============================================================================

def version_check(local_version, server, username, key_filename, passphrase, remote_project_path):

	share_type = 'exe'

	# establish a new sftp session with server, remoteprojectpath is folder where script is loaded
	# get the init file to a tmp folder and read the version from that file 
	try:
		SS = SFTP_Session(server=server, username=username, key_filename=key_filename, passphrase=passphrase, remote_project_path=remote_project_path)
		SS()
		if share_type == 'raw':
			tmp_int_file = SS.get_tmp_remote_init_file()
			remote_version = get_version(tmp_int_file)
		if share_type == 'exe':
			remote_version = SS.get_max_available_exec_version()
	except:
		print(f"[-] Error Retriving the server copy version. (Version check will be skipped)")
		return False

	# compare both versions
	if local_version is None:
		print(f"[-] There is an updated version [{remote_version}] available on server, you are missing with that.")
	elif remote_version > local_version:
		print(f"[-] There is an updated version [{remote_version}] available on server [Your local version is {local_version}].")
	else:
		print(f"[+] Your version is up to date")
		return True
	print(f"[+] Starting auto-download. It will take a while. Do NOT Interrupt. Wait to completion")
	if share_type == 'raw':
		SS.download_files(remote_project_path, ".") 
	if share_type == 'exe':
		SS.download_exe_file(remote_version, ".") 

	print(f"[+] Auto download completed")
	print(f"[+] Please restart the script with new file")
	return False

# read a text file, and returns content as list of lines
def text_file_content(file):
	with open(file, 'r') as f: 
		lines = f.readlines()
	return lines

def pull_variables(cred_file):
	creds_variables = {}
	try:
		tfc = text_file_content(cred_file)
	except Exception as e:
		print(f"[-] Creds File read error\n{e}")
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
			print("[-] variable pull failed for: " + l)

	return creds_variables


def version_check_by_file_name(remote_project_path):
	versions = set()
	for file in os.listdir(remote_project_path):
		if not file.endswith(".exe"): continue
		if not "dtac_script_gui_v" in file: continue
		version = file.split("dtac_script_gui_v")[-1].split(".")[0]
		if not version: continue
		try:
			versions.add(int(version))
		except:
			continue
	return versions


def get_files_list(url, file_starts_with):
	response = requests.get(url)
	files = []
	if response.status_code == 200:
		for line in response.iter_lines():
			line = str(line)
			fs = f'<a href="{file_starts_with}'
			if fs in line:
				files.append(f'{file_starts_with}{line.split(fs)[-1]}'.split('"')[0])
	return files

def version_check_on_schedule_web(local_version, remote_url, file_starts_with):
	remote_files = get_files_list(remote_url, file_starts_with)
	remote_versions = []
	for file in remote_files:		
		try:
			remote_versions.append(float(file.lower().split(file_starts_with)[-1].split(".")[0]))
		except:
			pass
	# remote_versions.append(1.1)      #### test line
	max_version = max(remote_versions) if remote_versions else 0		
	if max_version > local_version:
		print(f"[-] There is an updated version [{max_version}] available on server [Your local version is {local_version}].")
		return max_version
	print(f"[+] Your version is up to date")
	return 0

def download_file(url, file, dest='.'):
	print(f"[+] Downloading the latest copy, please wait")
	response = requests.get(url+str(file))
	if response.status_code == 200:
		with open(f'{dest}/{file}', 'wb') as f:
			print(f"[+] Saving the file")
			f.write(response.content)
		print(f"[+] Updated file downloaded")
		print(f"[+] Please restart the script with new file")
	else:
		print(f"[-] Unable to Download the file. Failed")


# ===============================================================================
#   END
# ===============================================================================