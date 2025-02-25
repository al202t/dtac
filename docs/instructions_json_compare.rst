JSON Capture Instructions
=================================================

Requirements
----------------
	1. json data output from Ericsson portal
	2. Pre-capture results (.log files) for the devices


Steps
-------------

	1. Ericsson portal select top level (order level), take **data json** output to a file. ( extension should be **.json** ) 
	2. Capture the output of the devices using Pre-Capture tab.
	3. Select a Json File.
	4. Select respective devices pre-capture files.
	5. Output Folder ( Fixed as C:\NFV-PreCheck ) --> Folder can be access quickly by clicking open button

Once provided json and precapture files,  Click on ``Pull Devices`` button. It will pull the devices details and present in two device lists.

	6. Map the devices between pre-capture list v/s json list horizontally.  Move/shuffle device up/down (cut-paste) if require.

Once mapping done, Click on ``Compare`` button. 

Result will appear on command/console window  and/or to output file based on additional option selected.

	7. Onscreen display - to see result in console window
	8. Save to file  - to write output to a text output file. ( output file name will be starting 13 characters from a device hostname )

Output will be stored under C:\NFV-PreCheck\<DATE>  Folder.

