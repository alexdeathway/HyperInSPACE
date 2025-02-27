
import os
import datetime
import numpy as np

from HDFRoot import HDFRoot
from SeaBASSWriter import SeaBASSWriter
from CalibrationFileReader import CalibrationFileReader
from MainConfig import MainConfig
from ConfigFile import ConfigFile
from Utilities import Utilities
from AncillaryReader import AncillaryReader

from ProcessL1a import ProcessL1a
from ProcessL1aqc import ProcessL1aqc
from ProcessL1b import ProcessL1b
from ProcessL1bqc import ProcessL1bqc
from ProcessL2 import ProcessL2
from PDFreport import PDF


class Controller:

    @staticmethod
    def writeReport(fileName, pathOut, outFilePath, level, inFilePath):
        print('Writing PDF Report...')
        numLevelDict = {'L1A':1,'L1AQC':2,'L1B':3,'L1BQC':4,'L2':5}
        numLevel = numLevelDict[level]
        # fp = os.path.join(pathOut, level, f'{fileName}_{level}.hdf')

        # Reports are written during failure at any level or success at L2.
        # The highest level succesfully processed will have the correct configurations in the HDF attributes.

        #   Try to open current level. If this fails, open the previous level and use all the parameters
        #   from the attributes up to that level, then use the ConfigFile.settings for the current level parameters.
        try:
            # Processing successful at this level
            root = HDFRoot.readHDF5(outFilePath)
            fail = 0
            root.attributes['Fail'] = 0
        except:
            fail =1
            # Processing failed at this level. Open the level below it
            #   This won't work for ProcessL1A looking back for RAW...
            if level != 'L1A':
                try:
                    # Processing successful at the next lower level
                    # Shift from the output to the input directory
                    root = HDFRoot.readHDF5(inFilePath)
                except:
                    msg = "Controller.writeReport: Unable to open HDF file. May be open in another application."
                    Utilities.errorWindow("File Error", msg)
                    print(msg)
                    Utilities.writeLogFile(msg)
                    return

            else:
                # Create a root with nothing but the fail flag in the attributes to pass to PDF reporting
                #   PDF will contain parameters from ConfigFile.settings
                root = HDFRoot()
                root.id = "/"
                root.attributes["HYPERINSPACE"] = MainConfig.settings["version"]
                root.attributes['TIME-STAMP'] = 'Null' # Collection time not preserved in failed RAW>L1A
            root.attributes['Fail'] = 1


        timeStamp = root.attributes['TIME-STAMP']
        title = f'File: {fileName} Collected: {timeStamp}'

        # Reports
        reportPath = os.path.join(pathOut, 'Reports')
        if os.path.isdir(reportPath) is False:
            os.mkdir(reportPath)
        dirPath = os.getcwd()
        inLogPath = os.path.join(dirPath, 'Logs')

        inPlotPath = os.path.join(pathOut,'Plots')
        # The inPlotPath is going to be different for L1A-L1E than L2 for many cruises...
        # In that case, move up one directory
        if os.path.isdir(os.path.join(inPlotPath, 'L1AQC_Anoms')) is False:
            inPlotPath = os.path.join(pathOut,'..','Plots')

        outHDF = os.path.split(outFilePath)[1]
        if fail:
            outPDF = os.path.join(reportPath, f'{os.path.splitext(outHDF)[0]}_fail.pdf')
        else:
            outPDF = os.path.join(reportPath, f'{os.path.splitext(outHDF)[0]}.pdf')

        pdf = PDF()
        pdf.set_title(title)
        pdf.set_author(f'HyperInSPACE_{MainConfig.settings["version"]}')

        inLog = os.path.join(inLogPath,f'{fileName}_L1A.log')
        if os.path.isfile(inLog):
            print('Level 1A')
            pdf.print_chapter('L1A', 'Process RAW to L1A', inLog, inPlotPath, fileName, outFilePath, root)

        if numLevel > 1:
            print('Level 1AQC')
            inLog = os.path.join(inLogPath,f'{fileName}_L1A_L1AQC.log')
            if os.path.isfile(inLog):
                pdf.print_chapter('L1AQC', 'Process L1A to L1AQC', inLog, inPlotPath, fileName, outFilePath, root)

        if numLevel > 2:
            print('Level 1B')
            inLog = os.path.join(inLogPath,f'{fileName}_L1AQC_L1B.log')
            if os.path.isfile(inLog):
                pdf.print_chapter('L1B', 'Process L1AQC to L1B', inLog, inPlotPath, fileName, outFilePath, root)

        if numLevel > 3:
            print('Level 1BQC')
            inLog = os.path.join(inLogPath,f'{fileName}_L1B_L1BQC.log')
            if os.path.isfile(inLog):
                pdf.print_chapter('L1BQC', 'Process L1B to L1BQC', inLog, inPlotPath, fileName, outFilePath, root)

        if numLevel > 4:
            print('Level 2')
            # For L2, reset Plot directory
            inPlotPath = os.path.join(pathOut,'Plots')
            if 'STATION' in outFilePath:
                inLog = os.path.join(inLogPath,f'Stations_{fileName}_L1BQC_L2.log')
            else:
                inLog = os.path.join(inLogPath,f'{fileName}_L1BQC_L2.log')
            if os.path.isfile(inLog):
                pdf.print_chapter('L2', 'Process L1BQC to L2', inLog, inPlotPath, fileName, outFilePath, root)

        try:
            pdf.output(outPDF, 'F')
        except:
            msg = 'Unable to write the PDF file. It may be open in another program.'
            Utilities.errorWindow("File Error", msg)
            print(msg)
            Utilities.writeLogFile(msg)

    @staticmethod
    def generateContext(calibrationMap):
        ''' Generate a calibration context map for the instrument suite '''

        for key in calibrationMap:
            cf = calibrationMap[key]
            cf.printd()
            # Satlantic HyperSAS-specific definitions
            if cf.id.startswith("SATHED"):
                cf.instrumentType = "Reference"
                cf.media = "Air"
                cf.measMode = "Surface"
                cf.frameType = "ShutterDark"
                cf.sensorType = cf.getSensorType()
            elif cf.id.startswith("SATHSE"):
                cf.instrumentType = "Reference"
                cf.media = "Air"
                cf.measMode = "Surface"
                cf.frameType = "ShutterLight"
                cf.sensorType = cf.getSensorType()
            elif cf.id.startswith("SATHLD"):
                cf.instrumentType = "SAS"
                cf.media = "Air"
                cf.measMode = "VesselBorne"
                cf.frameType = "ShutterDark"
                cf.sensorType = cf.getSensorType()
            elif cf.id.startswith("SATHSL"):
                cf.instrumentType = "SAS"
                cf.media = "Air"
                cf.measMode = "VesselBorne"
                cf.frameType = "ShutterLight"
                cf.sensorType = cf.getSensorType()
            elif cf.id.startswith("$GPRMC") or cf.id.startswith("$GPGGA"):
                cf.instrumentType = "GPS"
                cf.media = "Not Required"
                cf.measMode = "Not Required"
                cf.frameType = "Not Required"
                cf.sensorType = cf.getSensorType()
            elif cf.id.startswith("SATPYR"):
                cf.instrumentType = "SATPYR"
                cf.media = "Not Required"
                cf.measMode = "Not Required"
                cf.frameType = "Not Required"
                cf.sensorType = cf.getSensorType()
            elif cf.id.startswith("SATTHS"):
                cf.instrumentType = "SATTHS"
                cf.media = "Not Required"
                cf.measMode = "Not Required"
                cf.frameType = "Not Required"
                cf.sensorType = cf.getSensorType()
            else:
                cf.instrumentType = "SAS"
                cf.media = "Air"
                cf.measMode = "VesselBorne"
                cf.frameType = "LightAncCombined"
                cf.sensorType = cf.getSensorType()

    @staticmethod
    def processCalibrationConfig(configName, calFiles):
        ''' Read in calibration files/configuration '''

        # print("processCalibrationConfig")
        calFolder = os.path.splitext(configName)[0] + "_Calibration"
        calPath = os.path.join("Config", calFolder)
        print("Read CalibrationFile ", calPath)
        calibrationMap = CalibrationFileReader.read(calPath)
        Controller.generateContext(calibrationMap)

        # Settings from Config file
        print("Apply ConfigFile settings")
        print("calibrationMap keys:", calibrationMap.keys())
        # print("config keys:", calFiles.keys())

        for key in list(calibrationMap.keys()):
            # print(key)
            if key in calFiles.keys():
                if calFiles[key]["enabled"]:
                    calibrationMap[key].frameType = calFiles[key]["frameType"]
                else:
                    del calibrationMap[key]
            else:
                del calibrationMap[key]
        return calibrationMap

    @staticmethod
    def processAncData(fp):
        ''' Read in the ancillary field data file '''

        if fp is None or fp=='':
            return None
        elif not os.path.isfile(fp):
            print("Specified ancillary file not found: " + fp)
            return None
        ancillaryData = AncillaryReader.readAncillary(fp)
        return ancillaryData

    @staticmethod
    def processL1a(inFilePath, outFilePath, calibrationMap):
        root = None
        if not os.path.isfile(inFilePath):
            msg = 'No such file...'
            Utilities.errorWindow("File Error", msg)
            print(msg)
            Utilities.writeLogFile(msg)
            return None, 'Never'

        # Process the data
        msg = "ProcessL1a"
        print(msg)
        root = ProcessL1a.processL1a(inFilePath, calibrationMap)

        # Write output file
        if root is not None:
            try:
                root.writeHDF5(outFilePath)
            except:
                msg = 'Unable to write L1A file. It may be open in another program.'
                Utilities.errorWindow("File Error", msg)
                print(msg)
                Utilities.writeLogFile(msg)
                return None
        else:
            msg = "L1a processing failed. Nothing to output."
            if MainConfig.settings["popQuery"] == 0 and os.getenv('HYPERINSPACE_CMD') != 'TRUE':
                Utilities.errorWindow("File Error", msg)
            print(msg)
            Utilities.writeLogFile(msg)
            return None

        return root

    @staticmethod
    def processL1aqc(inFilePath, outFilePath, calibrationMap, ancillaryData):
        root = None
        if not os.path.isfile(inFilePath):
            print('No such input file: ' + inFilePath)
            return None

        # Process the data
        print("ProcessL1aqc")
        try:
            root = HDFRoot.readHDF5(inFilePath)
        except:
            msg = "Unable to open file. May be open in another application."
            Utilities.errorWindow("File Error", msg)
            print(msg)
            Utilities.writeLogFile(msg)
            return None

        # At this stage the Anomanal parameterizations are current in ConfigFile.settings,
        #   regardless of who called this method.  This method will promote them to root.attributes.
        root = ProcessL1aqc.processL1aqc(root, calibrationMap, ancillaryData)

        # Write output file
        if root is not None:
            try:
                root.writeHDF5(outFilePath)
            except:
                msg = "Unable to write the file. May be open in another application."
                Utilities.errorWindow("File Error", msg)
                print(msg)
                Utilities.writeLogFile(msg)
                return None
        else:
            msg = "L1aqc processing failed. Nothing to output."
            if MainConfig.settings["popQuery"] == 0 and os.getenv('HYPERINSPACE_CMD') != 'TRUE':
                Utilities.errorWindow("File Error", msg)
            print(msg)
            Utilities.writeLogFile(msg)
            return None

        return root

    @staticmethod
    def processL1b(inFilePath, outFilePath):
        root = None
        if not os.path.isfile(inFilePath):
            print('No such input file: ' + inFilePath)
            return None

        # Process the data
        msg = ("ProcessL1b: " + inFilePath)
        print(msg)
        Utilities.writeLogFile(msg)
        try:
            root = HDFRoot.readHDF5(inFilePath)
        except:
            msg = "Controller.processL1b: Unable to open HDF file. May be open in another application."
            Utilities.errorWindow("File Error", msg)
            print(msg)
            Utilities.writeLogFile(msg)
            return None


        root = ProcessL1b.processL1b(root, outFilePath)

        # Write output file
        if root is not None:
            try:
                root.writeHDF5(outFilePath)
            except:
                msg = "Controller.ProcessL1b: Unable to write file. May be open in another application."
                Utilities.errorWindow("File Error", msg)
                print(msg)
                Utilities.writeLogFile(msg)
                return None
        else:
            msg = "L1b processing failed. Nothing to output."
            if MainConfig.settings["popQuery"] == 0:
                Utilities.errorWindow("File Error", msg)
            print(msg)
            Utilities.writeLogFile(msg)
            return None

        return root

    @staticmethod
    def processL1bqc(inFilePath, outFilePath):
        root = None

        if not os.path.isfile(inFilePath):
            print('No such input file: ' + inFilePath)
            return None

        # Process the data
        print("ProcessL1bqc")
        try:
            root = HDFRoot.readHDF5(inFilePath)
        except:
            msg = "Unable to open file. May be open in another application."
            Utilities.errorWindow("File Error", msg)
            print(msg)
            Utilities.writeLogFile(msg)
            return None

        root.attributes['In_Filepath'] = inFilePath
        root = ProcessL1bqc.processL1bqc(root)

        # Write output file
        if root is not None:
            try:
                root.writeHDF5(outFilePath)
            except:
                msg = "Unable to write file. May be open in another application."
                Utilities.errorWindow("File Error", msg)
                print(msg)
                Utilities.writeLogFile(msg)
                return None,
        else:
            msg = "L1bqc processing failed. Nothing to output."
            if MainConfig.settings["popQuery"] == 0 and os.getenv('HYPERINSPACE_CMD') != 'TRUE':
                Utilities.errorWindow("File Error", msg)
            print(msg)
            Utilities.writeLogFile(msg)
            return None

        return root


    @staticmethod
    def processL2(root,outFilePath,station=None):

        node = ProcessL2.processL2(root,station)

        _, filename = os.path.split(outFilePath)
        if node is not None:

            # Create Plots
            # Radiometry
            if ConfigFile.settings['bL2PlotRrs']==1:
                Utilities.plotRadiometry(node, filename, rType='Rrs', plotDelta = True)
            if ConfigFile.settings['bL2PlotnLw']==1:
                Utilities.plotRadiometry(node, filename, rType='nLw', plotDelta = True)
            if ConfigFile.settings['bL2PlotEs']==1:
                Utilities.plotRadiometry(node, filename, rType='ES', plotDelta = True)
            if ConfigFile.settings['bL2PlotLi']==1:
                Utilities.plotRadiometry(node, filename, rType='LI', plotDelta = True)
            if ConfigFile.settings['bL2PlotLt']==1:
                Utilities.plotRadiometry(node, filename, rType='LT', plotDelta = True)

            # IOPs
            # These three should plot GIOP and QAA together (eventually, once GIOP is complete)
            if ConfigFile.products["bL2ProdadgQaa"]:
                Utilities.plotIOPs(node, filename, algorithm = 'qaa', iopType='adg', plotDelta = False)
            if ConfigFile.products["bL2ProdaphQaa"]:
                Utilities.plotIOPs(node, filename, algorithm = 'qaa', iopType='aph', plotDelta = False)
            if ConfigFile.products["bL2ProdbbpQaa"]:
                Utilities.plotIOPs(node, filename, algorithm = 'qaa', iopType='bbp', plotDelta = False)

            # This puts ag, Sg, and DOC on the same plot
            if ConfigFile.products["bL2Prodgocad"] and ConfigFile.products["bL2ProdSg"] \
                 and ConfigFile.products["bL2Prodag"] and ConfigFile.products["bL2ProdDOC"]:
                Utilities.plotIOPs(node, filename, algorithm = 'gocad', iopType='ag', plotDelta = False)

        # Write output file
        if node is not None:
            try:
                node.writeHDF5(outFilePath)
                return node
            except:
                msg = "Unable to write file. May be open in another application."
                Utilities.errorWindow("File Error", msg)
                print(msg)
                Utilities.writeLogFile(msg)
                return None
        else:
            msg = "L2 processing failed. Nothing to output."
            if MainConfig.settings["popQuery"] == 0:
                Utilities.errorWindow("File Error", msg)
            print(msg)
            Utilities.writeLogFile(msg)
            return None

    # Process every file in a list of files 1 level
    @staticmethod
    # def processSingleLevel(pathOut, inFilePath, calibrationMap, level, ancFile=None):
    def processSingleLevel(pathOut, inFilePath, calibrationMap, level):
        # Find the absolute path to the output directory
        pathOut = os.path.abspath(pathOut)
        # inFilePath is a singleton file complete with path
        inFilePath = os.path.abspath(inFilePath)
        # (inpath, inFileName) = os.path.split(inFilePath)
        inFileName = os.path.split(inFilePath)[1]
        # Grab input name and extension
        fileName,extension = os.path.splitext(inFileName)#[0]

        # Initialize the Utility logger, overwriting it if necessary
        if ConfigFile.settings["bL2Stations"] == 1 and level == 'L2':
            os.environ["LOGFILE"] = f'Stations_{fileName}_{level}.log'
        else:
            os.environ["LOGFILE"] = (fileName + '_' + level + '.log')
        msg = "Process Single Level"
        print(msg)
        Utilities.writeLogFile(msg,mode='w') # <<---- Logging initiated here

        # If this is an HDF, assume it is not RAW, drop the level from fileName
        if extension=='.hdf':
            fileName = fileName.rsplit('_',1)[0]

        # Check for base output directory
        if os.path.isdir(pathOut):
            pathOutLevel = os.path.join(pathOut,level)
        else:
            msg = "Bad output destination. Select new Output Data Directory."
            print(msg)
            Utilities.writeLogFile(msg)
            return False

        # Add output level directory if necessary
        if os.path.isdir(pathOutLevel) is False:
            os.mkdir(pathOutLevel)

        outFilePath = os.path.join(pathOutLevel,fileName + "_" + level + ".hdf")

        if level == "L1A" or level == "L1AQC" or level == "L1B" or level == "L1BQC":

            if level == "L1A":
                root = Controller.processL1a(inFilePath, outFilePath, calibrationMap)

            elif level == "L1AQC":
                ancillaryData = Controller.processAncData(MainConfig.settings["metFile"])
                # If called locally from Controller and not AnomalyDetection.py, then
                #   try to load the parameter file for this cruise/configuration and update
                #   ConfigFile.settings to reflect the appropriate parameterizations for this
                #   particular file. If no parameter file exists, or this SAS file is not in it,
                #   then fall back on the default ConfigFile.settings.

                if ConfigFile.settings["bL1aqcDeglitch"]:
                    anomAnalFileName = os.path.splitext(ConfigFile.filename)[0]
                    anomAnalFileName = anomAnalFileName + '_anoms.csv'
                    fp = os.path.join('Config',anomAnalFileName)
                    if os.path.exists(fp):
                        msg = f"Deglitching file {fp} found for {ConfigFile.filename.split('.')[0]}. Using these parameters."
                        print(msg)
                        Utilities.writeLogFile(msg)
                        params = Utilities.readAnomAnalFile(fp)
                        # If a parameterization has been saved in the AnomAnalFile, set the properties in the local object
                        # for all sensors
                        l1aqcfileName = fileName + '_L1AQC'
                        if l1aqcfileName in params.keys():
                            ref = 0
                            for sensor in ['ES','LI','LT']:
                                print(f'{sensor}: Setting ConfigFile.settings to match saved parameterization. ')
                                ConfigFile.settings[f'fL1aqc{sensor}WindowDark'] = params[l1aqcfileName][ref+0]
                                ConfigFile.settings[f'fL1aqc{sensor}WindowLight'] = params[l1aqcfileName][ref+1]
                                ConfigFile.settings[f'fL1aqc{sensor}SigmaDark'] = params[l1aqcfileName][ref+2]
                                ConfigFile.settings[f'fL1aqc{sensor}SigmaLight'] = params[l1aqcfileName][ref+3]
                                ConfigFile.settings[f'fL1aqc{sensor}MinDark'] = params[l1aqcfileName][ref+4]
                                ConfigFile.settings[f'fL1aqc{sensor}MaxDark'] = params[l1aqcfileName][ref+5]
                                ConfigFile.settings[f'fL1aqc{sensor}MinMaxBandDark'] = params[l1aqcfileName][ref+6]
                                ConfigFile.settings[f'fL1aqc{sensor}MinLight'] = params[l1aqcfileName][ref+7]
                                ConfigFile.settings[f'fL1aqc{sensor}MaxLight'] = params[l1aqcfileName][ref+8]
                                ConfigFile.settings[f'fL1aqc{sensor}MinMaxBandLight'] = params[l1aqcfileName][ref+9]
                                ref += 10
                        else:
                            msg = 'This file not found in parameter file. Resorting to values in ConfigFile.settings.'
                            print(msg)
                            Utilities.writeLogFile(msg)
                    else:
                        msg = 'No deglitching parameter file found. Resorting to default values. NOT RECOMMENDED. RUN ANOMALY ANALYSIS.'
                        print(msg)
                        Utilities.writeLogFile(msg)
                else:
                    msg = 'No deglitching will be performed.'
                    print(msg)
                    Utilities.writeLogFile(msg)
                root = Controller.processL1aqc(inFilePath, outFilePath, calibrationMap, ancillaryData)

            elif level == "L1B":
                root = Controller.processL1b(inFilePath, outFilePath)

            elif level == "L1BQC":
                root = Controller.processL1bqc(inFilePath, outFilePath)

            # Confirm output file creation
            if os.path.isfile(outFilePath):
                modTime = os.path.getmtime(outFilePath)
                nowTime = datetime.datetime.now()
                if nowTime.timestamp() - modTime < 60: # If the file exists and was created in the last minute...
                    msg = f'{level} file produced: \n {outFilePath}'
                    print(msg)
                    Utilities.writeLogFile(msg)

        elif level == "L2":
            # Ancillary data from metadata have been read in at L1C,
            # and will be extracted from the ANCILLARY_METADATA group later

            root = None
            if not os.path.isfile(inFilePath):
                print('No such input file: ' + inFilePath)
                return None, outFilePath

            msg = ("ProcessL2: " + inFilePath)
            print(msg)
            Utilities.writeLogFile(msg)
            try:
                # root variable is replaced by L2 node unless station extraction, in which case
                #   it is retained and node is returned from ProcessL2
                root = HDFRoot.readHDF5(inFilePath)
            except:
                msg = "Unable to open file. May be open in another application."
                Utilities.errorWindow("File Error", msg)
                print(msg)
                Utilities.writeLogFile(msg)
                return None, outFilePath

            ##### Loop over this whole section for each station in the file where appropriate ####
            if ConfigFile.settings["bL2Stations"]:
                ancGroup = root.getGroup("ANCILLARY")
                for ds in ancGroup.datasets:
                    try:
                        ancGroup.datasets[ds].datasetToColumns()
                    except:
                        print('Error: Something wrong with root ANCILLARY')
                stations = np.array(root.getGroup("ANCILLARY").getDataset("STATION").columns["STATION"])
                stations = np.unique(stations[~np.isnan(stations)]).tolist()

                if len(stations) > 0:

                    for station in stations:
                        stationStr = str( round(station*100)/100 )
                        stationStr = stationStr.replace('.','_')
                        # Current SeaBASS convention experiment_cruise_measurement_datetime_Revision#.sb
                        # For HDF, leave off measurement; add at SeaBASS writer
                        outPath, filename = os.path.split(outFilePath)
                        filename,ext = filename.split('.')
                        filename = f'{filename}_STATION_{stationStr}.hdf'
                        outFilePathStation = os.path.join(outPath,filename)

                        msg = f'Processing station: {stationStr}: \n'
                        print(msg)
                        Utilities.writeLogFile(msg)

                        node = Controller.processL2(root, outFilePathStation,station)

                        if os.path.isfile(outFilePathStation):
                            # Ensure that the L2 on file is recent before continuing with
                            # SeaBASS files or reports
                            modTime = os.path.getmtime(outFilePathStation)
                            nowTime = datetime.datetime.now()
                            if nowTime.timestamp() - modTime < 60:
                                msg = f'{level} file produced: \n{outFilePathStation}'
                                print(msg)
                                Utilities.writeLogFile(msg)

                                # Write SeaBASS
                                if int(ConfigFile.settings["bL2SaveSeaBASS"]) == 1:
                                    msg = f'Output SeaBASS for HDF: \n{outFilePathStation}'
                                    print(msg)
                                    Utilities.writeLogFile(msg)
                                    SeaBASSWriter.outputTXT_Type2(outFilePathStation)
                                # return True

                        # Write L2 report for each station, regardless of pass/fail
                        if ConfigFile.settings["bL2WriteReport"] == 1:
                            Controller.writeReport(fileName, pathOut, outFilePathStation, level, inFilePath)
                else:
                    msg = f'No stations found in: {fileName}'
                    print(msg)
                    Utilities.writeLogFile(msg)

            else:
                # Even where not extracting stations, processL2 returns node, not root, but to comply with expectations
                # below based on the other levels and PDF reporting, overwrite root with node
                root = Controller.processL2(root,outFilePath)

                if os.path.isfile(outFilePath):
                    # Ensure that the L2 on file is recent before continuing with
                    # SeaBASS files or reports
                    modTime = os.path.getmtime(outFilePath)
                    nowTime = datetime.datetime.now()
                    if nowTime.timestamp() - modTime < 60:
                        msg = f'{level} file produced: \n{outFilePath}'
                        print(msg)
                        Utilities.writeLogFile(msg)

                        # Write SeaBASS
                        if int(ConfigFile.settings["bL2SaveSeaBASS"]) == 1:
                            msg = f'Output SeaBASS for HDF: \n{outFilePath}'
                            print(msg)
                            Utilities.writeLogFile(msg)
                            SeaBASSWriter.outputTXT_Type2(outFilePath)

        # If the process failed at any level, write a report and return
        if root is None and ConfigFile.settings["bL2Stations"] == 0:
            if ConfigFile.settings["bL2WriteReport"] == 1:
                Controller.writeReport(fileName, pathOut, outFilePath, level, inFilePath)
            return False

        # If L2 successful and not station extraction, write a report
        if level == "L2" and ConfigFile.settings["bL2Stations"] == 0:
            if ConfigFile.settings["bL2WriteReport"] == 1:
                Controller.writeReport(fileName, pathOut, outFilePath, level, inFilePath)

        msg = f'Process Single Level: {outFilePath} - SUCCESSFUL'
        print(msg)
        Utilities.writeLogFile(msg)

        return True


    # Process every file in a list of files from L0 to L2
    @staticmethod
    def processFilesMultiLevel(pathOut,inFiles, calibrationMap, ancFile=None):
        print("processFilesMultiLevel")
        # t0 = time.time()
        for fp in inFiles:
            print("Processing: " + fp)

            # if Controller.processSingleLevel(pathOut, fp, calibrationMap, 'L1A', ancFile):
            if Controller.processSingleLevel(pathOut, fp, calibrationMap, 'L1A'):
                # Going from L0 to L1A, need to account for the underscore
                inFileName = os.path.split(fp)[1]
                fileName = os.path.join('L1A',f'{os.path.splitext(inFileName)[0]}'+'_L1A.hdf')
                fp = os.path.join(os.path.abspath(pathOut),fileName)
                # if Controller.processSingleLevel(pathOut, fp, calibrationMap, 'L1AQC', ancFile):
                if Controller.processSingleLevel(pathOut, fp, calibrationMap, 'L1AQC'):
                    inFileName = os.path.split(fp)[1]
                    fileName = os.path.join('L1AQC',f"{os.path.splitext(inFileName)[0].rsplit('_',1)[0]}"+'_L1AQC.hdf')
                    fp = os.path.join(os.path.abspath(pathOut),fileName)
                    # if Controller.processSingleLevel(pathOut, fp, calibrationMap, 'L1B', ancFile):
                    if Controller.processSingleLevel(pathOut, fp, calibrationMap, 'L1B'):
                        inFileName = os.path.split(fp)[1]
                        fileName = os.path.join('L1B',f"{os.path.splitext(inFileName)[0].rsplit('_',1)[0]}"+'_L1B.hdf')
                        fp = os.path.join(os.path.abspath(pathOut),fileName)
                        # if Controller.processSingleLevel(pathOut, fp, calibrationMap, 'L1BQC', ancFile):
                        if Controller.processSingleLevel(pathOut, fp, calibrationMap, 'L1BQC'):
                            inFileName = os.path.split(fp)[1]
                            fileName = os.path.join('L1BQC',f"{os.path.splitext(inFileName)[0].rsplit('_',1)[0]}"+'_L1BQC.hdf')
                            fp = os.path.join(os.path.abspath(pathOut),fileName)
                            # Controller.processSingleLevel(pathOut, fp, calibrationMap, 'L2', ancFile)
                            Controller.processSingleLevel(pathOut, fp, calibrationMap, 'L2')
        print("processFilesMultiLevel - DONE")
        # t1 = time.time()
        # print(f'Elapsed time: {(t1-t0)/60} minutes')


    # Process every file in a list of files 1 level
    @staticmethod
    def processFilesSingleLevel(pathOut, inFiles, calibrationMap, level, ancFile=None):
        # print("processFilesSingleLevel")
        for fp in inFiles:
            # Check that the input file matches what is expected for this processing level
            # Not case sensitive
            fileName = str.lower(os.path.split(fp)[1])
            if level == "L1A":
                srchStr = 'RAW'
            elif level == 'L1AQC':
                srchStr = 'L1A'
            elif level == 'L1B':
                srchStr = 'L1AQC'
            elif level == 'L1BQC':
                srchStr = 'L1B'
            elif level == 'L2':
                srchStr = 'L1BQC'
            if fileName.find(str.lower(srchStr)) == -1:
                msg = f'{fileName} does not match expected input level for outputing {level}'
                print(msg)
                Utilities.writeLogFile(msg)
                return -1

            print("Processing: " + fp)
            # try:
            # Controller.processSingleLevel(pathOut, fp, calibrationMap, level, ancFile)
            Controller.processSingleLevel(pathOut, fp, calibrationMap, level)
            # except OSError:
            #     print("Unable to process that file due to an operating system error. Try again.")
        print("processFilesSingleLevel - DONE")
