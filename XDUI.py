# -*- coding: utf-8 -*-
"""
Created on Wed Mar  8 10:35:54 2017

@author: Sanket Gupte

Xnat Download Upload UI 
"""

import os
import sys
from xnatdui import Ui_XnatDUI
from PyQt5 import QtCore, QtGui, QtWidgets
import yaml
import errno
#import requests
import getpass
import sip
from platform import system
from string import whitespace
import subprocess
from XRest import XnatRest
import operator
from collections import defaultdict
from SwarmSubmitter import SwarmJob
from time import sleep
import asyncio
import zipfile
import shutil
import concurrent.futures

#Headers for the Upload Tree
SESS_HEADERS=('1','2','3','4')
#Pre-set ComboBox translations for Path Creation screen
CMBPATH=['PROJ','SUBJ','SESS','SCAN','SCANID']

if system()=='Windows':
    CUST_PROG_CONV='<Custom Program> -LocOfDcmFiles %Output-Dir%\* -CustomFileExtension %File-Name% -CustomFileDOwnloadLocation %Output-Dir%\Custom'
else:
    CUST_PROG_CONV='<Custom Program> -LocOfDcmFiles %Output-Dir%/* -CustomFileExtension %File-Name% -CustomFileDOwnloadLocation %Output-Dir%/Custom'

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtWidgets.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig)
# Memoise function to speed up things
def memoise(f):
    cache ={}
    return lambda *args: cache[args] if args in cache else cache.update({args: f(*args)}) or cache[args]


class StartQT(QtWidgets.QMainWindow):
    def __init__(self,parent=None):
        #Setting up the GUI
        QtCore.pyqtRemoveInputHook()
        QtWidgets.QWidget.__init__(self,parent)
        self.main_ui = Ui_XnatDUI()
        self.main_ui.setupUi(self)
        
        #Connect signals to buttons
        self.main_ui.btn_page1.clicked.connect(self.page1_clicked)
        self.main_ui.btn_page2.clicked.connect(self.page2_clicked)
        self.main_ui.btn_page3.clicked.connect(self.page3_clicked)
        self.main_ui.btn_page4.clicked.connect(self.page4_clicked)
        self.main_ui.btn_page5.clicked.connect(self.page5_clicked)
        self.main_ui.btn_page6.clicked.connect(self.page6_clicked)
        self.main_ui.btn_sysconfig.clicked.connect(self.loadConfig)
        self.main_ui.btn_reset.clicked.connect(self.reset_all_clicked)
        self.main_ui.btn_SignIn.clicked.connect(self.sign_in)
        self.main_ui.edt_pwd.returnPressed.connect(self.sign_in)
        self.main_ui.edt_username.returnPressed.connect(self.sign_in)
        
        self.main_ui.rb_sel_download.toggled.connect(self.download_selected)
        self.main_ui.rb_sel_upload.toggled.connect(self.upload_selected)
        
        self.main_ui.cmb_project.currentIndexChanged.connect(self.index_proj_changed)
        
        
       #Class Variables
        self.sysConfig=None
        self.userConfig=None
        
        #Session variables
        self.XConn=None
        #self.url=None
        #self.auth=None
        #self.sess=None
                
        self.projects=None
        
        #Scan labels list
        self.scan_quality_labels=None
        #Scan Quality CheckBoxes
        #To add additional scan qualities, add a checkbox in the xnatui.py file in the appropriate groupbox. Then add the id of that checkbox in this list
        #This can be more Muggle-Friendly by pulling number of scan qualities from the config file and creating that many checkboxes.
        self.scan_quality_checkBoxes=[self.main_ui.chk_quality_1,self.main_ui.chk_quality_2,self.main_ui.chk_quality_3,
                                      self.main_ui.chk_quality_4,self.main_ui.chk_quality_5,self.main_ui.chk_quality_6]
        self.main_ui.chk_quality_1.clicked.connect(self.scan_quality_checked)
        self.main_ui.chk_quality_2.clicked.connect(self.scan_quality_checked)
        self.main_ui.chk_quality_3.clicked.connect(self.scan_quality_checked)
        self.main_ui.chk_quality_4.clicked.connect(self.scan_quality_checked)
        self.main_ui.chk_quality_5.clicked.connect(self.scan_quality_checked)
        self.main_ui.chk_quality_6.clicked.connect(self.scan_quality_checked)

        self.resource_labels=[]
        #This can be more Muggle-Friendly by pulling number of resources from the config file and creating that many checkboxes.
        self.resource_checkBoxes=[self.main_ui.chk_res_1,self.main_ui.chk_res_2,self.main_ui.chk_res_3,self.main_ui.chk_res_4,self.main_ui.chk_res_5]
        self.main_ui.chk_res_1.clicked.connect(self.res_type_checked)
        self.main_ui.chk_res_2.clicked.connect(self.res_type_checked)
        self.main_ui.chk_res_3.clicked.connect(self.res_type_checked)
        self.main_ui.chk_res_4.clicked.connect(self.res_type_checked)
        self.main_ui.chk_res_5.clicked.connect(self.res_type_checked)
        
        #Flags for checking if boxes are checked
        self.fl_Subj_checked =False
        self.fl_Sess_checked =False
        self.fl_Scan_checked =False
        
        #Radio button Selection flags
        self.fl_subjects_selection=None # 0=Sessions, 1=Resources
        self.fl_sessions_selection=None # 0=Scans, 1=Resources
        
        self.main_ui.lst_subjects.setEnabled(False)
        self.main_ui.tree_sessions.setEnabled(False)
        self.main_ui.tree_scans.setEnabled(False)
        #Connections to Subjects/Sessions/Scans List/Trees
        self.main_ui.lst_subjects.itemChanged.connect(self.click_sub)
        self.main_ui.tree_sessions.itemClicked.connect(self.handle_sess)
        self.main_ui.tree_scans.itemClicked.connect(self.handle_scan)
        
        #Radio Button Connections
        self.main_ui.rb_subj_res.toggled.connect(self.subj_res_rb_selected)
        self.main_ui.rb_subj_sess.toggled.connect(self.subj_sess_rb_selected)
        self.main_ui.rb_sess_scans.toggled.connect(self.sess_scan_rb_selected)
        self.main_ui.rb_sess_res.toggled.connect(self.sess_res_rb_selected)
        
        #Hide the root elements on the trees
        self.main_ui.tree_sessions.header().hide()
        self.main_ui.tree_scans.header().hide()
        
        
        #Button Connections for Path making buttons
        self.main_ui.btn_send_edt.clicked.connect(self.send2path_edt)
        self.main_ui.btn_send_cmb.clicked.connect(self.send2path_cmb)
        self.main_ui.btn_reset_path_selected.clicked.connect(self.reset_path_selected)
        self.main_ui.btn_reset_path_all.clicked.connect(self.reset_path_all)
        self.main_ui.chk_path_all_scans.setChecked(True)
        self.main_ui.chk_path_all_scans.clicked.connect(self.send2allScanChkBoxes)
        self.main_ui.cmb_path_txt.addItems(CMBPATH)
        
        
        #Flag to denote all download destination paths are unique
        self.fl_download_paths_uniq=False
        self.dict_duplicate_paths=defaultdict(list)
        
        #Download Options Radio Button Signals
        #QtCore.QObject.connect(self.main_ui.rb_afni, QtCore.SIGNAL("toggled(bool)"), self.afni_clicked)
        self.main_ui.rb_afni.toggled.connect(self.afni_clicked)
        #QtCore.QObject.connect(self.main_ui.rb_nifti, QtCore.SIGNAL("toggled(bool)"), self.nifti_clicked)
        self.main_ui.rb_nifti.toggled.connect(self.nifti_clicked)
        #QtCore.QObject.connect(self.main_ui.rb_custom, QtCore.SIGNAL("toggled(bool)"), self.custom_clicked)
        self.main_ui.rb_custom.toggled.connect(self.custom_clicked)
        #QtCore.QObject.connect(self.main_ui.rb_dcm, QtCore.SIGNAL("toggled(bool)"), self.dcm_clicked)
        self.main_ui.rb_dcm.toggled.connect(self.dcm_clicked)
        self.main_ui.btn_refresh_cmd.clicked.connect(self.download_cmd_refresh)
        self.main_ui.btn_download.clicked.connect(self.download_clicked)
        
        #Variables with data
        self.curr_proj=None #Currently selected Xnat Project
        
        # Lists and Dictionaries
        self.li_subs=[] #List of subjects as received
        self.dict_checked_all={} #Dictionary of selected subjects
        #dict_checked_all[SubjectId][SessionLabel][SessionShortLabel-Redundant][Unselected-scans=0][ScanId]=ScanName
        #dict_checked_all[SubjectId][SessionLabel][SessionShortLabel-Redundant][Selected-scans  =1][ScanId]=ScanName
        #dict_checked_all[SubjectId][SessionLabel][SessionShortLabel-Redundant][Session-Resources UnSelected =2][Resource-Dir-Label]=ResourceName
        #dict_checked_all[SubjectId][SessionLabel][SessionShortLabel-Redundant][Session-Resources Selected =3][Resource-Dir-Label]=ResourceName
        
        self.tree_all={} # A dict of dict of dict for everything

        #For Destination Tab
        self.main_ui.grp_allScans=[]
        self.selected_uniq_scans={}      

        #For Download Tab        
        self.d_format=1  #1=DCM, 2=AFNI , 3=NIFTI, 4=CUSTOM
        self.main_ui.rb_dcm.setChecked(True)
        self.download_begin=0  #Flag to start downloading        
        
        #Initialize stuff. The sequence is important.
        self.loadConfig()
        self.initDirs()
        self.loadUserConfig()
        #Load the colors from the config. #sysConfig variable is initialized in loadConfig
        self.colors=self.sysConfig['sys-init']['colors']
        
        
        #Disabling Buttons 
        self.main_ui.btn_page1.setEnabled(False)
        self.main_ui.btn_page2.setEnabled(False)
        self.main_ui.btn_page3.setEnabled(False)
        self.main_ui.btn_page4.setEnabled(False)
        self.main_ui.btn_page5.setEnabled(False)
        self.main_ui.btn_page6.setEnabled(False)
        
        #Flags to trigger tab refresh
        self.fl_refresh_page1=False
        self.fl_refresh_page2=False
        self.fl_refresh_page3=False
        self.fl_refresh_page4=False
        self.fl_refresh_page5=False
        self.fl_refresh_page6=False
        
        
        self.main_ui.grp_what.setEnabled(False)
        self.main_ui.grp_download_method.setEnabled(False)

        self.page1_clicked() #Go to the first page.
        #self.testTable()
    
    def download_clicked(self):
        """
        When the final 'Download' button is clicked
        """
        self.identify_duplicate_paths()
        if self.dict_duplicate_paths:
            self.PopupDlg("Please Remove Duplicate Paths !!\nCheck same colored rows")
        else:
            D_Flag=1024 #1024 = 0x00000400  , the message sent when OK is pressed
            if len(self.getCheckedResourceLabels())>1:
                D_Flag=self.DownloadWarningMultipleResources(self.getCheckedResourceLabels())
            if D_Flag==1024:
                if self.DownloadMsgBox(self.d_format)==1024:
                    #self.main_ui.tab_logger.setCurrentIndex(1)
                    self.PopupDlg("Hello Test")
                    self.disable_all()
                    #MySwarm=SwarmJob(self.XConn,20)
                    #Check if multiple resource types are checked.
                    resources=self.getCheckedResourceLabels()
                        
                    aList=[]
                    #items in aList - 0: Download Format
                    #               - 1: Download directory
                    #               - 2: DOwnload filename (with .zip appended at the end)
                    #               - 3: main URI
                    #               - 4: download structure
                    #               - 5: Counter
                        
                    for i in range(self.main_ui.lst_cmd.count()):
                        if len(resources)==1:
                            aList.append([self.d_format,self.main_ui.lst_dest_pick.item(i).text(),
                                       self.main_ui.lst_filename.item(i).text()+'.zip',
                                       self.main_ui.lst_dest_pick.item(i).toolTip()+"/resources/"+resources[0],
                                       self.main_ui.lst_cmd.item(i).text(),str(i+1)])
                        else:
                            #Create Resources directory and add resource to URI, for each resource
                            for res in resources:
                                aList.append([self.d_format,os.path.join(self.main_ui.lst_dest_pick.item(i).text(),res),
                                       self.main_ui.lst_filename.item(i).text()+'.zip',
                                       self.main_ui.lst_dest_pick.item(i).toolTip()+"/resources/"+res,
                                       self.main_ui.lst_cmd.item(i).text(),str(i+1)])

                    #Creates an asynchronous loop, and downloads the things (asynchronously)
#                    event_loop=asyncio.get_event_loop()
#                    try:
#                        event_loop.run_until_complete(self.download_async(aList))
#                    finally:
#                        event_loop.close()

                    #Create an asynchronous loop and run it in an executor, that creates a separate thread/process
                    if self.sysConfig['sys-init']['parallel']=='P':
                        executor = concurrent.futures.ProcessPoolExecutor(max_workers=self.sysConfig['sys-init']['max-parallel'],)
                    else:
                        executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.sysConfig['sys-init']['max-parallel'],)
                    event_loop=asyncio.get_event_loop()
                    try:
                        event_loop.run_until_complete(self.run_blocking_tasks(executor,aList))
                    finally:
                        event_loop.close()

#    async def download_async(self,jobList):
#        """
#        A helper function for download_clicked
#        """
#        #print("Going in the Download_Async helper")
#        dRequests=[self.downloadRequest(i) for i in jobList]
#        for nxt2finish in asyncio.as_completed(dRequests):
#            return_val=await nxt2finish
        
    async def run_blocking_tasks(self,executor,jobList): #Replacing download_async
        """
        
        """
        print("Going in run_blocking_tasks")
        ev_loop=asyncio.get_event_loop()
        blocking_tasks = [
                    #ev_loop.run_in_executor(executor,self.downloadRequest,i) #When using the function/s from the same class
                    ev_loop.run_in_executor(executor,downloadRequest,*[self.host,self.uname,self.passwd,i])
                    for i in jobList
                ]
        completed,pending = await asyncio.wait(blocking_tasks)
        results=[t.result() for t in completed]
        print('Results: {!r}'.format(results)) #return from the doenloadRequest function
        
        print('All Downloads Finished')
        
#There is a slight performance gain when the following two commented out functions are separeted from the QT Class, since they can now be run on a separete (sub)thread
#    def downloadRequest(self,jobDefs): #To run this with download_async make it async (i.e. async def downloadRequest(blah,blah))
#        """
#        Helper function for download_clicked. Download the files here
#        """
#        tmp=','.join(str(e) for e in jobDefs)
#        
#        #items in jobDefs - 0: Download Format
#        #                 - 1: Download directory
#        #                 - 2: DOwnload filename
#        #                 - 3: main resource URI 
#        #                 - 4: download structure
#        #                 - 5: Counter
#        if jobDefs[0]==1:
#            #Direct download no conversion
#            print ("Got 1 for >>>: %s"%tmp)
#            
#            #Make directories first
#            self.makeDirsIfNotExist(jobDefs[1])
#            # Getting resources as zip and exploding them seems like a faster way to retrieve files at this time. 
#            # Compared it to downloading each file one at a time, and it is considerably slower.
#            if self.XConn.getZip(jobDefs[3],jobDefs[1],jobDefs[2]):
#                self.cleanUpDownload(jobDefs[1],jobDefs[2])
#            
#        elif jobDefs[0]==2:
#            #Converting to AFNI after downloading
#            print ("Got 2 for >>>: %s"%tmp)
#            
#        elif jobDefs[0]==3:
#            #Converting to NIFTI after downloading
#            print ("Got 3 for >>>: %s"%tmp)
#        elif jobDefs[0]==3:
#            #Run custom script after downloading
#            print ("Got 3 for >>>: %s"%tmp)
#            
#        return "ReturnValue"
#
#    def cleanUpDownload(self,path,filename):
#        """
#        Extracts the zipfile and re-structures the directory structure as asked.
#        This function can be made better.
#        This is the dumbest thing, cannot extract each file to custom location, 
#        it has to be in the same internal directory structure as the zip file.
#        """
#        #TODO: COnsider the situation : DICOM & SNAPSHOTS is selected but scan 1 doesn't have SNAPSHOTS resource. -> getZip gives Oops Error code 404
#        if os.path.isfile(os.path.join(path,filename)):
#            #Need a try except block for the zipfile stuff
#            zipFileName=zipfile.ZipFile(os.path.join(path,filename))
#            zipFileName.extractall(path)
#            allFiles=zipFileName.namelist()
#    #        for zfile in zipFileName.namelist():
#    #            zipFileName.extract(zfile,path)
#            zipFileName.close()
#            
#            #Adding try block here doesn't seem necessary , as yet. 
#            os.remove(os.path.join(path,filename))
#            
#            #Flag to check if all files moved successfully
#            f_renamed=True
#            for aFile in allFiles:
#                fPath=aFile.split('/')
#                try:
#                    os.rename(os.path.join(path,os.path.join(*fPath)),os.path.join(path,filename+'-'+fPath[-1]))
#                except os.error as e:
#                    f_renamed=False
#                    raise #Do logging instead of raising
#                    
#            if f_renamed: #If all files successfully moved, then delete the directory
#                try:
#                    # A bit of a risky thing to do. But o well. :)
#                    shutil.rmtree(os.path.join(path,allFiles[0].split('/')[0]),ignore_errors=True)
#                except os.error as e:
#                    # Ignoring Errors, so this is kind of useless
#                    if e.errno !=errno.EEXIST:
#                        raise #Do logging instead of raising

    def identify_duplicate_paths(self):
        """
        Checking if there are any duplicate paths in the step when selecting download paths
        """
        path_list=[]
        for i in range(self.main_ui.lst_dest_pick.count()):
            path_list.append(self.main_ui.lst_dest_pick.item(i).text()+'/'+self.main_ui.lst_filename.item(i).text())
            self.main_ui.lst_dest_pick.item(i).setBackground(QtGui.QColor("transparent"))
            self.main_ui.lst_filename.item(i).setBackground(QtGui.QColor("transparent"))
        self.dict_duplicate_paths.clear()
        self.dict_duplicate_paths=defaultdict(list)
        for i,item in enumerate(path_list):
            self.dict_duplicate_paths[item].append(i)
        self.dict_duplicate_paths = {k:v for k,v in self.dict_duplicate_paths.items() if len(v)>1}
        #print(self.dict_duplicate_paths)
        i=0
        for key,val in self.dict_duplicate_paths.items():
            for itm in val:
                self.main_ui.lst_dest_pick.item(itm).setBackground(QtGui.QColor(self.colors[i]))
                self.main_ui.lst_filename.item(itm).setBackground(QtGui.QColor(self.colors[i]))
            if (i+1)==len(self.colors):
                i=0
            else:
                i+=1

                
    
    def send2path_edt(self):
        """
        When Send button is clicked for the 'Deestination' tab corresponding to TextBox
        """
        if self.main_ui.rb_send_path.isChecked():
                
            for scan_grp in self.main_ui.grp_allScans:
                #Getting the GroupBoxes for each selected scan types
                if scan_grp.isChecked():
                    grp_layout=scan_grp.layout()
                               
                #Getting hbox2 layout that has the textboxes
                    txt_layout=grp_layout.itemAt(1).layout()
                    #txt_layout.itemAt(0).widget().setText(txt_layout.itemAt(0).widget().text()+self.main_ui.edt_path_txt.text())
                    txt_layout.itemAt(0).widget().setText(os.path.join(txt_layout.itemAt(0).widget().text(),self.main_ui.edt_path_txt.text()))
                    
                    
        elif self.main_ui.rb_send_file.isChecked():
                            
            for scan_grp in self.main_ui.grp_allScans:
                #Getting the GroupBoxes for each selected scan types
                if scan_grp.isChecked():
                    grp_layout=scan_grp.layout()
                               
                #Getting hbox2 layout that has the textboxes
                    txt_layout=grp_layout.itemAt(1).layout()
                    txt_layout.itemAt(1).widget().setText(txt_layout.itemAt(1).widget().text()+self.main_ui.edt_path_txt.text())
                    #txt_layout.itemAt(1).widget().setText(os.path.join(txt_layout.itemAt(1).widget().text(),self.main_ui.edt_path_txt.text()))
        else:
            self.PopupDlg("Please Select WHERE to send this text !")

    def send2path_cmb(self):
        """
        When Send button is clicked for the 'Deestination' tab corresponding to Dropdown box
        """
        if self.main_ui.rb_send_path.isChecked():
                
            for scan_grp in self.main_ui.grp_allScans:
                #Getting the GroupBoxes for each selected scan types
                if scan_grp.isChecked():
                    grp_layout=scan_grp.layout()
               
                #Getting hbox2 layout that has the textboxes
                    txt_layout=grp_layout.itemAt(1).layout()
                    #txt_layout.itemAt(0).widget().setText(txt_layout.itemAt(0).widget().text()+"%"+str(self.main_ui.cmb_path_txt.currentText())+"%")
                    txt_layout.itemAt(0).widget().setText(os.path.join(txt_layout.itemAt(0).widget().text(),"%"+str(self.main_ui.cmb_path_txt.currentText())+"%"))
                    
        elif self.main_ui.rb_send_file.isChecked():
                            
            for scan_grp in self.main_ui.grp_allScans:
                #Getting the GroupBoxes for each selected scan types
                if scan_grp.isChecked():
                    grp_layout=scan_grp.layout()

                #Getting hbox2 layout that has the textboxes
                    txt_layout=grp_layout.itemAt(1).layout()
                    txt_layout.itemAt(1).widget().setText(txt_layout.itemAt(1).widget().text()+"%"+str(self.main_ui.cmb_path_txt.currentText())+"%")
                    #txt_layout.itemAt(1).widget().setText(os.path.join(txt_layout.itemAt(1).widget().text(),"%"+str(self.main_ui.cmb_path_txt.currentText())+"%"))
        else:
            self.PopupDlg("Please Select WHERE to send this text !")
    

    def send2allScanChkBoxes(self):
        if self.main_ui.chk_path_all_scans.isChecked():
                
            for scan_grp in self.main_ui.grp_allScans:
                #Getting the GroupBoxes for each selected scan types
                scan_grp.setChecked(True)
        else:
            for scan_grp in self.main_ui.grp_allScans:
                #Getting the GroupBoxes for each selected scan types
                scan_grp.setChecked(False)


    def reset_path_selected(self):
        """
        Resets the text boxes that is selected  in the 'Destination' tab
        # GETS EVERYTHING FROM THE DYNAMIC GroupBoxes 
        """
        for scan_grp in self.main_ui.grp_allScans:
            #Getting the GroupBoxes for each selected scan types
            if scan_grp.isChecked():
                grp_layout=scan_grp.layout()
                        
            #Getting hbox2 layout that has the textboxes
                txt_layout=grp_layout.itemAt(1).layout()
                txt_layout.itemAt(0).widget().setText("")
                txt_layout.itemAt(1).widget().setText("")
    
    def reset_path_all(self):
        """
        Resets everything in the 'Destination' tab
        """
        # GETS EVERYTHING FROM THE DYNAMIC GroupBoxes 
        for scan_grp in self.main_ui.grp_allScans:
            #Getting the GroupBoxes for each selected scan types
            #print scan_grp.isChecked()
            grp_layout=scan_grp.layout()
                    
            #Getting hbox2 layout that has the textboxes
            txt_layout=grp_layout.itemAt(1).layout()
            txt_layout.itemAt(0).widget().setText("")
            txt_layout.itemAt(1).widget().setText("")
    
    def handle_scan(self,item,column):
        """
        When a single scan is checked in the Scan Tree - 'Source' tab
        """
        #===========TODO==========
        #Handle the event : when all scans unchecked - disable the 'Download Tab' (btn_page2)
        self.fl_refresh_page2=True
        self.fl_refresh_page3=True
        self.fl_refresh_page4=True
        self.fl_refresh_page5=True
        self.fl_refresh_page6=True
        
        
        self.fl_Subj_checked=True
        self.fl_Sess_checked=True
        self.fl_Scan_checked=True
        self.main_ui.btn_page2.setEnabled(True)
        self.main_ui.tree_sessions.setEnabled(False)
        self.main_ui.lst_subjects.setEnabled(False)
        self.main_ui.grp_sess_select.setEnabled(False)
        self.main_ui.grp_subj_select.setEnabled(False)
        if self.main_ui.rb_subj_sess.isChecked() and self.main_ui.rb_sess_scans.isChecked():
            """
            If Subject + Session + Scan
            """
            if item.checkState(column) == QtCore.Qt.Checked:  #Checked
                for child in range(item.childCount()):
                    sess_det=self.lookup_session(item.child(child).text(0))
                    del_keys=[]
                    for k,v in self.dict_checked_all[str(sess_det[0])][str(item.child(child).text(0))][1][0].items():
                        if item.text(0)==v:
                            del_keys.append(k)
                            #break  #There are scans with same name in some cases.
                    #Pop from dict[0] and put it in dict[1] . 0=Unchecked , 1=Checked
                    #self.dict_checked_all[str(sess_det[0])][str(item.child(child).text(0))][1][1]={x:self.dict_checked_all[str(sess_det[0])][str(item.child(child).text(0))][1][0].pop(x, None) for x in del_keys}
                    self.dict_checked_all[str(sess_det[0])][str(item.child(child).text(0))][1][1].update({x:self.dict_checked_all[str(sess_det[0])][str(item.child(child).text(0))][1][0].pop(x, None) for x in del_keys})
            elif item.checkState(column) == QtCore.Qt.Unchecked:  #Unchecked
                for child in range(item.childCount()):
                    sess_det=self.lookup_session(item.child(child).text(0))
                    del_keys=[]
                    for k,v in self.dict_checked_all[str(sess_det[0])][str(item.child(child).text(0))][1][1].items():
                        if item.text(0)==v:
                            del_keys.append(k)
                            #break  #There are scans with same name in some cases.
                    #Pop from dict[0] and put it in dict[1] . 0=Unchecked , 1=Checked
                    self.dict_checked_all[str(sess_det[0])][str(item.child(child).text(0))][1][0].update({x:self.dict_checked_all[str(sess_det[0])][str(item.child(child).text(0))][1][1].pop(x, None) for x in del_keys})
    
            else: #Will not execute
                pass #QtCore.Qt.PartiallyChekced
                
            #print (self.dict_checked_all)
            
        elif self.main_ui.rb_subj_sess.isChecked() and self.main_ui.rb_sess_res.isChecked():
            """
            Subject + Session -> Resources. No Scans
            """
            if item.checkState(column) == QtCore.Qt.Checked:  #Checked
                #print (item.text(0)+ " Checked")
                self.main_ui.lbl_status.setStyleSheet(_fromUtf8("background-color:#f79f99;")) #4d9900 - Green
                self.main_ui.lbl_status.setText(' Getting data....WAIT')
                if item.childCount()==0:
                    #sess_det =self.lookup_session(item.text(0)) #Get's subjID & scan details
                    self.main_ui.pb_inter.setValue(10)
                    #self.handle_sess_Chk(sess_det[0],item.text(0))
                    self.main_ui.pb_inter.setValue(100)
                else:
                    child_cnt=item.childCount()
                    incr=int(100/child_cnt)
                    tot=0
                    for child in range(child_cnt):
                        tot=tot+incr
                        self.main_ui.pb_inter.setValue(tot)
                        #sess_det= self.lookup_session(item.child(child).text(0))  #Get's subjID & scan details
                        #self.handle_sess_Chk(sess_det[0],item.child(child).text(0))
            elif item.checkState(column) == QtCore.Qt.Unchecked:  #Unchecked
                #print (item.text(0)+" Unchecked")
                if item.childCount()==0:
                    #sess_det =self.lookup_session(item.text(0)) #Get's subjID & scan details
                    self.main_ui.pb_inter.setValue(10)
                    #self.handle_sess_UnChk(sess_det[0],item.text(0))
                    self.main_ui.pb_inter.setValue(100)
                else:
                    child_cnt=item.childCount()
                    incr=int(100/child_cnt)
                    tot=0
                    for child in range(child_cnt):
                        tot=tot+incr
                        self.main_ui.pb_inter.setValue(tot)
                        #sess_det= self.lookup_session(item.child(child).text(0))  #Get's subjID & scan details
                        #self.handle_sess_UnChk(sess_det[0],item.child(child).text(0))
        elif self.main_ui.rb_subj_res.isChecked():
            """
            Subject -> Resources. No Session. No Scan.
            """
            print("This should NEVER run")
        else :
            print("This should NEVER run either")
            
        self.main_ui.pb_inter.setValue(100)
        self.main_ui.lbl_status.setStyleSheet(_fromUtf8("background-color:#4d9900;")) # f79f99 - Red
        self.main_ui.lbl_status.setText('    Ready')

    
    def handle_sess(self, item, column):
        """
        When a single session is checked in the sessions tree - 'Source' Tab
        """
        self.fl_refresh_page2=True
        self.fl_refresh_page3=True
        self.fl_refresh_page4=True
        self.fl_refresh_page5=True
        self.fl_refresh_page6=True
        
        self.fl_Subj_checked=True
        self.fl_Sess_checked=True
        self.main_ui.lst_subjects.setEnabled(False)
        self.main_ui.tree_sessions.blockSignals(True)
        self.main_ui.pb_inter.setValue(0)
        if item.checkState(column) == QtCore.Qt.Checked:  #Checked
            #print (item.text(0)+ " Checked")
            self.main_ui.lbl_status.setStyleSheet(_fromUtf8("background-color:#f79f99;")) #4d9900 - Green
            self.main_ui.lbl_status.setText(' Getting data....WAIT')
            if item.childCount()==0:
                sess_det =self.lookup_session(item.text(0)) #Get's subjID & scan details
                self.main_ui.pb_inter.setValue(10)
                self.handle_sess_Chk(sess_det[0],item.text(0))
                self.main_ui.pb_inter.setValue(100)
            else:
                child_cnt=item.childCount()
                incr=int(100/child_cnt)
                tot=0
                for child in range(child_cnt):
                    tot=tot+incr
                    self.main_ui.pb_inter.setValue(tot)
                    sess_det= self.lookup_session(item.child(child).text(0))  #Get's subjID & scan details
                    self.handle_sess_Chk(sess_det[0],item.child(child).text(0))
        elif item.checkState(column) == QtCore.Qt.Unchecked:  #Unchecked
            #print (item.text(0)+" Unchecked")
            if item.childCount()==0:
                sess_det =self.lookup_session(item.text(0)) #Get's subjID & scan details
                self.main_ui.pb_inter.setValue(10)
                self.handle_sess_UnChk(sess_det[0],item.text(0))
                self.main_ui.pb_inter.setValue(100)
            else:
                child_cnt=item.childCount()
                incr=int(100/child_cnt)
                tot=0
                for child in range(child_cnt):
                    tot=tot+incr
                    self.main_ui.pb_inter.setValue(tot)
                    sess_det= self.lookup_session(item.child(child).text(0))  #Get's subjID & scan details
                    self.handle_sess_UnChk(sess_det[0],item.child(child).text(0))
        self.main_ui.pb_inter.setValue(100)
        self.main_ui.lbl_status.setStyleSheet(_fromUtf8("background-color:#4d9900;")) # f79f99 - Red
        self.main_ui.lbl_status.setText('    Ready')
        self.main_ui.tree_sessions.blockSignals(False)


    def handle_sess_Chk(self,subj,sess):
        """
        When a session is marked Checked - 'Source' tab
        """
        try:
            self.dict_checked_all[str(subj)][str(sess)][1][0].clear() #Clearing UnSelected
        except NameError:
            pass
        try:
            self.dict_checked_all[str(subj)][str(sess)][1][1].clear() #Clearing Selected
        except NameError:
            pass

        if self.main_ui.rb_sess_res.isChecked(): #If we want resources and not scans
#            self.main_ui.lbl_status.setStyleSheet(_fromUtf8("background-color:#f79f99;")) #4d9900 - Green
#            self.main_ui.lbl_status.setText('  Getting Resources')
            if 'res' not in self.tree_all[str(subj)][str(sess)]:
                tmp_res_list=self.XConn.getResourcesList(self.curr_proj,subj,sess)
                self.tree_all[str(subj)][str(sess)]['res']={}
                for sess_res in tmp_res_list:
                    self.tree_all[str(subj)][str(sess)]['res'][sess_res['label']]={k:v for k,v in sess_res.items() if k in ['xnat_abstractresource_id']} #Getting only select things from the session resources dict
            for r_lbl,r_det in self.tree_all[str(subj)][str(sess)]['res'].items():
                self.dict_checked_all[str(subj)][str(sess)][2][0][r_lbl]= [] #List of Resources under r_lbl  #r_det['xnat_abstractresource_id']
                self.add_to_scan_tree_res(subj, sess,r_lbl)  #Adding a dict of resource files to this []
        else: #If we want scans
#            self.main_ui.lbl_status.setStyleSheet(_fromUtf8("background-color:#f79f99;")) #4d9900 - Green
#            self.main_ui.lbl_status.setText('  Getting Scans')
            if 'scans' not in self.tree_all[str(subj)][str(sess)]:
                tmp_sess_list=self.XConn.getScans(self.curr_proj,subj,sess)
                #tmp_sess_list=XnatUtils.list_scans(self.xnat_intf,str(self.curr_proj),str(subj),str(sess))
                self.tree_all[str(subj)][str(sess)]['scans']={}
                for scan in tmp_sess_list:
                    #sc_res=self.XConn.getResourcesList(self.curr_proj,subj,sess,scan['ID'])
                    sc_res=self.XConn.getScanResources(self.curr_proj,subj,sess,scan['ID'])
                    self.tree_all[str(subj)][str(sess)]['scans'][scan['ID']]={k:v for k,v in scan.items() if k in ['quality','type']} #Getting only select things from the scan dict
                    self.tree_all[str(subj)][str(sess)]['scans'][scan['ID']]['res']=[res['label'] for res in sc_res ] #List of resources for this scan for e.g. DICOM, NIFTI, etc.
                    
                    for res in sc_res: #Adding the Resource checkbox if it doesn't exist already
                        #print (res['label'])
                        if res['label'] not in self.resource_labels:
                            self.addResourceCheckBox(res['label'] )
            for s_id,s_det in self.tree_all[str(subj)][str(sess)]['scans'].items():
                #print("SCAN")
                #print (s_det)
                if s_det['quality'] in self.getCheckedScanQualityLabels() : #and s_det['res'] in self.getCheckedResourceLabels: #Add to tree only if needed
                    #This quality is checked. Check Resources now.
                    for res in s_det['res']:
                        #This Resource Type is checked
                        if res in self.getCheckedResourceLabels():
                            self.add_to_scan_tree(subj, sess,s_id,s_det['type'])
                            # Adding to dict_checked_all
                            self.dict_checked_all[str(subj)][str(sess)][1][0][s_id]=s_det['type']
                            break
                    

        

    def handle_sess_UnChk(self,subj,sess):
        """
        When a session is marked UnChecked
        """
        if self.main_ui.rb_sess_res.isChecked(): #If we want Resources not scans
            pass
        else:        #If we want scans
            for k_scan,v_scan in self.dict_checked_all[str(subj)][str(sess)][1][0].items():
                self.remove_frm_scan_tree(str(subj),str(sess),k_scan,v_scan)
            for k_scan,v_scan in self.dict_checked_all[str(subj)][str(sess)][1][1].items():
                self.remove_frm_scan_tree(str(subj),str(sess),k_scan,v_scan)
            self.dict_checked_all[str(subj)][str(sess)][1][0].clear() #Clearing UnSelected
            self.dict_checked_all[str(subj)][str(sess)][1][1].clear() #Clearing Selected

    def add_to_scan_tree_res(self,subj,sess,res_lbl):
        """
        When Session 'resources' are required. Adding the session Resources to the scan-tree
        """
        self.main_ui.tree_scans.setEnabled(True)
        tmp_res=self.XConn.getResourceFiles(self.curr_proj,subj,sess,None,res_lbl)
        root=self.main_ui.tree_scans.invisibleRootItem()
        flag=0
        for index in range(root.childCount()):
            if root.child(index).text(0)==res_lbl:
                for res in tmp_res:
                    new_kid=QtWidgets.QTreeWidgetItem(root.child(index))
                    new_kid.setFlags(new_kid.flags() | QtCore.Qt.ItemIsUserCheckable)
                    new_kid.setCheckState(0,QtCore.Qt.Unchecked)
                    new_kid.setText(0,res['Name'])
                    new_kid.setToolTip(0,sess)
                flag=1
                break
        if flag==0:
            parent = QtWidgets.QTreeWidgetItem(self.main_ui.tree_scans)
            parent.setText(0,res_lbl)
            parent.setFlags(parent.flags() | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)
            parent.setCheckState(0,QtCore.Qt.Unchecked)
            for res in tmp_res:
                child = QtWidgets.QTreeWidgetItem(parent)
                child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
                child.setCheckState(0,QtCore.Qt.Unchecked)
                child.setText(0,res['Name'])
                child.setToolTip(0,sess)
                

    def add_to_scan_tree(self,subj,sess,scan_id,scan_type):  # args are Non-Xnat terms/(labels not IDs)
        """
        Add entries from the scan tree - Resources are picked
        """
        root=self.main_ui.tree_scans.invisibleRootItem()
        flag=0
        for index in range(root.childCount()):
            if root.child(index).text(0)==scan_type:
                new_kid=QtWidgets.QTreeWidgetItem(root.child(index))
                new_kid.setText(0,sess)
                new_kid.setStatusTip(0,scan_id)
                flag=1
                break
        if flag==0:
            parent = QtWidgets.QTreeWidgetItem(self.main_ui.tree_scans)
            parent.setText(0,scan_type)
            parent.setFlags(parent.flags() | QtCore.Qt.ItemIsUserCheckable)
            parent.setCheckState(0,QtCore.Qt.Unchecked)
            child = QtWidgets.QTreeWidgetItem(parent)
            child.setText(0,sess)
            child.setStatusTip(0,scan_id)
    def remove_frm_scan_tree_res(self,subj,sess,res_lbl):
        """
        Remove entries from the scan tree - Resources are picked
        """
        pass
    def remove_frm_scan_tree(self,subj,sess,scan_id,scan_type):  # args are Non-Xnat terms/(labels not IDs)
        root=self.main_ui.tree_scans.invisibleRootItem()
        for index in range(root.childCount()):
            if root.child(index).text(0)==scan_type:
                for ind2 in range(root.child(index).childCount()):
                    if root.child(index).child(ind2).text(0)==sess and root.child(index).child(ind2).statusTip(0)==scan_id:
                        root.child(index).removeChild(root.child(index).child(ind2))
                        if root.child(index).childCount()==0:
                            root.removeChild(root.child(index))
                        break
                break

    def sess_scan_rb_selected(self):
        self.main_ui.grp_sess_select.setStyleSheet(_fromUtf8("background-color:;"))
        if self.main_ui.rb_sess_scans.isChecked():
            self.main_ui.grp_scan_quality.setVisible(True)
            self.main_ui.lbl_scan.setVisible(True)
            if self.fl_sessions_selection==None: #Fresh start
                self.fl_sessions_selection=0
                self.main_ui.lst_subjects.setEnabled(True)
                self.main_ui.tree_scans.setEnabled(True)
            elif self.fl_sessions_selection==1: #Switching from 1 to 0
                self.fl_sessions_selection=0       
    
    def sess_res_rb_selected(self):
        self.main_ui.grp_sess_select.setStyleSheet(_fromUtf8("background-color:;"))
        if self.main_ui.rb_sess_res.isChecked():
            self.main_ui.grp_scan_quality.setVisible(False)
            self.main_ui.lbl_scan.setVisible(False)
            if self.fl_sessions_selection==None: #Fresh start
                self.fl_sessions_selection=1
                self.main_ui.lst_subjects.setEnabled(True)
            elif self.fl_sessions_selection==0: #Switching from 0 to 1
                self.fl_sessions_selection=1       

    def subj_sess_rb_selected(self):
        self.main_ui.grp_subj_select.setStyleSheet(_fromUtf8("background-color:;"))
        if not self.main_ui.lst_subjects.isEnabled() and (self.main_ui.rb_sess_scans.isChecked() or self.main_ui.rb_sess_res.isChecked()):
            self.main_ui.lst_subjects.setEnabled(True)
        else:
            self.main_ui.grp_sess_select.setStyleSheet(_fromUtf8("background-color:#e0ffba;"))
        if self.main_ui.rb_subj_sess.isChecked():
            #print("Sessions Selected")
            self.main_ui.grp_scan_quality.setVisible(True)
            self.main_ui.lbl_scan.setVisible(True)
            self.main_ui.vf_sessions.setVisible(True)
            if self.fl_subjects_selection==None: #Fresh start
                self.fl_subjects_selection=0
            elif self.fl_subjects_selection==1: #Switching from 1 to 0
                self.fl_subjects_selection=0

    def subj_res_rb_selected(self):
        self.main_ui.grp_subj_select.setStyleSheet(_fromUtf8("background-color:;"))
        if not self.main_ui.lst_subjects.isEnabled() :#and (self.main_ui.rb_sess_scans.isChecked() or self.main_ui.rb_sess_res.isChecked()):
            self.main_ui.lst_subjects.setEnabled(True)
        #Clear the Resource checkboxes
#        else:
#            self.main_ui.grp_sess_select.setStyleSheet(_fromUtf8("background-color:#e0ffba;"))
        if self.main_ui.rb_subj_res.isChecked():
            #self.main_ui.tree_scans.clear()
            self.main_ui.grp_scan_quality.setVisible(False)
            self.main_ui.lbl_scan.setVisible(False)
            self.main_ui.vf_sessions.setVisible(False)
            if self.fl_subjects_selection==None: #Fresh start
                self.fl_subjects_selection=1                
            elif self.fl_subjects_selection==0: #Switching from 0 to 1
                self.fl_subjects_selection=1


    def click_sub(self,item_sub):
        """
        When a Subject is clicked
        """
        self.fl_refresh_page2=True
        self.fl_refresh_page3=True
        self.fl_refresh_page4=True
        self.fl_refresh_page5=True
        self.fl_refresh_page6=True

        if self.fl_subjects_selection==1: #If "Resources" is selected
            #For Resources
            self.main_ui.lbl_status.setStyleSheet(_fromUtf8("background-color:#f79f99;")) #4d9900 - Green
            self.main_ui.lbl_status.setText('  Getting Resources')

            if item_sub.checkState(): #Item is Checked - checkState is True
                pass
            else:
                pass
        elif self.fl_subjects_selection==0: #If "Sessions" is selected
            #For Sessions
            if not self.main_ui.tree_sessions.isEnabled():
                if not self.main_ui.rb_sess_scans.isChecked() and not self.main_ui.rb_sess_res.isChecked():
                    self.PopupDlg("Please Select if you want to download Scans or Resources")
                else:
                    self.main_ui.tree_sessions.setEnabled(True)
            self.main_ui.lbl_status.setStyleSheet(_fromUtf8("background-color:#f79f99;")) #4d9900 - Green
            self.main_ui.lbl_status.setText('  Getting Sessions')
            if item_sub.checkState(): #Item is Checked - checkState is True
                self.main_ui.pb_inter.setValue(0)
                self.fl_refresh_page5=True
                self.fl_Subj_checked=True
                if str(item_sub.text()) not in self.tree_all:
                    self.main_ui.pb_inter.setValue(10)
                    tmp_exp_list=self.XConn.getExperiments(self.curr_proj,item_sub.text())
                    #tmp_exp_list=XnatUtils.list_experiments(self.xnat_intf,str(self.curr_proj),str(item_sub.text()))
                    self.tree_all[str(item_sub.text())]={}
                    if len(tmp_exp_list)!=0:  #To prevent divide by zero error
                        inter=int(100/len(tmp_exp_list))
                        tot=0
                        for exp in tmp_exp_list:
                            tot=tot+inter
                            self.main_ui.pb_inter.setValue(tot)
                            if exp['xsiType']=='xnat:mrSessionData': #Getting experiments only of the type mrSessionData
                                self.tree_all[str(item_sub.text())][exp['label']]={}
                                self.tree_all[str(item_sub.text())][exp['label']]['exp']=exp['ID'] #Keeping only the ID  . No use for other fields for now.
                                self.tree_all[str(item_sub.text())][exp['label']]['strip']=self.strip_sub_id(str(item_sub.text()),exp['label'])
                self.main_ui.pb_inter.setValue(95)
                self.dict_checked_all[str(item_sub.text())]={}
                for sess in self.tree_all[str(item_sub.text())]:                
                    #self.dict_checked_all[str(item_sub.text())][sess]=[self.strip_sub_id(str(item_sub.text()),sess),{}] #Using the Processor
                    self.dict_checked_all[str(item_sub.text())][sess]=[self.tree_all[str(item_sub.text())][sess]['strip'],{0: {}, 1: {}},{0: {}, 1: {}}] # 0= Not selected, 1=Selected scans & resources || So, [1] is scans,[2] is resources
    
                root=self.main_ui.tree_sessions.invisibleRootItem()
    
                for sess in self.dict_checked_all[str(item_sub.text())]:
                    flag=0
                    for index in range(root.childCount()):
                        if root.child(index).text(0)==self.dict_checked_all[str(item_sub.text())][sess][0]:
                            new_kid=QtWidgets.QTreeWidgetItem(root.child(index))
                            new_kid.setFlags(new_kid.flags() | QtCore.Qt.ItemIsUserCheckable)
                            new_kid.setText(0,sess)
                            new_kid.setCheckState(0,QtCore.Qt.Unchecked)
                            flag=1
                            break
                    if flag==0:
                        parent = QtWidgets.QTreeWidgetItem(self.main_ui.tree_sessions)
                        parent.setText(0,self.dict_checked_all[str(item_sub.text())][sess][0])
                        parent.setFlags(parent.flags()| QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)
                        #parent.setCheckState(0,QtCore.Qt.Unchecked)
                        child = QtWidgets.QTreeWidgetItem(parent)
                        child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
                        child.setText(0,sess)
                        child.setCheckState(0,QtCore.Qt.Unchecked)        
                self.main_ui.pb_inter.setValue(100)
                                
            else:
            
                sub=self.dict_checked_all.pop(str(item_sub.text()),None)
                
                #print sub
                root=self.main_ui.tree_sessions.invisibleRootItem()
                for sess in sub:
                    #print sub[sess][0]
                    for index in range(root.childCount()):
                        if root.child(index).text(0)==sub[sess][0]:
                            for ind2 in range(root.child(index).childCount()):
                                if root.child(index).child(ind2).text(0)==sess:
                                    root.child(index).removeChild(root.child(index).child(ind2))
                                    if root.child(index).childCount()==0:
                                        root.removeChild(root.child(index))
                                    break
                            break
            self.main_ui.lbl_status.setStyleSheet(_fromUtf8("background-color:#4d9900;")) # f79f99 - Red
            self.main_ui.lbl_status.setText('  Ready')

        else: #If none of "Resources" or "Sessions" is selected
            """
            This will never run. NEVER. I think.
            """
            self.PopupDlg("Select Sessions or Resources")

    @memoise
    def lookup_session(self,sess):
        
        for k_sub, v_sess in self.dict_checked_all.items():
            for k_sess, v_scans in v_sess.items():
                if k_sess==sess:
                    return(k_sub,v_scans[1])
        return None
    
    @memoise
    def lookup_scan_quality(self,subj,sess,scan_id):
        #print(self.tree_all[subj][sess]['scans'])
        for s_id,s_det in self.tree_all[subj][sess]['scans'].items():
            if s_id==scan_id:
                return s_det['quality']
        return None
            
    def refresh_page1(self):
        #self.reset_process()
        #self.reset_export()
        #self.reset_upload()
        #self.reset_download()
        #self.reset_destination()
        self.fl_refresh_page2=True
        self.fl_refresh_page3=True
        self.fl_refresh_page4=True
        self.fl_refresh_page5=True
        self.fl_refresh_page6=True
        
        self.populate_subjects()
            
            
    def refresh_page2(self):
        #self.reset_process()
        #self.reset_upload()
        #self.reset_download()
        self.fl_refresh_page3=True
        self.fl_refresh_page6=True

        #-- Fresh
        vs_lay=QtWidgets.QVBoxLayout()

        vs_widg=QtWidgets.QWidget()
        vs_widg.setLayout(vs_lay)
        vs_scroll=QtWidgets.QScrollArea()
        vs_scroll.setWidgetResizable(True)
        vs_scroll.setWidget(vs_widg)
        
        self.reset_destination()
        
#        if system()=='Windows':
#            self.PopupDlg("Sorry, downloading isn't available on Windows !")
#            return
        
        for subj in self.dict_checked_all:
            for sess in self.dict_checked_all[subj]:
                for scan in self.dict_checked_all[subj][sess][1][1]: #Only Checked Scans
                    scan_name=self.dict_checked_all[subj][sess][1][1][scan]
                    if scan_name not in self.selected_uniq_scans:
                        self.selected_uniq_scans[scan_name]=''  #Save the text-box contents here
                        groupbox = QtWidgets.QGroupBox('%s' % scan_name)
                        groupbox.setCheckable(True)
                        grouplayout = QtWidgets.QVBoxLayout()
                        if system()=='Windows':
                            txtpath=QtWidgets.QLineEdit(self.sysConfig['down-init']['pathprefix-win'])
                        else:
                            txtpath=QtWidgets.QLineEdit(self.sysConfig['down-init']['pathprefix-linux'])
                        txtpath.setFixedWidth(500)
                        txtpath.setFixedHeight(20)
                        txtfname=QtWidgets.QLineEdit(self.sysConfig['down-init']['fileprefix'])
                        txtfname.setFixedWidth(150)
                        txtfname.setFixedHeight(20)
                      
                        hbox1=QtWidgets.QHBoxLayout()
                        hbox2=QtWidgets.QHBoxLayout()
                        
                        hbox2.addWidget(txtpath)
                        hbox2.addWidget(txtfname)
                        
                        grouplayout.addLayout(hbox1)
                        grouplayout.addLayout(hbox2)
                        groupbox.setLayout(grouplayout)
                        vs_lay.addWidget(groupbox)
                        self.main_ui.grp_allScans.append(groupbox)
                
        layout=QtWidgets.QHBoxLayout()
        layout.addWidget(vs_scroll)
        self.main_ui.grp_path.setLayout(layout)
        self.main_ui.btn_page3.setEnabled(True)
            
    def refresh_page3(self):
        #self.reset_process()
        #self.reset_upload()
        self.fl_refresh_page6=True
        #print("Refreshing Page3 Yay")
        #   GETS EVERYTHING FROM THE DYNAMIC GroupBoxes 

        self.reset_download()
#        if system()=='Windows':
#            self.PopupDlg("Download currently doesn't work on Windows ! Sorry")
#            return
        for scan_grp in self.main_ui.grp_allScans:
            
            #Getting the GroupBoxes for each selected scan types
            grp_layout=scan_grp.layout()

            self.selected_uniq_scans[str(scan_grp.title())]=[str(grp_layout.itemAt(1).layout().itemAt(0).widget().text()),str(grp_layout.itemAt(1).layout().itemAt(1).widget().text())]
        
        for subj in self.dict_checked_all:
            for sess in self.dict_checked_all[subj]:
                for scan in self.dict_checked_all[subj][sess][1][1]: #Only Checked Scans
                    scan_name=self.dict_checked_all[subj][sess][1][1][scan]
                    src_path="Proj:"+str(self.curr_proj)+"| Subj:"+str(subj)+"| Exp:"+str(sess)+"| Scan:"+str(scan_name)
                    #print src_path
                    int_path='/data/archive/projects/'+str(self.curr_proj)+'/subjects/'+str(subj)+'/experiments/'+str(sess)+'/scans/'+str(scan)
                    #print int_path
                    
                    dest_path=""
                    for dst_spl in [x for x in str(self.selected_uniq_scans[str(scan_name)][0]).split("%") if x]: #"%protocol%","%subject%","%session%","%scan%"
                        if dst_spl in ['proj','project','PROJ','PROJECT']:
                            dest_path+=str(self.curr_proj)
                        elif dst_spl in ["subject","subj","SUBJECT","SUBJ"]:
                            dest_path+=str(subj)
                        elif dst_spl in ["session","sess","SESSION","SESS"]:
                            dest_path+=str(sess)
                        elif dst_spl in ["scan","SCAN"]:
                            dest_path+=str(scan_name)
                        elif dst_spl in ["scanid","SCANID"]:
                            dest_path+=str(scan)
                        else:
                            dest_path+=str(dst_spl)
                    
                    dst_c_fn=""
                    for dst_fn in [x for x in str(self.selected_uniq_scans[str(scan_name)][1]).split("%") if x]:
                        if dst_fn in ['proj','project','PROJ','PROJECT']:
                            dst_c_fn+=str(self.curr_proj)
                        elif dst_fn in ["subject","subj","SUBJECT","SUBJ"]:
                            dst_c_fn+=str(subj)
                        elif dst_fn in ["session","sess","SESSION","SESS"]:
                            dst_c_fn+=str(sess)
                        elif dst_fn in ["scan","SCAN"]:
                            dst_c_fn+=str(scan_name)
                        elif dst_fn in ["scanid","SCANID"]:
                            dst_c_fn+=str(scan)
                        else:
                            dst_c_fn+=dst_fn

                    
                    #Removing Whitespaces
                    dest_path=dest_path.translate(whitespace)
                    dst_c_fn=dst_c_fn.translate(whitespace)
                    dst_c_fn=dst_c_fn.replace('/','-')
                    dst_c_fn=dst_c_fn.replace('#','')
                    
                    #Add to lists 
                    itm_src=QtWidgets.QListWidgetItem(src_path)
                    itm_dest=QtWidgets.QListWidgetItem(dest_path)
                    itm_fname=QtWidgets.QListWidgetItem(dst_c_fn)
                    
                    itm_src.setFlags(itm_src.flags() | QtCore.Qt.ItemIsEditable)                    
                    itm_dest.setFlags(itm_dest.flags() | QtCore.Qt.ItemIsEditable)
                    itm_fname.setFlags(itm_fname.flags() | QtCore.Qt.ItemIsEditable)
                    
                    #itm_dest.setData(1,QtCore.QVariant(int_path))
                    itm_dest.setToolTip(int_path)
                    
                    self.main_ui.lst_sel_log.addItem(itm_src)
                    self.main_ui.lst_dest_pick.addItem(itm_dest)
                    self.main_ui.lst_filename.addItem(itm_fname)
                    self.main_ui.grp_down_format.setStyleSheet(_fromUtf8("background-color:#e0ffba;"))
        self.download_cmd_refresh()
                    
    def download_cmd_refresh(self):
        """
        Refreshing the command text boxes for each scans
        """
        #Make FUll Command in the ListWidget
        self.main_ui.lst_cmd.clear()
        for subj in self.dict_checked_all:
            for sess in self.dict_checked_all[subj]:
                for scan in self.dict_checked_all[subj][sess][1][1]: #Only Checked Scans
                    itm_cmd=QtWidgets.QListWidgetItem(self.main_ui.edt_down_cmd.text())
                    itm_cmd.setFlags(itm_cmd.flags() | QtCore.Qt.ItemIsEditable)
                    self.main_ui.lst_cmd.addItem(itm_cmd)
        self.identify_duplicate_paths()

    def afni_clicked(self):
        """
        When Radio Button for AFNI is clicked
        """
        #Afni doesn't run on Windows
        self.main_ui.grp_down_format.setStyleSheet(_fromUtf8("background-color:;"))
        self.d_format=2
        if self.prog_exists('Dimon'):
            self.main_ui.edt_down_cmd.setText('Dimon -infile_pattern %Output-Dir%/* -dicom_org -gert_create_dataset -gert_to3d_prefix %File-Name% -gert_outdir %Output-Dir%')
            self.main_ui.edt_down_status.setText("Status: Please confirm the arguments to Dimon")
            self.main_ui.edt_down_status.setStyleSheet("color: rgb(128,128,0);")
        else:
            self.main_ui.edt_down_cmd.setText(CUST_PROG_CONV)
            self.main_ui.edt_down_status.setText("Status: Dimon not found. Please Enter proper conversion command")
            self.main_ui.edt_down_status.setStyleSheet("color: rgb(255,0,0);")
        self.download_cmd_refresh()
    
    def nifti_clicked(self):
        """
        When Radio Button for NIFTI is clicked
        """
        #Afni doesn't run on Windows
        self.main_ui.grp_down_format.setStyleSheet(_fromUtf8("background-color:;"))
        self.d_format=3
        if self.prog_exists('Dimon'):
            self.main_ui.edt_down_cmd.setText('Dimon -infile_pattern %Output-Dir%/* -dicom_org -gert_create_dataset -gert_write_as_nifti -gert_to3d_prefix %File-Name% -gert_outdir %Output-Dir%')
            self.main_ui.edt_down_status.setText("Status: Please confirm the arguments to Dimon")
            self.main_ui.edt_down_status.setStyleSheet("color: rgb(128,128,0);")
        else:
            self.main_ui.edt_down_cmd.setText(CUST_PROG_CONV)
            self.main_ui.edt_down_status.setText("Status: Dimon not found. Please Enter proper conversion command")
            self.main_ui.edt_down_status.setStyleSheet("color: rgb(255,0,0);")            
        self.download_cmd_refresh()
        
    
    def custom_clicked(self):
        """
        When Radio Button for Custom is clicked
        """
        self.main_ui.grp_down_format.setStyleSheet(_fromUtf8("background-color:;"))
        self.d_format=4
        if self.prog_exists('dcm2nii'):
            if system()=='Windows':
                self.main_ui.edt_down_cmd.setText('dcm2nii -e N -f Y -d N -p N -v N -g N %Output-Dir%\%File-Name%')
            else:
                self.main_ui.edt_down_cmd.setText('dcm2nii -e N -f Y -d N -p N -v N -g N %Output-Dir%/%File-Name%')
            self.main_ui.edt_down_status.setText("Status: Please confirm the arguments to dcm2nii are correct")
            self.main_ui.edt_down_status.setStyleSheet("color: rgb(255,140,0);")
        else:
            self.main_ui.edt_down_cmd.setText(CUST_PROG_CONV)
            self.main_ui.edt_down_status.setText("Status: Please Enter proper conversion command")
            self.main_ui.edt_down_status.setStyleSheet("color: rgb(255,0,0);")
        self.download_cmd_refresh()
    
    def dcm_clicked(self):
        """
        When Radio Button for DICOM is clicked
        """
        self.main_ui.grp_down_format.setStyleSheet(_fromUtf8("background-color:;"))
        self.d_format=1
        self.main_ui.edt_down_status.setText("Status: Ready. No Conversion needed")
        self.main_ui.edt_down_cmd.setText(os.path.join('%Output-Dir%','%File-Name%-######'))
        self.main_ui.edt_down_status.setStyleSheet("color: rgb(107,142,35);")
        self.download_cmd_refresh()
                    
    def prog_exists(self,prog_name): 
        """
        Checking if the program exists in the environment
        """
        try:
            devnull = open(os.devnull)
            subprocess.Popen([prog_name],stdout=devnull,stderr=devnull).communicate()
        except OSError as e:
            if e.errno == os.errno.ENOENT:
                return False
        return True

    def refresh_page4(self):
        pass
            
    def refresh_page5(self):

        header = ['Subject', 'Session', 'ScanID', 'ScanType','Quality']
        data_list=[]
        # 3 flags , Subj_checked, Sess_checked, Scan_checked
        if self.fl_Subj_checked and not self.fl_Sess_checked and not self.fl_Scan_checked:
            header=header[:1]
            for subj,sess_dict in self.dict_checked_all.items():
                data_list.append((subj,))
        elif self.fl_Subj_checked and self.fl_Sess_checked and not self.fl_Scan_checked:
            header=header[:2]
            for subj,sess_dict in self.dict_checked_all.items():
                for sess,scan_dict in sess_dict.items():
                    data_list.append((subj,sess))
        elif self.fl_Subj_checked and self.fl_Sess_checked and self.fl_Scan_checked:
            for subj,sess_dict in self.dict_checked_all.items():
                for sess,scan_dict in sess_dict.items():
                    for sc_id,sc_type in scan_dict[1][1].items():
                        data_list.append((subj,sess,sc_id,sc_type,self.lookup_scan_quality(subj,sess,sc_id)))
        
        self.main_ui.tableView.setModel(MyTableModel(self,data_list,header))
        self.main_ui.tableView.setSortingEnabled(True)

    
    def refresh_page6(self):
        self.PopupDlg(" This shouldn't be clicked, did you mess with the code ?? ")
        

    def page1_clicked(self):
        self.main_ui.stackedWidget.setCurrentIndex(0)
        if self.fl_refresh_page1:
            self.fl_refresh_page1=False
            self.refresh_page1()
        
    def page2_clicked(self):
        self.main_ui.stackedWidget.setCurrentIndex(1)
        self.fl_refresh_page3=True
        if self.fl_refresh_page2:
            self.fl_refresh_page2=False
            self.refresh_page2()
        
    def page3_clicked(self):
        self.main_ui.stackedWidget.setCurrentIndex(2)
        if self.fl_refresh_page3:
            self.fl_refresh_page3=False
            self.refresh_page3()
        
    def page4_clicked(self):
        self.main_ui.stackedWidget.setCurrentIndex(3)
        if self.fl_refresh_page4:
            self.fl_refresh_page4=False
            self.refresh_page4()
        
    def page5_clicked(self):
        self.main_ui.stackedWidget.setCurrentIndex(4)
        if self.fl_refresh_page5:
            self.fl_refresh_page5=False
            self.refresh_page5()
        
    def page6_clicked(self):
        self.main_ui.stackedWidget.setCurrentIndex(5)
        if self.fl_refresh_page6:
            self.fl_refresh_page6=False
            self.refresh_page6()
        
        
    def sign_in(self):
        """
        When the User Clicks the SignIn Button
        """
        self.host=str(self.main_ui.edt_host.text())
        self.uname=str(self.main_ui.edt_username.text())
        self.passwd=str(self.main_ui.edt_pwd.text())
        #print ("Signing In")
        #print("Host:"+host)
        if self.host=="" or self.uname=="" or self.passwd=="":
            self.PopupDlg("Please Enter all information !!")
        else:
            #print("Success")
            self.XConn=XnatRest(self.host,self.uname,self.passwd,False)
            self.projects=self.XConn.getProjects()
            if self.projects==0:
                self.PopupDlg("Something doesn't seem right. Check your Username/Password/Hostname")
                
            else:
                self.main_ui.lbl_status.setVisible(True)
                self.main_ui.lbl_status.setStyleSheet(_fromUtf8("background-color:#4d9900;"))
                self.main_ui.lbl_status.setText('  SUCCESS')
                #print(self.projects)
                self.main_ui.cmb_project.addItem("---SELECT---")
                self.main_ui.cmb_project.addItems(self.projects)
                
            self.main_ui.edt_pwd.setText("")
            #/data/projects/TEST/subjects/1/experiments/MR1/scans/1/resources/DICOM/files

    def scan_quality_checked(self):
        """
        When any of the scan_quality checkboxes are checked/Unchecked
        """
#        root=self.main_ui.tree_scans.invisibleRootItem()
#        qlabels=self.getCheckedScanQualityLabels()
#        for index in range(root.childCount()):
#            for ind2 in range(root.child(index).childCount()):
#                subj,scans=self.lookup_session(root.child(index).child(ind2).text(0))
#                if self.lookup_scan_quality(subj,root.child(index).child(ind2).text(0),root.child(index).child(ind2).statusTip(0)) in qlabels:
#                    print("Need this quality")
#                hello
        #Cleanup prior data
        self.main_ui.tree_scans.clear()        
        self.main_ui.tree_sessions.blockSignals(True)
                
        root=self.main_ui.tree_sessions.invisibleRootItem()
        for index in range(root.childCount()):
            item=root.child(index)
            if item.checkState(0) == QtCore.Qt.Checked:  #Checked                
                if item.childCount()==0:
                    sess_det =self.lookup_session(item.text(0)) #Get's subjID & scan details
                    self.handle_sess_Chk(sess_det[0],item.text(0))
                else:
                    for child in range(item.childCount()):
                        sess_det= self.lookup_session(item.child(child).text(0))  #Get's subjID & scan details
                        self.handle_sess_Chk(sess_det[0],item.child(child).text(0))
                        
#            elif item.checkState(0) == QtCore.Qt.Unchecked:  #Unchecked
#                
#                if item.childCount()==0:
#                    sess_det =self.lookup_session(item.text(0)) #Get's subjID & scan details
#                    self.handle_sess_UnChk(sess_det[0],item.text(0))
#                else:
#                    for child in range(item.childCount()):
#                        sess_det= self.lookup_session(item.child(child).text(0))  #Get's subjID & scan details
#                        self.handle_sess_UnChk(sess_det[0],item.child(child).text(0))
        self.main_ui.tree_sessions.blockSignals(False)
                

    def getCheckedScanQualityLabels(self):
        """
        returns the list of quality labels that are checked.
        """
        chkLabels=[]
        for chkBox in self.scan_quality_checkBoxes:
            if chkBox.isChecked():
                chkLabels.append(chkBox.text())
        return chkLabels
    def getCheckedResourceLabels(self):
        """
        returns the list of quality labels that are checked.
        """
        chkLabels=[]
        for chkBox in self.resource_checkBoxes:
            if chkBox.isChecked():
                chkLabels.append(chkBox.text())
        return chkLabels
    
    def res_type_checked(self):
        """
        When any of the resources checkboxes are checked/Unchecked
        """
        self.scan_quality_checked()

    def createScanQualityCheckBoxes(self):
        """
        Getting the xnat system-wide scan quality labels and resetting the Scan Quality Checkboxes
        """
        self.scan_quality_labels=self.XConn.getQualityLabels()
        if self.scan_quality_labels !=0:
            #print("Found labels")
            if len(self.scan_quality_labels) >len(self.scan_quality_checkBoxes):
                self.PopupDlg("This Xnat has too many scan Quality Labels. Keeping only first %d"%len(self.scan_quality_checkBoxes))
                self.scan_quality_labels=self.scan_quality_labels[:len(self.scan_quality_checkBoxes)]
            i=0
            for qualityLbl in self.scan_quality_labels:
                self.scan_quality_checkBoxes[i].setText(qualityLbl)
                self.scan_quality_checkBoxes[i].setChecked(True)
                i+=1
            for chkBox in range(i,len(self.scan_quality_checkBoxes)):
                self.scan_quality_checkBoxes[i].setChecked(False)
                self.scan_quality_checkBoxes[i].setVisible(False)
                i+=1
    def addResourceCheckBox(self,label):
        """
        Adding an additional Checkbox for the newly found resource
        """
        if len(self.resource_labels) == len(self.resource_checkBoxes):
            self.PopupDlg("Some of the scan/s may have too many Resources. Keeping only first %d"%len(self.resource_checkBoxes))
        else:
            self.resource_labels.append(label)
            i=0
            for res_lbl in self.resource_labels:                
                self.resource_checkBoxes[i].setText(res_lbl)
                self.resource_checkBoxes[i].setChecked(True)
                self.resource_checkBoxes[i].setVisible(True)
                i+=1
            for chkBox in range(i,len(self.resource_checkBoxes)):                
                self.resource_checkBoxes[i].setChecked(False)
                self.resource_checkBoxes[i].setVisible(False)
                i+=1
            
        
    
#    def removeResourceCheckBox(self,label):
#        self.resource_labels.remove(label)

    def populate_subjects(self):
        """
        Populating the Subject List in the UI
        """
        if self.main_ui.cmb_project.currentIndex()!=0:
            #print("Populating: "+str(self.curr_proj))
            self.li_subs.extend(self.XConn.getSubjects(self.curr_proj))
            # Populate the Subject List
            for sub in self.li_subs:
                tmp_item=QtWidgets.QListWidgetItem(sub['label'])
                tmp_item.setToolTip(sub['ID'])
                tmp_item.setCheckState(0)
                self.main_ui.lst_subjects.addItem(tmp_item)

            #Enabling Upload Tab
            #self.main_ui.btn_page4.setEnabled(True)
    
        
    def index_proj_changed(self):
        """
        If the index of the combobox of available projects changes.
        """
        if self.main_ui.cmb_project.currentIndex()!=0:
            #print(self.main_ui.cmb_project.currentText())
            self.main_ui.grp_what.setEnabled(True)
            self.curr_proj=self.main_ui.cmb_project.currentText()
            self.reset_internal()
            if self.main_ui.rb_sel_download.isChecked():
                self.download_selected()
            elif self.main_ui.rb_sel_upload.isChecked():
                self.upload_selected()
            if not self.main_ui.rb_sel_download.isChecked() and not self.main_ui.rb_sel_upload.isChecked():
                self.main_ui.grp_what.setStyleSheet(_fromUtf8("background-color:#e0ffba;"))
            
    def reset_all_clicked(self):
        """
        When the 'Reset All' button is clicked
        """
        self.main_ui.cmb_project.setCurrentIndex(0)
        self.reset_all()


    def reset_source(self):
        self.main_ui.pb_final.setValue(0)
        self.main_ui.pb_inter.setValue(0)
        self.main_ui.lst_subjects.clear()
        del self.li_subs[:]
        self.dict_checked_all.clear()
        self.tree_all.clear()
        self.main_ui.tree_sessions.clear()
        self.main_ui.tree_scans.clear()
        if self.fl_subjects_selection and self.fl_sessions_selection:
            self.main_ui.lst_subjects.setEnabled(True)
        else:
            self.main_ui.lst_subjects.setEnabled(False)
        

    def reset_destination(self):
        self.main_ui.pb_final.setValue(33)
        self.main_ui.pb_inter.setValue(0)
        self.delete_layout(self.main_ui.grp_path.layout())
        self.selected_uniq_scans.clear()
        del self.main_ui.grp_allScans[:] #Deleting contents of the list

    def reset_export(self)        :
        self.fl_Subj_checked=False
        self.fl_Sess_checked=False
        self.fl_Scan_checked=False

    def reset_download(self):
        self.main_ui.pb_final.setValue(66)
        self.main_ui.pb_inter.setValue(0)
        self.main_ui.lst_sel_log.clear()
        self.main_ui.lst_dest_pick.clear()
        self.main_ui.lst_filename.clear()
        self.main_ui.lst_cmd.clear()
        
    def reset_upload(self):
        #self.main_ui.pb_final.setValue(50)
        self.main_ui.pb_inter.setValue(0)
        self.main_ui.tree_upload_main.clear()
    
    def reset_process(self):
        """
        Nothing in here for now.
        """
        #print("This may never print")
        pass

    def reset_internal(self):
        if self.main_ui.rb_sel_download.isChecked():
            self.prep_download()
        elif self.main_ui.rb_sel_upload.isChecked():
            self.prep_upload()
        if not self.main_ui.rb_sel_download.isChecked() and not self.main_ui.rb_sel_upload.isChecked():
            self.main_ui.grp_what.setStyleSheet(_fromUtf8("background-color:#e0ffba;"))
            
        self.reset_process()
        self.reset_upload()
        self.reset_export()
        self.reset_download()
        self.reset_destination()
        self.reset_source()
        self.reset_variables()
        
    def delete_layout(self,layout):
        """
        A helper function needed to remove widgets
        """
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.deleteLayout(item.layout())
            sip.delete(layout)
    
    def reset_variables(self):
        """
        Cleaning the memory
        """
        # Lists and Dictionaries
        del self.li_subs[:] #List of subjects as received
        self.dict_checked_all.clear() #Dictionary of selected subjects
        
        self.tree_all.clear() # A dict of dict of dict for everything

        #For Destination Tab
        del self.main_ui.grp_allScans[:]
        self.selected_uniq_scans.clear()      

        #For Download Tab        
        self.d_format=1  #1=DCM, 2=AFNI , 3=NIFTI, 4=CUSTOM
        self.download_begin=0  #Flag to start downloading        
        
    def reset_all(self):
        """
        To have a clean slate
        """
        self.reset_variables()
        #self.get_projects()
        self.main_ui.tree_sessions.setEnabled(True)
        self.main_ui.lst_subjects.setEnabled(False)
        #self.curr_proj=self.main_ui.cmb_project.currentText()
        #Reset RadioButtons
        self.main_ui.rb_sel_upload.setAutoExclusive(False)
        self.main_ui.rb_sel_download.setAutoExclusive(False)
        self.main_ui.rb_sel_upload.setChecked(False)
        self.main_ui.rb_sel_download.setChecked(False)
        self.main_ui.rb_sel_upload.setAutoExclusive(True)
        self.main_ui.rb_sel_download.setAutoExclusive(True)
        #Reset More radio buttons        
        self.main_ui.rb_subj_res.setAutoExclusive(False)
        self.main_ui.rb_subj_sess.setAutoExclusive(False)
        self.main_ui.rb_sess_scans.setAutoExclusive(False)
        self.main_ui.rb_sess_res.setAutoExclusive(False)
        self.main_ui.rb_subj_res.setChecked(False)
        self.main_ui.rb_subj_sess.setChecked(False)
        self.main_ui.rb_sess_scans.setChecked(False)
        self.main_ui.rb_sess_res.setChecked(False)
        self.main_ui.rb_subj_res.setAutoExclusive(True)
        self.main_ui.rb_subj_sess.setAutoExclusive(True)
        self.main_ui.rb_sess_scans.setAutoExclusive(True)
        self.main_ui.rb_sess_res.setAutoExclusive(True)
        
        self.main_ui.grp_what.setEnabled(False)
        self.refresh_page1=True
        #Reset CheckBoxes
        for chkbox in self.scan_quality_checkBoxes:
            if chkbox.isVisible():
                chkbox.setChecked(True)
        for chkbox in self.resource_checkBoxes:
            if chkbox.isVisible():
                chkbox.setChecked(True)
        self.page1_clicked()
        self.reset_internal()
    
    def disable_all(self):
        """
        To disable all buttons while download or Upload process is underway. 
        """
        self.main_ui.btn_download.setEnabled(False)
        self.main_ui.btn_refresh_cmd.setEnabled(False)
        self.main_ui.grp_down_format.setEnabled(False)
        self.main_ui.btn_page1.setEnabled(False)
        self.main_ui.btn_page2.setEnabled(False)
        self.main_ui.btn_page3.setEnabled(False)
        self.main_ui.btn_page4.setEnabled(False)
        self.main_ui.btn_page5.setEnabled(False)
        self.main_ui.btn_page6.setEnabled(False)
        self.main_ui.btn_SignIn.setEnabled(False)
        self.main_ui.grp_what.setEnabled(False)
        self.main_ui.cmb_project.setEnabled(False)
        self.main_ui.btn_refresh.setEnabled(False)
        self.main_ui.btn_reset.setEnabled(False)
        self.main_ui.btn_export_csv.setEnabled(False)
        self.main_ui.btn_export_xlsx.setEnabled(False)
        self.main_ui.btn_up_res.setEnabled(False)
        self.main_ui.btn_upload.setEnabled(False)
        
        
        
        
    def strip_sub_id(self,subj,sess):
        return str(str(sess).replace(str(subj),"").strip('-').strip('_').strip('(').strip(')'))
    def strip_tail(self,str_strip):
        return str(str_strip).split("(")[0]
        
    def download_selected(self):
        self.reset_internal()
        #self.prep_download() #reset_internal takes care of this
        self.createScanQualityCheckBoxes()
        self.page1_clicked()
        self.populate_subjects()
        self.main_ui.grp_what.setStyleSheet(_fromUtf8("background-color:;"))
        self.main_ui.grp_subj_select.setStyleSheet(_fromUtf8("background-color:#e0ffba;"))
        
    def prep_download(self):
        """
        Prepare the UI for downloading
        """
        self.main_ui.tree_sessions.setEnabled(False)
        self.main_ui.btn_page1.setEnabled(True)
        self.main_ui.btn_page1.setVisible(True)
        self.main_ui.btn_page2.setEnabled(False)
        self.main_ui.btn_page2.setVisible(True)
        self.main_ui.btn_page3.setEnabled(False)
        self.main_ui.btn_page3.setVisible(True)
        self.main_ui.btn_page4.setEnabled(False)
        self.main_ui.btn_page4.setVisible(False)
        self.main_ui.btn_page5.setEnabled(True)
        self.main_ui.btn_page5.setVisible(True)
        self.main_ui.btn_page6.setEnabled(False)
        self.main_ui.btn_page6.setVisible(False)
        self.main_ui.grp_sess_select.setVisible(True)
        self.main_ui.grp_download_method.setEnabled(True)
        
    def upload_selected(self):
        self.reset_internal()
        #self.prep_upload() #reset_internal takes care of this
        self.createScanQualityCheckBoxes()
        self.page1_clicked()
        self.populate_subjects()
        self.main_ui.grp_what.setStyleSheet(_fromUtf8("background-color:;"))
        self.main_ui.grp_subj_select.setStyleSheet(_fromUtf8("background-color:#e0ffba;"))
        
    def prep_upload(self):
        """
        Prepare the UI for uploading
        """
        self.main_ui.tree_sessions.setEnabled(True)
        self.main_ui.btn_page1.setEnabled(True)
        self.main_ui.btn_page1.setVisible(True)
        self.main_ui.btn_page2.setEnabled(False)
        self.main_ui.btn_page2.setVisible(False)
        self.main_ui.btn_page3.setEnabled(False)
        self.main_ui.btn_page3.setVisible(False)
        self.main_ui.btn_page4.setEnabled(True)
        self.main_ui.btn_page4.setVisible(True)
        self.main_ui.btn_page5.setEnabled(False)
        self.main_ui.btn_page5.setVisible(False)
        self.main_ui.btn_page6.setEnabled(False)
        self.main_ui.btn_page6.setVisible(False)
        self.main_ui.grp_sess_select.setVisible(True)
        
        
    def loadConfig(self):
        """
        Loads the config file in a dictionary 
        """
        with open("xnat_config.yaml",'r') as sysConfigF:
            self.sysConfig= yaml.load(sysConfigF)
        if self.sysConfig['sys-init']['cache-location'][0]=='~':
            self.sysConfig['sys-init']['cache-location'][0]=os.path.expanduser("~")
            
        #Load host
        self.main_ui.edt_host.setText(self.sysConfig['sys-init']['host'])
        #Reads Username from system and loads it
        self.main_ui.edt_username.setText(getpass.getuser())
        self.main_ui.edt_pwd.setFocus()
        
    def initDirs(self):
        """
        Initialize the directories. Make them if they don't exist yet.
        """
        xcache=''
        for dirname in self.sysConfig['sys-init']['cache-location']:
            xcache=os.path.join(xcache,dirname)
        self.makeDirsIfNotExist(xcache)
                    
    def makeDirsIfNotExist(self,path):
        """
        Make directories recursively if they dont exist
        Can add more permission checking exceptions and popups here.
        """
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except os.error as e:
                if e.errno !=errno.EEXIST:
                    raise
                    
                    
    def loadUserConfig(self):
        """
        Reads in the config file for the user. Creates a file if one doesn't exist already. 
        Stores user cache
        """
        pass

    def PopupDlg(self,msg_show):
        """
        Simplistic Popup DialogBox
        """
        self.dlg=MyPopupDlg(msg_show)
        self.dlg.exec_()  #For modal dialog
        
                      
    def DownloadWarningMultipleResources(self,res_list):
       msg = QtWidgets.QMessageBox()
       msg.setIcon(QtWidgets.QMessageBox.Warning)
       msg.setText("Sure ??")
       msg.setInformativeText("You have selected multiple resource types. Are you sure?")
       msg.setWindowTitle("Multiple Resources WARNING")
       msg.setDetailedText("You have Checked Multiple resources.\nThis would make multiple directories :%s  , under the scan directory.\n Would you like to continue?" %(",".join(res_list)))
       msg.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
       #msg.buttonClicked.connect(self.MsgBoxBtn)
       return msg.exec_()
                      
    def DownloadMsgBox(self,dformat):
       if dformat==1:
           dfformat='DICOM'
       elif dformat==2:
           dfformat='AFNI'
       elif dformat==3:
           dfformat='NIFTI'
       elif dformat==4:
           dfformat='CUSTOM'
       msg = QtWidgets.QMessageBox()
       msg.setIcon(QtWidgets.QMessageBox.Information)
       msg.setText("READY ??")
       msg.setInformativeText("All scans will be downloaded in %s format" %(dfformat))
       msg.setWindowTitle("Begin Download")
       msg.setDetailedText("Do not close the main window until you see the Finish Popup. \nCheck the progress bar for status.\nAfter all is done, Check the Log for any problems during download or conversion")
       msg.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
       #msg.buttonClicked.connect(self.MsgBoxBtn)
       return msg.exec_()
                      
    def closeEvent(self,event):
        result = QtWidgets.QMessageBox.question(self,
                      "Confirm Exit...",
                      "Are you sure you want to exit ?",
                      QtWidgets.QMessageBox.Yes| QtWidgets.QMessageBox.No)
        #event.ignore()

        if result == QtWidgets.QMessageBox.Yes:
#            try:
#                self.xnat_intf.disconnect()   #Disconnect the Xnat Interface before exiting
#            except:
#                pass
            event.accept()

class MyTableModel(QtCore.QAbstractTableModel):
    def __init__(self,parent,mylist,header,*args):
        QtCore.QAbstractTableModel.__init__(self,parent,*args)
        self.mylist=mylist
        self.header=header
    def rowCount(self,parent):
        return len(self.mylist)
    def columnCount(self,parent):
        return len(self.mylist[0])
    def data(self,index,role):
        if not index.isValid():
            return None
        elif role !=QtCore.Qt.DisplayRole:
            return None
        return self.mylist[index.row()][index.column()]
    def headerData(self,col,orientation,role):
        if orientation ==QtCore.Qt.Horizontal and role==QtCore.Qt.DisplayRole:
            return self.header[col]
        return None
    def sort(self,col,order):
        """
        Sort table by given column number
        """
        self.layoutAboutToBeChanged.emit()
        self.mylist = sorted(self.mylist,key=operator.itemgetter(col))
        if order == QtCore.Qt.DescendingOrder:
            self.mylist.reverse()
        self.layoutChanged.emit()


class MyPopupDlg(QtWidgets.QDialog):
    def __init__(self,msg,parent=None):
        #self.resize(300,200)
        super(MyPopupDlg, self).__init__(parent)
        layout=QtWidgets.QGridLayout(self)
        lbl=QtWidgets.QLabel(msg)
        #btn=QtGui.QPushButton("Ok")
        btn=QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok,QtCore.Qt.Horizontal,self)
        btn.accepted.connect(self.accept)
        layout.addWidget(lbl)
        layout.addWidget(btn)


def downloadRequest(host,uname,passwd,jobDefs): #To run this with download_async make it async (i.e. async def downloadRequest(blah,blah))
    """
    Helper function for download_clicked. Download the files here
    """
    #tmp=','.join(str(e) for e in jobDefs)
    
    #items in jobDefs - 0: Download Format
    #                 - 1: Download directory
    #                 - 2: DOwnload filename
    #                 - 3: main resource URI 
    #                 - 4: download structure
    #                 - 5: Counter
    if jobDefs[0]==1:
        #Direct download no conversion
        print ("Now Getting >>>: %s"%jobDefs[1])
        #Make directories first
        if not os.path.exists(jobDefs[1]):
            try:
                os.makedirs(jobDefs[1])
            except os.error as e:
                if e.errno !=errno.EEXIST:
                    raise
        
        # Getting resources as zip and exploding them seems like a faster way to retrieve files at this time. 
        # Compared it to downloading each file one at a time, and it is considerably slower.
        #Creating new connection object.
        XConn=XnatRest(host,uname,passwd,False)
        if XConn.getZip(jobDefs[3],jobDefs[1],jobDefs[2]):
            cleanUpDownload(jobDefs[1],jobDefs[2])
            return "Success: "+jobDefs[3]
        else:
            return "Failed GET: "+jobDefs[3] #Will fail if 404 in GET (or any issues with GET)
        
        
    elif jobDefs[0]==2:
        #Converting to AFNI after downloading
        print ("Got 2 for >>>: %s"%jobDefs[1])
        return "Success: "+jobDefs[3]
        
    elif jobDefs[0]==3:
        #Converting to NIFTI after downloading
        print ("Got 3 for >>>: %s"%jobDefs[1])
        return "Success: "+jobDefs[3]
    elif jobDefs[0]==3:
        #Run custom script after downloading
        print ("Got 3 for >>>: %s"%jobDefs[1])
        return "Success: "+jobDefs[3]
        
    return "Failed: "+jobDefs[3]

def cleanUpDownload(path,filename):
    """
    Extracts the zipfile and re-structures the directory structure as asked.
    This function can be made better.
    This is the dumbest thing, cannot extract each file to custom location, 
    it has to be in the same internal directory structure as the zip file.
    """
    #TODO: COnsider the situation : DICOM & SNAPSHOTS is selected but scan 1 doesn't have SNAPSHOTS resource. -> getZip gives Oops Error code 404
    if os.path.isfile(os.path.join(path,filename)):
        #Need a try except block for the zipfile stuff
        zipFileName=zipfile.ZipFile(os.path.join(path,filename))
        zipFileName.extractall(path)
        allFiles=zipFileName.namelist()
#        for zfile in zipFileName.namelist():
#            zipFileName.extract(zfile,path)
        zipFileName.close()
        
        #Adding try block here doesn't seem necessary , as yet. 
        os.remove(os.path.join(path,filename))
        
        #Flag to check if all files moved successfully
        f_renamed=True
        for aFile in allFiles:
            fPath=aFile.split('/')
            try: #filename[:-4] to remove the .zip extension from the name
                os.rename(os.path.join(path,os.path.join(*fPath)),os.path.join(path,filename[:-4]+'-'+fPath[-1]))
            except os.error as e:
                f_renamed=False
                raise #Do logging instead of raising
                
        if f_renamed: #If all files successfully moved, then delete the directory
            try:
                # A bit of a risky thing to do. But o well. :)
                shutil.rmtree(os.path.join(path,allFiles[0].split('/')[0])) #,ignore_errors=True)
            except os.error as e:
                # Ignoring Errors, so this is kind of useless
                if e.errno !=errno.EEXIST:
                    raise #Do logging instead of raising


if __name__ == "__main__":
    
    app = QtWidgets.QApplication.instance() #Checks if QApplication already exists    
    if not app:
        app = QtWidgets.QApplication(sys.argv)
    myapp = StartQT()
    app_icon=QtGui.QIcon()
    app_icon.addFile('icons/brain_16_icon.ico',QtCore.QSize(16,16))
    app_icon.addFile('icons/brain_24_icon.ico',QtCore.QSize(24,24))
    app_icon.addFile('icons/brain_32_icon.ico',QtCore.QSize(32,32))
    app_icon.addFile('icons/brain_48_icon.ico',QtCore.QSize(48,48))
    app_icon.addFile('icons/brain_64_icon.ico',QtCore.QSize(64,64))
    app_icon.addFile('icons/brain_128_icon.ico',QtCore.QSize(128,128))
    app_icon.addFile('icons/brain_192_icon.ico',QtCore.QSize(192,192))
    app_icon.addFile('icons/brain_256_icon.ico',QtCore.QSize(256,256))
    app_icon.addFile('icons/brain_96_icon.ico',QtCore.QSize(96,96))
    myapp.setWindowIcon(app_icon)
    myapp.show()
    sys.exit(app.exec_())