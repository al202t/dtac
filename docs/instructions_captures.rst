Capture Instructions
=================================================

Requirements
----------------

	1. creds.txt file path ( Fixed as C:\PreQA6\creds.txt )  --> File can be opened and edited by clicking open file button
	2. commands list tex file ( Fixed as C:\PreQA6\flexware_pre_capture_commands.txt ) --> File can be opened and edited by clicking open file button
	3. output folder ( Fixed as C:\NFV-PreCheck ) --> Folder can be access quickly by clicking open button
	4. Pollers List ( 4* Pollers are added, Can be modified as need ) ( Pollers will be selected round robin base to access the devices parallelly if multiple devices provided )
	5. Devices (Hostname) List ( JZZ/JDM names ) ( N-Number of devices can be entered. Max 12 devices parallel processing has been capped. More devices will be executed in batch of 12s )
	6. passphrase: (optional) - Provide if it is set while public/private key pair generation.

-----------------

* **Creds.txt** and **flexware_pre_capture_commands.txt** sample files are uploaded along with script.

Steps
---------------

* Click on Start to start executing scipt once all necessary inputs are entered.
* Execution progress can be seen on console/command prompt. 
* Outputs will be stored in C:\NFV-PreCheck Folder.  Everytime while execute, it will create a <DATE> folder \ <TIME LT> folder. All output files will reside within it. 

