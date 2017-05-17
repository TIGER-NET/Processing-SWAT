"""
***************************************************************************
   MDWF_GenModelClimateData.py
-------------------------------------
    Copyright (C) 2014 TIGER-NET (www.tiger-net.org)

***************************************************************************
* This plugin is part of the Water Observation Information System (WOIS)  *
* developed under the TIGER-NET project funded by the European Space      *
* Agency as part of the long-term TIGER initiative aiming at promoting    *
* the use of Earth Observation (EO) for improved Integrated Water         *
* Resources Management (IWRM) in Africa.                                  *
*                                                                         *
* WOIS is a free software i.e. you can redistribute it and/or modify      *
* it under the terms of the GNU General Public License as published       *
* by the Free Software Foundation, either version 3 of the License,       *
* or (at your option) any later version.                                  *
*                                                                         *
* WOIS is distributed in the hope that it will be useful, but WITHOUT ANY * 
* WARRANTY; without even the implied warranty of MERCHANTABILITY or       *
* FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License   *
* for more details.                                                       *
*                                                                         *
* You should have received a copy of the GNU General Public License along *
* with this program.  If not, see <http://www.gnu.org/licenses/>.         *
***************************************************************************
"""

import os
from datetime import date, timedelta, datetime
import numpy
from PyQt4 import QtGui
from processing.core.GeoAlgorithmExecutionException import GeoAlgorithmExecutionException
from processing.core.parameters import *
from SWATAlgorithm import SWATAlgorithm
from ModelFile import ModelFile
from ClimateStationsSWAT import ClimateStationsSWAT
from ZonalStats import ZonalStats

class MDWF_GenModelClimateData(SWATAlgorithm):

    MODEL_FILE = "MODEL_FILE"
    PCP_DST_FOLDER = "PCP_DST_FOLDER"
    TMAX_DST_FOLDER = "TMAX_DST_FOLDER"
    TMIN_DST_FOLDER = "TMIN_DST_FOLDER"
    SUBCATCH_RES = 'SUBCATCH_RES'

    def __init__(self):
        super(MDWF_GenModelClimateData, self).__init__(__file__)

    def defineCharacteristics(self):
        self.name = "3 - Generate model climate data (MDWF)"
        self.group = "Model development workflow (MDWF)"
        self.addParameter(ParameterFile(MDWF_GenModelClimateData.MODEL_FILE, "Model description file", False, False))
        self.addParameter(ParameterFile(MDWF_GenModelClimateData.PCP_DST_FOLDER, "Precipitation folder", True, False))
        self.addParameter(ParameterFile(MDWF_GenModelClimateData.TMAX_DST_FOLDER, "Maximum temperature folder", True, False))
        self.addParameter(ParameterFile(MDWF_GenModelClimateData.TMIN_DST_FOLDER, "Minimum temperature folder", True, False))
        self.addParameter(ParameterNumber(MDWF_GenModelClimateData.SUBCATCH_RES, "Resolution of subcatchment map", 0.001, 0.5, 0.01))

    def processAlgorithm(self, progress):
        progress.setConsoleInfo("Loading model and data files...")
        # Get inputs
        model_file = str(self.getParameterValue(MDWF_GenModelClimateData.MODEL_FILE))
        pcp_folder = str(self.getParameterValue(MDWF_GenModelClimateData.PCP_DST_FOLDER))
        tmax_folder = str(self.getParameterValue(MDWF_GenModelClimateData.TMAX_DST_FOLDER))
        tmin_folder = str(self.getParameterValue(MDWF_GenModelClimateData.TMIN_DST_FOLDER))
        subcatchmap_res = float(self.getParameterValue(MDWF_GenModelClimateData.SUBCATCH_RES))

        # Check inputs
        for folder in [pcp_folder, tmax_folder, tmin_folder]:
            if not os.path.isdir(folder):
                raise GeoAlgorithmExecutionException('No such directory: \"' + folder + '\" ')
        if not os.path.isfile(model_file):
            raise GeoAlgorithmExecutionException('No such file: \"' + model_file + '\" ')

        # Load model
        model = ModelFile(model_file)

        # Create log file
        log_file = open(model.Path + os.sep + "log.txt", "w")
        # Write current date to log file
        now = date.today()
        log_file.write(self.name + ' run date: ' + now.strftime('%Y%m%d') + '\n')

        # Load SWAT stations file
        stations = ClimateStationsSWAT(model.Path + os.sep + model.desc['Stations'])

        progress.setConsoleInfo("Reading old climate data...")
        # Getting SWAT .pcp data
        pcp_juliandates, first_pcp_date, last_pcp_date, pcp_array = stations.readSWATpcpFiles(log_file)
##        numpy.savetxt(model.Path + os.sep + 'pcp_array.csv', pcp_array, delimiter=",")
##        log_file.write(str(pcp_dates))

        # Getting SWAT .tmp data
        tmp_juliandates, first_tmp_date, last_tmp_date, tmp_max_array, tmp_min_array = stations.readSWATtmpFiles(log_file)
##        numpy.savetxt(model.Path + os.sep + 'tmp_max_array.csv', tmp_max_array, delimiter=",")

        # Delete last forecast in .pcp and .tmp data if Real Time model
        if model.desc['Type'] == 'RT':
            # Read last forecast dates from file
            forecast_dates_file = model.Path + os.sep + model.desc['ForecastDateFile']
            forecast_dates = {}
            forecast_file=open(forecast_dates_file,'r').readlines()
            if not forecast_file[0].find('Forecast dates file') == -1:
                for line in range(1,len(forecast_file)):
                    (key, val) = forecast_file[line].split()
                    forecast_dates[key] = val

                # setting new last_dates and crop arrays
                # APCP
                new_last_pcp_date = datetime.strptime(forecast_dates['APCP'], "%Y%m%d").date() - timedelta(days=1)
                dif = (last_pcp_date - new_last_pcp_date).days
                if dif > 0:
                    pcp_array = pcp_array[:-dif,:]
                    pcp_juliandates = pcp_juliandates[:-dif]
                    last_pcp_date = new_last_pcp_date
                # TMP
                new_last_tmp_date = datetime.strptime(forecast_dates['TMP'], "%Y%m%d").date() - timedelta(days=1)
                dif = (last_tmp_date - new_last_tmp_date).days
                if dif > 0:
                    tmp_max_array = tmp_max_array[:-dif,:]
                    tmp_min_array = tmp_min_array[:-dif,:]
                    tmp_juliandates = tmp_juliandates[:-dif]
                    last_tmp_date = new_last_tmp_date


        progress.setConsoleInfo("Searching for new files...")
        # Getting list of new pcp data files
        new_pcp_files = []
        new_pcp_enddate = last_pcp_date
        dirs = os.listdir(pcp_folder)
        if model.desc['Type'] == 'RT':
            pcp_forecast_var = 'APCP_Forecast_'
        else:
            pcp_forecast_var = 'none'
        pcp_var_GFS = 'APCP.tif'
        pcp_var_RFE = '_rain_.tif'
        pcp_var_TRMM = '_TRMM3B42.tif'
        for f in dirs:
            if ((pcp_var_GFS in f) or (pcp_var_RFE in f) or (pcp_var_TRMM in f)):
                file_date = datetime.strptime(f[0:8], "%Y%m%d").date()
                # Only get new files
                if (last_pcp_date < file_date):
                    new_pcp_files.append(pcp_folder + os.sep + f)
                    # Find the last date
                    if new_pcp_enddate < file_date:
                        new_pcp_enddate = file_date
            # Append forecast files for real-time
            elif (pcp_forecast_var in f) and (model.desc['Type'] == 'RT'):
                file_date = datetime.strptime(f[0:8], "%Y%m%d").date()
                # Only get new files
                if (last_pcp_date < file_date):
                    new_pcp_files.append(pcp_folder + os.sep + f)
                    # Find the last date
                    if new_pcp_enddate < file_date:
                        new_pcp_enddate = file_date
                    new_pcp_forecast_date = f.split(pcp_forecast_var)[1].split('.tif')[0]

        # Getting list of new tmax data files
        new_tmax_files = []
        new_tmax_enddate = last_tmp_date
        tmax_var_GFS = 'TMAX.tif'
        tmax_var_ECMWF = '_TMAX_ECMWF.tif'
        tmax_forecast_var = 'TMAX_Forecast_'
        dirs = os.listdir(tmax_folder)
        for f in dirs:
            if (tmax_var_GFS in f) or (tmax_var_ECMWF in f):
                file_date = datetime.strptime(f[0:8], "%Y%m%d").date()
                # Only get new files
                if (last_tmp_date < file_date):
                    new_tmax_files.append(tmax_folder + os.sep + f)
                    # Find the last date
                    if new_tmax_enddate < file_date:
                        new_tmax_enddate = file_date
            # Append forecast files for real-time
            elif (tmax_forecast_var in f) and (model.desc['Type'] == 'RT'):
                file_date = datetime.strptime(f[0:8], "%Y%m%d").date()
                # Only get new files
                if (last_tmp_date < file_date):
                    new_tmax_files.append(tmax_folder + os.sep + f)
                    # Find the last date
                    if new_tmax_enddate < file_date:
                        new_tmax_enddate = file_date
                    new_tmax_forecast_date = f.split(tmax_forecast_var)[1].split('.tif')[0]

        # Getting list of new tmin data files
        new_tmin_files = []
        new_tmin_enddate = last_tmp_date
        tmin_var_GFS = 'TMIN.tif'
        tmin_var_ECMWF = '_TMIN_ECMWF.tif'
        tmin_forecast_var = 'TMIN_Forecast_'
        dirs = os.listdir(tmin_folder)
        for f in dirs:
            if (tmin_var_GFS in f) or (tmin_var_ECMWF in f):
                file_date = datetime.strptime(f[0:8], "%Y%m%d").date()
                # Only get new files
                if (last_tmp_date < file_date):
                    new_tmin_files.append(tmin_folder + os.sep + f)
                    # Find the last date
                    if new_tmin_enddate < file_date:
                        new_tmin_enddate = file_date
            # Append forecast files for real-time
            elif (tmin_forecast_var in f) and (model.desc['Type'] == 'RT'):
                file_date = datetime.strptime(f[0:8], "%Y%m%d").date()
                # Only get new files
                if (last_tmp_date < file_date):
                    new_tmin_files.append(tmin_folder + os.sep + f)
                    # Find the last date
                    if new_tmin_enddate < file_date:
                        new_tmin_enddate = file_date
                    new_tmin_forecast_date = f.split(tmin_forecast_var)[1].split('.tif')[0]

##        log_file.write('APCP files: ' + str(new_pcp_files) + '\n')
##        log_file.write('TMAX files: ' + str(new_tmax_files) + '\n')
##        log_file.write('TMIN files: ' + str(new_tmin_files) + '\n')

        progress.setConsoleInfo("Extracting precipitation data...")
        # Process new APCP files
        if not new_pcp_files == []:
            try:
                correct_factor = float(model.desc['PcpCorrFact'])
            except:
                correct_factor = None
            # Get new array
            pcp_startdate = last_pcp_date + timedelta(days=1)
            new_pcp_juliandates, new_pcp_array = ZonalStats(pcp_startdate, new_pcp_enddate, model.Path, \
                model.desc['ModelName'], model.Path+os.sep+model.desc['Shapefile'], model.desc['SubbasinColumn'], \
                subcatchmap_res, new_pcp_files, log_file, GeoAlgorithmExecutionException, None, correct_factor)
            # Combine arrays
            pcp_juliandates = numpy.concatenate((pcp_juliandates, new_pcp_juliandates), axis=0)
            pcp_array = numpy.concatenate((pcp_array, new_pcp_array), axis=0)
            progress.setConsoleInfo("Writing new precipitation files...")
            # Write files
            stations.writeSWATpcpFiles(pcp_juliandates, pcp_array, log_file)

        progress.setConsoleInfo("Extracting temperature data...")
        # Process Temperature files
        if not (new_tmax_files == [] and new_tmin_files == []):
            # Get new array
            # TMAX
            # Get corrections
            if tmax_var_ECMWF in new_tmax_files[0]:
                correct_number = -273.15
                pass
            else:
                correct_number = None
            tmp_startdate = last_tmp_date + timedelta(days=1)
            new_tmax_juliandates, new_tmp_max_array = ZonalStats(tmp_startdate, new_tmax_enddate, model.Path, \
                model.desc['ModelName'], model.Path+os.sep+model.desc['Shapefile'], model.desc['SubbasinColumn'], \
                subcatchmap_res, new_tmax_files, log_file, GeoAlgorithmExecutionException, correct_number, None)
            # TMIN
            if tmin_var_ECMWF in new_tmin_files[0]:
                correct_number = -273.15
                pass
            else:
                correct_number = None
            new_tmin_juliandates, new_tmp_min_array = ZonalStats(tmp_startdate, new_tmin_enddate, model.Path, \
                model.desc['ModelName'], model.Path+os.sep+model.desc['Shapefile'], model.desc['SubbasinColumn'], \
                subcatchmap_res, new_tmin_files, log_file, GeoAlgorithmExecutionException, correct_number, None)

            # Make shure tmax and tmin have same end days
            dif = (len(new_tmax_juliandates)-len(new_tmin_juliandates))
            if dif > 0:
                new_tmp_max_array = new_tmp_max_array[:-dif,:]
                new_tmax_juliandates = new_tmax_juliandates[:-dif]
                if model.desc['Type'] == 'RT':
                    new_tmp_forecast_date = new_tmin_forecast_date
            elif dif < 0:
                new_tmp_min_array = new_tmp_min_array[:-dif,:]
                new_tmin_juliandates = new_tmin_juliandates[:-dif,:]
                if model.desc['Type'] == 'RT':
                    new_tmp_forecast_date = new_tmax_forecast_date
            else:
                if model.desc['Type'] == 'RT':
                    new_tmp_forecast_date = new_tmax_forecast_date

            progress.setConsoleInfo("Writing new temperature files...")
            # Combine arrays
            # TMAX
            tmp_juliandates = numpy.concatenate((tmp_juliandates, new_tmax_juliandates), axis=0)
            tmp_max_array = numpy.concatenate((tmp_max_array, new_tmp_max_array), axis=0)
            # TMIN
            tmp_min_array = numpy.concatenate((tmp_min_array, new_tmp_min_array), axis=0)
            # Write files
            stations.writeSWATtmpFiles(tmp_juliandates, tmp_max_array, tmp_min_array, log_file)

            progress.setConsoleInfo("Update model files...")
            # Updating forecast file
            if model.desc['Type'] == 'RT':
                if new_pcp_files == []:
                    new_pcp_forecast_date = forecast_dates['APCP']
                forecast_file=open(forecast_dates_file,'w')
                forecast_file.write('Forecast dates file \n')
                forecast_file.write('APCP ' + new_pcp_forecast_date + '\n')
                forecast_file.write('TMP ' + new_tmp_forecast_date + '\n')

        log_file.close()
