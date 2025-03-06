

# ---------------- [Package] ---------------- #
## --- IMPORTS --- ##

from .dtac_scripts.ver_check import version_check, version_check_by_file_name, get_version, version_check_on_schedule_web, download_file

## --- DECLARE --- ##

__all__ = [

]

## --- INFO --- ##
__version__ = 2.0
__doc__ = '''AT&T DTAC SD Automation'''


def version():
	return __version__

def doc_str():
	return __doc__