# tinytail
Cisco ACI log collector

#### Collect all logs:
1.	Copy “onekey.txt”  into APIC CLI.
2.	Download from https

#### Collect range logs:
1.	Copy/vim  “tinytail.py” into APIC.
2.	Run command   “python tinytail.py -f 2020-02-01T00:00:00 -t 2020-02-01T23:59:59”
3.	Download from https.

#### Example:
```bash
apic1# python tinytail.py                 <<<Get all logs.

apic1# python tinytail.py -f 2020-02-01T00:00:00 -t 2020-02-01T23:59:59            <<<Get range logs.

apic1# python tinytail.py -c                    <<<Clean temp files.
2020-02-13 18:08:22,413 - INFO: Tinytail version: Alpha (INTERNAL LAB ONLY)
2020-02-13 18:08:22,420 - INFO: Cleaned all temp files, Have a good day! 😝

apic1# python tinytail.py -h        <<< Get help info
usage: tinytail.py [-h] [-f START] [-t TO] [-v | -c] [-d]

---------------------------------
"Tinytail" APIC log collector
---------------------------------
optional arguments:
  -h, --help     show this help message and exit
  -v, --version  Display version.
  -c, --clean    Clean the tmp directory.

Other options: :
  -f START       Collect date From. eg. 2020-01-02T00:00:00
  -t TO          Collect date To. eg. 2020-01-02T23:59:59
  -d, --debug    Enable debug use this option.
---------------------------------
```
### Troubleshooting log:
```bash
/tmp/tinytail.log             << debug log here.
/tmp/.tac/
```
