#!/usr/bin/env python

import argparse
import logging
import subprocess
import re
import os
import time
start_time = time.time()
showList = """
date
date +"%Z %z"
pstree
ps -aux
hostname -I
hostname -a
netstat -tuan
route -n
ifconfig -a
df -h
acidiag fnvread
acidiag rvread
acidiag avread
acidiag fnvreadex
acidiag journal
acidiag hwcheck
acidiag version
version
show cores
show switch
show controller
"""
recordNameList = """
eventRecord
"""

version = 'Alpha (INTERNAL ONLY)  yuxuliu@cisco.com'

fileFormatter = logging.Formatter(
    "%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s : %(message)s")
consoleFormatter = logging.Formatter(
    "%(asctime)s - %(levelname)s: %(message)s")
logFile = logging.FileHandler("/tmp/tinytail.log")
logFile.setFormatter(fileFormatter)

logConsole = logging.StreamHandler()
logConsole.setFormatter(consoleFormatter)
logger = logging.getLogger()

logger.setLevel(logging.DEBUG)
logFile.setLevel(logging.DEBUG)         # logfile always use DEBUG level.
# console log using INFO level bug can be set to others using cmd args (-d).
logConsole.setLevel(logging.INFO)

logger.addHandler(logFile)
logger.addHandler(logConsole)

# logger.debug('DEBUG')
# logger.info('INFO')
# logger.warning('WARN')
# logger.error('ERRO')
# logger.critical('CRIT')


class apicCollector(object):
    def __init__(self):
        self.page_size = 50000
        parser = argparse.ArgumentParser(description="""
---------------------------------
"Tinytail" APIC log collector
---------------------------------
        yuxuliu@cisco.com
****** CISCO INTERNAL ONLY ******
---------------------------------
""", epilog="""
---------------------------------
        """, formatter_class=argparse.RawTextHelpFormatter)

        mutuallyGroup = parser.add_mutually_exclusive_group()
        otherGroup = parser.add_argument_group('Other options: ')
        otherGroup.add_argument(
            "-f", help="Collect date From. eg. 2020-01-02T00:00:00", dest="start")
        otherGroup.add_argument(
            "-t", help="Collect date To. eg. 2020-01-02T23:59:59", dest="to")
        mutuallyGroup.add_argument(
            "-v", "--version", help="Display version.", action="store_true")
        mutuallyGroup.add_argument(
            "-c", "--clean", help="Clean the tmp directory.", action="store_true")
        otherGroup.add_argument(
            "-d", "--debug", help="Enable debug use this option.", action="store_true"
        )

        self.args = parser.parse_args()

    def execCmd(self, CMD):
        process = subprocess.Popen(
            args=CMD, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        output, std_err = process.communicate()
        logger.debug("Trying to run CMD: " + "[ \"" + CMD + "\" ]")
        if std_err:
            logger.error(std_err)
        if process.returncode != 0:
            logger.error("Return code: " +
                         str(process.returncode) + " Context: "+str(output))
        return(process.returncode)

    def initDir(self):
        logger.info("[Phase 0]: Start. Init directory and session log.")
        self.execCmd(
            "mkdir -p /tmp/.tac/commands/ && mkdir -p /tmp/.tac/logFiles/")
        logger.info("[Phase 0]: Done. Created tmp dir: /tmp/.tac/")

    def cleanUp(self):
        returncode = self.execCmd(
            "rm -rf /tmp/.tac/ && rm -rf /tmp/tinytail.log")
        if returncode == 0:
            logger.info("Cleaned all temp files, Have a good day! :P")
        else:
            logger.error("Clean the dir: /tmp/.tac/ FAILED")

    def collectShowCmds(self):
        self.initDir()
        logger.info("[Phase 1]: Start. Collect 'show' commands.")
        for cmdItem in showList.splitlines():
            if cmdItem.strip(" ").__len__() == 0:
                pass
            else:
                cmdItemRun = cmdItem + " >/tmp/.tac/commands/" + \
                    cmdItem.replace(" ", "_")+".log"
                logger.info(" SUCCESS: " + "/tmp/.tac/commands/" +
                            cmdItem.replace(" ", "_") + ".log")
                self.execCmd(CMD=cmdItemRun)
        logger.info("[Phase 1]: Done. Collect 'show' commands success.")

    def collectXmlFiles(self, cmdlist, shell=False):
        linelist = []
        p = subprocess.Popen(args=cmdlist, shell=shell, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        for line in iter(p.stdout.readline, b''):
            linelist.append(line.rstrip())
        return linelist

    def splitPage(self, recordName, startTime=None, endTime=None):
        A = "icurl \'http://localhost:7777/api/class/"+recordName+".xml?"
        C = "order-by="+recordName+".created|desc&page-size=1\'"
        try:
            logger.info("[Phase 2]: Start read page number: \""+recordName +
                        "\" startTime: "+str(startTime) + " endTime: "+str(endTime))
            CMD = ""
            if startTime == None and endTime == None:
                # no startTime no endTime
                CMD = A+C
            elif startTime != None and endTime != None:
                # with startTime and endtime
                B = "query-target-filter=and(and(gt(%s.created,\"%s\"))and(lt(%s.created,\"%s\")))&" % (
                    recordName, str(startTime), recordName, str(endTime))
                CMD = A + B + C
            elif startTime != None and endTime == None:
                # with startTime only
                B = "query-target-filter=gt('%s'.created,'%s')&" % (
                    recordName, str(startTime))
                CMD = A+B+C
            elif startTime == None and endTime != None:
                # with endTime only
                B = "query-target-filter=lt('%s'.created,'%s')&" % (
                    recordName, str(endTime))
                CMD = A+B+C
            logger.debug("DUMP: read page_number: "+recordName +
                         " startTime: "+str(startTime) + " endTime: "+str(endTime) + CMD)
            sumItem = self.collectXmlFiles(cmdlist=CMD, shell="bash")
            re_number = re.search("(?<=imdata totalCount=\")\d+", sumItem[3])
            total_number = re_number.group(0)
            logger.info("[Phase 2]: There were: \"" + str(total_number) +
                        "\" itmes in: \"" + recordName+"\"")
            page_number = (int(total_number) / int(self.page_size)) + 1
            logger.info("[Phase 2]: \"" + recordName + "\" split to: \"" +
                        str(page_number) + "\" page. page_size: " + str(self.page_size))
            return page_number
        except Exception as e:
            logger.error("Failed to read: " + recordName +
                         " page number: "+str(e))

    def collectPages(self, recordName, page_number, startTime=None, endTime=None):
        for page in range(0, page_number):
            A = "icurl \'http://localhost:7777/api/class/"+recordName+".xml?"
            C = "order-by=%s.created|desc&page-size=%s&page=%s'" % (
                recordName, str(self.page_size), str(page))
            fileDestnation = " >/tmp/.tac/logFiles/" + \
                recordName+"-"+str(page+1)+".xml"
            logger.info("(" + str(page+1) + "/"+str(page_number) + ") COLLECT: \"" + recordName +
                        "\"")
            CMD = ""
            if startTime == None and endTime == None:
                # no startTime no endTime
                CMD = A+C
            elif startTime != None and endTime != None:
                # with startTime and endtime
                B = "query-target-filter=and(and(gt(%s.created,\"%s\"))and(lt(%s.created,\"%s\")))&" % (
                    recordName, startTime, recordName, str(endTime))
                CMD = A + B + C
            elif startTime != None and endTime == None:
                # with startTime only
                B = "query-target-filter=gt(%s.created,\"%s\")&" % (
                    recordName, str(startTime))
                CMD = A+B+C
            elif startTime == None and endTime != None:
                # with endTime only
                B = "query-target-filter=lt(%s.created,\"%s\")&" % (
                    recordName, str(endTime))
                CMD = A+B+C
            try:
                CMD = CMD + fileDestnation
                logger.debug("Dump CMD and Dst: " + CMD)

                self.collectXmlFiles(cmdlist=CMD, shell="bash")
                logger.info("(" + str(page+1) + "/" +
                            str(page_number) + ") SUCCESS: \"" + recordName+"\"" + fileDestnation)
            except Exception as e:
                logger.error("Collect: " + recordName +
                             " page: "+str(page) + " failed: "+str(e))

    def zipAllfiles(self):
        self.execCmd(
            CMD="rm -rf /data/techsupport/tinytail.tgz && cp -a /tmp/tinytail.log /tmp/.tac/")
        zipPath = '/tmp/.tac/'
        zipDestnation = '/data/techsupport/tinytail.tgz'
        self.execCmd(CMD="tar -czvf  " + zipDestnation + " "+zipPath)


if __name__ == "__main__":
    myApicCollector = apicCollector()
    if myApicCollector.args.debug == True:
        # If enable debug, change the logging level to DEBUG.
        logConsole.setLevel(logging.DEBUG)

    logger.info("Tinytail version: " + version)
    # Debug output app version
    logger.debug(myApicCollector.args)
    # Dump all options
    myApicCollector.start = True

    if myApicCollector.args.version == True:
        # Version option to print app version
        print("Tinytail version: " + version)
        myApicCollector.start = False

    if myApicCollector.args.clean == True:
        # clean option to clean the tmp dir and log files
        myApicCollector.cleanUp()
        myApicCollector.start = False

    if myApicCollector.start == True:
        # Trigger log collector
        logger.debug("START COLLECT TRIGGERD")
        try:
            myApicCollector.collectShowCmds()
            logger.info("[Phase 2]: Start. Collect xml files.")
            for recordName in recordNameList.splitlines():
                if recordName.strip(" ").__len__() == 0:
                    pass
                else:
                    mypage_number = myApicCollector.splitPage(
                        recordName=recordName, startTime=myApicCollector.args.start, endTime=myApicCollector.args.to)
                    myApicCollector.collectPages(recordName=recordName, page_number=mypage_number,
                                                 startTime=myApicCollector.args.start, endTime=myApicCollector.args.to)
            logger.info("[Phase 2]: Done. Collect xml files success")
            logger.info("[Phase 3]: Start. Zip all logs to web directory.")
            myApicCollector.zipAllfiles()
            logger.info("[Phase 3]: Done. Zip success")
            ## myApicCollector.cleanUp()
            ipv4 = os.popen('ip addr show oobmgmt').read().split(
                "inet ")[1].split("/")[0]
            logger.info("App cost: %.2f mins" %
                        ((time.time() - start_time)/60))
            print("\n\nPLEASE DOWNLOAD FROM SCP OR HTTPS\n\nLocation: \n/data/techsupport/tinytail.tgz\n\nHTTPS: \n" +
                  "https://"+ipv4+"/files/1/techsupport/tinytail.tgz\n\nSCP: \n"+"scp://" + ipv4 + "/data/techsupport/tinytail.tgz\n\nAuthor: Bruce Liu yuxuliu@cisco.com\n")

        except KeyboardInterrupt:
            logger.info("Action safe canceled. :D ")
            myApicCollector.cleanUp()
    else:
        logger.debug("COLLECT DIDN'T TRIGGER")
