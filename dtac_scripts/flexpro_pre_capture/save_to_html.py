# ----------------------------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------------------------
import pandas as pd
from tabulate import tabulate
from colorama import Fore
from nettoolkit.nettoolkit_db import write_to_xl


# ----------------------------------------------------------------------------------------
#  Some PreDefined Static Entries
# ----------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------
#  Some common Functions
# ----------------------------------------------------------------------------------------

def html_file_header(device, file):
	s = f"""
<!DOCTYPE html>
<html><body>
<h1>{device}</h1>
"""
	with open(file, 'w') as f:
		f.write(s)


# writes provided command and its output to given file (append mode)
def cmd_output_to_html_file(cmd, output, file):
	s = f"""
<details>
<summary>{cmd}</summary>
<pre>
{output}
</pre>
</details>
"""
	with open(file, 'a') as f:
		f.write(s)


def html_file_footer(file):
	s = f"""
</body></html>
"""
	with open(file, 'a') as f:
		f.write(s)


# ----------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------
#  main
# ----------------------------------------------------------------------------------------
if __name__ == "__main__":
	pass
# ----------------------------------------------------------------------------------------


