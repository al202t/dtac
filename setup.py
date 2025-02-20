import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="att_dtac",
    version="0.0.02",
    author="ALIASGAR - ALI",
    author_email="aliasgar.lokhandwala@att.com",
    description="DTAC Engineering Team Tool Set",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/al202t/dtac",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.10',
    install_requires=['pandas', 'openpyxl', 'PySimpleGUI==4.60.5', 'numpy', 'pyfiglet', 'colorama', 'tabulate',
        'xlrd', 'jinja2', 'paramiko', 'netmiko', 'ntc-templates', 'pyyaml', 'attrs', 'textfsm', 'jumpssh',
        'nettoolkit',
        # 'pywin32',                    ## Windows specific library, need to install manually...
    ],
    package_data={
        'nettoolkit.nettoolkit.forms':  ['cable_n_connectors.xlsx', ],
        'nettoolkit.yaml_facts.templates':  ['*.textfsm', ],
    },
)
