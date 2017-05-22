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
import requests
import getpass
import sip

#Headers for the Upload Tree
SESS_HEADERS=('1','2','3','4')

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
        
        self.main_ui.rb_sel_download.clicked.connect(self.download_selected)
        self.main_ui.rb_sel_upload.clicked.connect(self.upload_selected)
        
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
        
        #Variables with data
        self.curr_proj=None #Currently selected Xnat Project
        
        # Lists and Dictionaries
        self.li_subs=[] #List of subjects as received
        self.dict_checked_all={} #Dictionary of selected subjects
        
        self.tree_all={} # A dict of dict of dict for everything

        #For Destination Tab
        self.main_ui.grp_allScans=[]
        self.selected_uniq_scans={}      

        #For Download Tab        
        self.d_format=1  #1=DCM, 2=AFNI , 3=NIFTI, 4=CUSTOM
        self.download_begin=0  #Flag to start downloading        
        
        
        #Initialize stuff
        self.loadConfig()
        self.initDirs()
        self.loadUserConfig()
        
        
        #Disabling Buttons 
        self.main_ui.btn_page1.setEnabled(False)
        self.main_ui.btn_page2.setEnabled(False)
        self.main_ui.btn_page3.setEnabled(False)
        self.main_ui.btn_page4.setEnabled(False)
        self.main_ui.btn_page5.setEnabled(False)
        self.main_ui.btn_page6.setEnabled(False)
        
        #Flags to trigger tab refresh
        self.fl_refresh_page1=True
        self.fl_refresh_page2=True
        self.fl_refresh_page3=True
        self.fl_refresh_page4=True
        self.fl_refresh_page5=True
        self.fl_refresh_page6=True
        
        
        self.main_ui.grp_what.setEnabled(False)
        self.main_ui.grp_download_method.setEnabled(False)

        self.page1_clicked() #Go to the first page.
    

    @memoise
    def lookup_session(self,sess):
        
        for k_sub, v_sess in self.dict_checked_all.iteritems():
            for k_sess, v_scans in v_sess.iteritems():
                if k_sess==sess:
                    return(k_sub,v_scans)
        return None
            
    def refresh_page1(self):
        self.reset_process()
        self.reset_export()
        self.reset_upload()
        self.reset_download()
        self.reset_destination()
        self.populate_subjects()
            
            
    def refresh_page2(self):
        self.reset_process()
        #self.reset_upload()
        self.reset_download()
            
    def refresh_page3(self):
        self.reset_process()
        #self.reset_upload()
            
    def refresh_page4(self):
        pass
            
    def refresh_page5(self):
        pass
            
    def refresh_page6(self):
        self.PopupDlg("This area is under Development ")
        

    def page1_clicked(self):
        self.main_ui.stackedWidget.setCurrentIndex(0)
        if self.fl_refresh_page1:
            self.fl_refresh_page1=False
            self.refresh_page1()
        
    def page2_clicked(self):
        self.main_ui.stackedWidget.setCurrentIndex(1)
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
        host=str(self.main_ui.edt_host.text())
        uname=str(self.main_ui.edt_username.text())
        passwd=str(self.main_ui.edt_pwd.text())
        print ("Signing In")
        #print("Host:"+host)
        if host=="" or uname=="" or passwd=="":
            self.PopupDlg("Please Enter all information !!")
        else:
            print("Success")
            self.XConn=XnatConnection(host,uname,passwd,False)
            self.projects=self.XConn.getProjects()
            if self.projects==0:
                self.PopupDlg("Something doesn't seem right. Check your Username/Password/Hostname")
                
            else:
                self.main_ui.lbl_status.setVisible(True)
                self.main_ui.lbl_status.setStyleSheet(_fromUtf8("background-color:#4d9900;"))
                self.main_ui.lbl_status.setText('  SUCCESS')
                print(self.projects)
                self.main_ui.cmb_project.addItem("---SELECT---")
                self.main_ui.cmb_project.addItems(self.projects)
            self.main_ui.edt_pwd.setText("")

                
    def populate_subjects(self):
        print("Start Populating!")
        if self.main_ui.cmb_project.currentIndex()!=0:
            print("Populating: "+self.curr_proj)
            self.li_subs.extend(self.XConn.getSubjects(self.curr_proj))
            # Populate the Subject List
            for sub in self.li_subs:
                tmp_item=QtWidgets.QListWidgetItem(sub['label'])
                print(sub['label'])
                tmp_item.setToolTip(sub['ID'])
                tmp_item.setCheckState(0)
                self.main_ui.lst_subjects.addItem(tmp_item)

            #Enabling Upload Tab
            #self.main_ui.btn_page4.setEnabled(True)
    
        
    def index_proj_changed(self):
        print("Index Changed")
        if self.main_ui.cmb_project.currentIndex()!=0:
            print(self.main_ui.cmb_project.currentText())
            self.main_ui.grp_what.setEnabled(True)
            self.curr_proj=self.main_ui.cmb_project.currentText()
            self.reset_internal()
            print("About to Populate Subjects")
            self.populate_subjects()
            
    def reset_all_clicked(self):
        self.main_ui.cmb_project.setCurrentIndex(0)
        self.reset_all()


    def reset_source(self):
        print("Resetting Source")
        self.main_ui.pb_final.setValue(0)
        self.main_ui.pb_inter.setValue(0)
        self.main_ui.lst_subjects.clear()
        del self.li_subs[:]
        self.dict_checked_all.clear()
        self.tree_all.clear()
        self.main_ui.tree_sessions.clear()
        self.main_ui.tree_scans.clear()
        self.main_ui.lst_subjects.setEnabled(True)
        

    def reset_destination(self):
        print("Resetting Destination")
        self.main_ui.pb_final.setValue(33)
        self.main_ui.pb_inter.setValue(0)
        self.delete_layout(self.main_ui.grp_path.layout())
        self.selected_uniq_scans.clear()
        del self.main_ui.grp_allScans[:] #Deleting contents of the list

    def reset_export(self)        :
        pass

    def reset_download(self):
        print("Resetting Download")
        self.main_ui.pb_final.setValue(66)
        self.main_ui.pb_inter.setValue(0)
        self.main_ui.lst_sel_log.clear()
        self.main_ui.lst_dest_pick.clear()
        self.main_ui.lst_filename.clear()
        self.main_ui.lst_cmd.clear()
        
    def reset_upload(self):
        print("Resetting Upload")
        #self.main_ui.pb_final.setValue(50)
        self.main_ui.pb_inter.setValue(0)
        self.main_ui.tree_upload_main.clear()
    
    def reset_process(self):
        print("Resetting Process")

    def reset_internal(self):
        print("Resetting Internal")
        self.reset_process()
        self.main_ui.btn_page5.setEnabled(False)
        self.reset_upload()
        self.main_ui.btn_page4.setEnabled(False)
        self.reset_download()
        self.main_ui.btn_page3.setEnabled(False)
        self.reset_destination()
        self.main_ui.btn_page2.setEnabled(False)
        self.reset_source()
        print("Done Resetting Internal")
        
  
    def delete_layout(self,layout):
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
        self.reset_variables()
        #self.get_projects()
        self.main_ui.tree_sessions.setEnabled(True)
        self.main_ui.lst_subjects.setEnabled(True)
        #self.curr_proj=self.main_ui.cmb_project.currentText()
        self.main_ui.grp_what.setEnabled(False)
        self.main_ui.rb_sel_download.setChecked(False)
        self.main_ui.rb_sel_upload.setChecked(False)
        self.change_tab0()
        self.reset_internal()
    
        
    def strip_sub_id(self,subj,sess):
        return str(str(sess).replace(str(subj),"").strip('-').strip('_').strip('(').strip(')'))
    def strip_tail(self,str_strip):
        return str(str_strip).split("(")[0]
        
    def download_selected(self):
        self.main_ui.btn_page1.setEnabled(True)
        self.main_ui.btn_page2.setEnabled(True)
        self.main_ui.btn_page3.setEnabled(True)
        self.main_ui.btn_page4.setEnabled(False)
        self.main_ui.btn_page5.setEnabled(True)
        self.main_ui.btn_page6.setEnabled(False)
        self.main_ui.grp_download_method.setEnabled(True)
        self.page1_clicked()
        
    def upload_selected(self):
        self.main_ui.btn_page1.setEnabled(True)
        self.main_ui.btn_page2.setEnabled(False)
        self.main_ui.btn_page3.setEnabled(False)
        self.main_ui.btn_page4.setEnabled(True)
        self.main_ui.btn_page5.setEnabled(False)
        self.main_ui.btn_page6.setEnabled(False)
        self.page1_clicked()
        
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
        if not os.path.exists(xcache):
            try:
                os.makedirs(xcache)
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
        
    def closeEvent(self,event):
        result = QtGui.QMessageBox.question(self,
                      "Confirm Exit...",
                      "Are you sure you want to exit ?",
                      QtGui.QMessageBox.Yes| QtGui.QMessageBox.No)
        event.ignore()

#        if result == QtGui.QMessageBox.Yes:
#            try:
#                self.xnat_intf.disconnect()   #Disconnect the Xnat Interface before exiting
#            except:
#                pass
#            event.accept()

class XnatConnection:
    def __init__(self,host,user,passwd,verify=True):
        # Set up session
        if host[-1]=='/':
            self.host=host[:-1]
        else:
            self.host=host
        self.user=user
        self.passwd=passwd
        self.verify=verify
        #self.xnat_session=None
        self.intf = requests.Session()
        self.intf.verify = False
        self.intf.auth = (self.user,self.passwd)
        
    def refresh(self):
        """
        Refreshes http connection to url
        """
        pass

    def getProjects(self):
        projects=self.get()
        proj_ids=[]
        for proj in projects:
            proj_ids.append(proj['ID'])
        return proj_ids
        
    def getSubjects(self,proj):
        """
       {'ID': 'Cerebra_S02566',
        'URI': '/data/subjects/Cerebra_S02566',
        'insert_date': '2016-07-27 13:27:23.636',
        'insert_user': 'moynihanbt',
        'label': '184612',
        'project': '000'},
        """
        return self.get(proj)
#        subjects =self.get(proj)
#        ret_subs=[]
#        for sub in subjects:
#            ret_subs.append({'ID':sub['ID'],'label':sub['label']})
#        return ret_subs
    def getExperiments(self,proj,subj):
        """
        {'ID': 'Cerebra_E03214',
            'URI': '/data/experiments/Cerebra_E03214',
            'date': '2017-02-23',
            'insert_date': '2017-03-02 09:57:35.695',
            'label': '185574-1',
            'project': '457',
            'xnat:subjectassessordata/id': 'Cerebra_E03214',
            'xsiType': 'xnat:mrSessionData'}
        """
        return self.get(proj,subj)
    def getScans(self,proj,subj,exp):
        """
        {'ID': '1',
          'URI': '/data/experiments/Cerebra_E03214/scans/1',
          'note': '',
          'quality': 'unknown',
          'series_description': 'localizer',
          'type': 'localizer',
          'xnat_imagescandata_id': '45077',
          'xsiType': 'xnat:mrScanData'},
        """
        return self.get(proj,subj,exp)

    def get(self,proj=None,subj=None,exp=None,scan=None):
        """
        Does a GET request according to the query
        """
        tail="?format=json"
        if proj==None:
            url="/data/archive/projects"
            result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
        elif subj==None:
            url="/data/archive/projects/"+proj+"/subjects"
            result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
        elif exp==None:
            url="/data/archive/projects/"+proj+"/subjects/"+subj+"/experiments"
            result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
        elif scan==None:
            url="/data/archive/projects/"+proj+"/subjects/"+subj+"/experiments/"+exp+"/scans"
            result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
            
    def _get(self,url):
        """
        Does a GET on the url
        """
        try:
            r = self.intf.get(url)
            r.raise_for_status()
        except (requests.ConnectionError, requests.exceptions.RequestException) as e:
            print ("Request Failed")
            print ("    " + str( e ))
            print ("    Please Check Username/Password")
            return 0
            #sys.exit(1)
        return r

    def _put(url,**kwargs):
        """
        Does a PUT on the url
        """
        try:
            r = intf.get( url, **kwargs )
            r.raise_for_status()
        except (requests.ConnectionError, requests.exceptions.RequestException) as e:
            print ("Request Failed")
            print ("    " + str( e ))
            sys.exit(1)
        return r

    def putFile():
        queryArgs = {"format":"csv","content":"QC Data","reference":os.path.abspath(os.path.join(dicomdir, f_name))}
        r = intf.put(host + "/data/experiments/%s/resources/QC/files" % (session), params=queryArgs)
        r.raise_for_status()

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