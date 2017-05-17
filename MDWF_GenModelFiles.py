"""
***************************************************************************
   MDWF_GenModelFiles.py
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
import subprocess
from PyQt4 import QtGui
from processing.core.GeoAlgorithmExecutionException import GeoAlgorithmExecutionException
from processing.core.parameters import *
from SWATAlgorithm import SWATAlgorithm
from ModelFile import ModelFile
from processing.tools import dataobjects
from processing.algs.grass.GrassUtils import GrassUtils
from osgeo import gdal
from osgeo.gdalconst import *
import processing

class MDWF_GenModelFiles(SWATAlgorithm):

    MODEL_FILEPATH = "MODEL_FILEPATH"
    MODEL_FILE = "MODEL_FILE"
    MODEL_NAME = "MODEL_NAME"
    MODEL_TYPE = "MODEL_TYPE"
    MODEL_STARTDATE = "MODEL_STARTDATE"
    MODEL_SUBSHAPES = "MODEL_SUBSHAPES"
    MODEL_SUBCOLUMN = "MODEL_SUBCOLUMN"
    MODEL_CLIMSTATS = "MODEL_CLIMSTATS"
    MODEL_FCFILE = "MODEL_FCFILE"
    MODEL_PCPFAC = "MODEL_PCPFAC"
    MODEL_CENTROIDFILE ="MODEL_CENTROIDFILE"
    MODEL_LATCOLUMN ="MODEL_LATCOLUMN"
    MODEL_LONCOLUMN ="MODEL_LONCOLUMN"
    MODEL_ELEVCOLUMN ="MODEL_ELEVCOLUMN"

    def __init__(self):
        super(MDWF_GenModelFiles, self).__init__(__file__)

    def defineCharacteristics(self):
        self.name = "2 - Generate Model Description and climate files (MDWF)"
        self.group = "Model development workflow (MDWF)"
        self.addParameter(ParameterFile(MDWF_GenModelFiles.MODEL_FILEPATH, "Storage location for model description file", True, False))
        self.addParameter(ParameterString(MDWF_GenModelFiles.MODEL_FILE, "Name of the model description file",'model.txt'))
        self.addParameter(ParameterString(MDWF_GenModelFiles.MODEL_NAME, "Name of the model"))
        self.addParameter(ParameterSelection(MDWF_GenModelFiles.MODEL_TYPE, "Type of model", ['RT','Hist'], True))
        self.addParameter(ParameterString(MDWF_GenModelFiles.MODEL_STARTDATE, "Starting date of the model YYYYMMDD", '20000101'))
        self.addParameter(ParameterFile(MDWF_GenModelFiles.MODEL_SUBSHAPES, "Model sub-basin shapefile (in lat-lon)", False, False))
        self.addParameter(ParameterString(MDWF_GenModelFiles.MODEL_SUBCOLUMN, "Name shapefile column holding sub IDs", 'Subbasin'))
        self.addParameter(ParameterFile(MDWF_GenModelFiles.MODEL_CLIMSTATS, "Storage location for model climate station file", True, False))
        self.addParameter(ParameterString(MDWF_GenModelFiles.MODEL_FCFILE, "Name of forecast dates file", 'ForecastDates.txt'))
        self.addParameter(ParameterNumber(MDWF_GenModelFiles.MODEL_PCPFAC, "Precipitation scaling factor", 0.1, 10.0, 1.0))
        self.addParameter(ParameterFile(MDWF_GenModelFiles.MODEL_CENTROIDFILE, "Model sub-basin centroid shapefile (in lat-lon)", False, False))
        self.addParameter(ParameterString(MDWF_GenModelFiles.MODEL_LATCOLUMN, "Name centroid file column holding Latitude", 'ycoord'))
        self.addParameter(ParameterString(MDWF_GenModelFiles.MODEL_LONCOLUMN, "Name centroid file column holding Longitude", 'xcoord'))
        self.addParameter(ParameterString(MDWF_GenModelFiles.MODEL_ELEVCOLUMN, "Name centroid file column holding Elevation", 'mean'))

    def processAlgorithm(self, progress):
        MODEL_FILEPATH = self.getParameterValue(MDWF_GenModelFiles.MODEL_FILEPATH)
        MODEL_FILE = self.getParameterValue(MDWF_GenModelFiles.MODEL_FILE)
        MODEL_NAME = self.getParameterValue(MDWF_GenModelFiles.MODEL_NAME)
        MODEL_TYPE = self.getParameterValue(MDWF_GenModelFiles.MODEL_TYPE)
        MODEL_STARTDATE = self.getParameterValue(MDWF_GenModelFiles.MODEL_STARTDATE)
        MODEL_SUBSHAPES = self.getParameterValue(MDWF_GenModelFiles.MODEL_SUBSHAPES)
        MODEL_SUBCOLUMN = self.getParameterValue(MDWF_GenModelFiles.MODEL_SUBCOLUMN)
        MODEL_CLIMSTATS = self.getParameterValue(MDWF_GenModelFiles.MODEL_CLIMSTATS)
        MODEL_FCFILE = self.getParameterValue(MDWF_GenModelFiles.MODEL_FCFILE)
        MODEL_PCPFAC = self.getParameterValue(MDWF_GenModelFiles.MODEL_PCPFAC)
        MODEL_CENTROIDFILE = self.getParameterValue(MDWF_GenModelFiles.MODEL_CENTROIDFILE)
        MODEL_LATCOLUMN = self.getParameterValue(MDWF_GenModelFiles.MODEL_LATCOLUMN)
        MODEL_LONCOLUMN = self.getParameterValue(MDWF_GenModelFiles.MODEL_LONCOLUMN)
        MODEL_ELEVCOLUMN = self.getParameterValue(MDWF_GenModelFiles.MODEL_ELEVCOLUMN)

        modelfile = open(MODEL_FILEPATH + os.sep + MODEL_FILE, 'w')
        modelfile.writelines('Model description file\r\n')
        modelfile.writelines('ModelName ' + MODEL_NAME + '\r\n')
        if MODEL_TYPE == 0:
            modelfile.writelines('Type RT\r\n')
        else:
            modelfile.writelines('Type Hist\r\n')
        modelfile.writelines('ModelStartDate ' + MODEL_STARTDATE + '\r\n')
        modelfile.writelines('Shapefile ' + os.path.relpath(MODEL_SUBSHAPES,MODEL_FILEPATH) + '\r\n')
        modelfile.writelines('SubbasinColumn ' + MODEL_SUBCOLUMN + '\r\n')
        modelfile.writelines('Stations ' + os.path.relpath(MODEL_CLIMSTATS,MODEL_FILEPATH) + os.sep + MODEL_NAME + 'Stations.txt' + '\r\n')
        modelfile.writelines('ForecastDateFile ' + MODEL_FCFILE + '\r\n')
        modelfile.writelines('PcpCorrFact ' + str(MODEL_PCPFAC) + '\r\n')
        modelfile.writelines('Centroidfile ' + os.path.relpath(MODEL_CENTROIDFILE,MODEL_FILEPATH) + '\r\n')
        modelfile.writelines('LatColumn ' + str(MODEL_LATCOLUMN) + '\r\n')
        modelfile.writelines('LonColumn ' + str(MODEL_LONCOLUMN) + '\r\n')
        modelfile.writelines('ElevColumn ' + str(MODEL_ELEVCOLUMN) + '\r\n')
        modelfile.close()
        fcfile = open(MODEL_FILEPATH + os.sep + MODEL_FCFILE, 'w')
        fcfile.writelines('Forecast dates file\r\n')
        fcfile.writelines('APCP ' + date.today().strftime('%Y%m%d') + '\r\n')
        fcfile.writelines('TMP ' + date.today().strftime('%Y%m%d') + '\r\n')
        fcfile.close()

        # Generate climate station file
        # Write station file
        model = ModelFile(MODEL_FILEPATH + os.sep + MODEL_FILE)

        layer = dataobjects.getObjectFromUri(model.Path+os.sep+model.desc['Shapefile'])
        extent = str(layer.extent().xMinimum())+","+str(layer.extent().xMaximum())+","+str(layer.extent().yMinimum())+","+str(layer.extent().yMaximum())
        Subbasin_filename = model.Path + os.sep + model.desc['SubbasinColumn'] + '.txt'
        processing.runalg("grass7:v.db.select",model.Path+os.sep+model.desc['Shapefile'],1,model.desc['SubbasinColumn'],False,",","","","",False,False,extent,-1, 0.0001, Subbasin_filename)

        layer = dataobjects.getObjectFromUri(model.Path+os.sep+model.desc['Centroidfile'])
        extent = str(layer.extent().xMinimum())+","+str(layer.extent().xMaximum())+","+str(layer.extent().yMinimum())+","+str(layer.extent().yMaximum())
        Lat_filename = model.Path + os.sep + model.desc['LatColumn'] + '.txt'
        processing.runalg("grass7:v.db.select",model.Path+os.sep+model.desc['Centroidfile'],1,model.desc['LatColumn'],False,",","","","",False,False,extent,-1, 0.0001, Lat_filename)
        Lon_filename = model.Path + os.sep + model.desc['LonColumn'] + '.txt'
        processing.runalg("grass7:v.db.select",model.Path+os.sep+model.desc['Centroidfile'],1,model.desc['LonColumn'],False,",","","","",False,False,extent,-1, 0.0001, Lon_filename)
        Elev_filename = model.Path + os.sep + model.desc['ElevColumn'] + '.txt'
        processing.runalg("grass7:v.db.select",model.Path+os.sep+model.desc['Centroidfile'],1,model.desc['ElevColumn'],False,",","","","",False,False,extent,-1, 0.0001, Elev_filename)


        # Read subbasins from file
        Subbasins = []
        Subbasin_file = open(Subbasin_filename,'r').readlines()
        for n in range(1,len(Subbasin_file)):
            Subbasins.append(int(Subbasin_file[n]))

        Latitudes = []
        Lat_file = open(Lat_filename,'r').readlines()
        for n in range(1,len(Lat_file)):
            Latitudes.append(float(Lat_file[n]))

        Longitudes = []
        Lon_file = open(Lon_filename,'r').readlines()
        for n in range(1,len(Lon_file)):
            Longitudes.append(float(Lon_file[n]))

        Elevations = []
        Elev_file = open(Elev_filename,'r').readlines()
        for n in range(1,len(Elev_file)):
            Elevations.append(float(Elev_file[n]))

        Stations_file = open(model.Path + os.sep + model.desc['Stations'],'w')
        startdate = date(int(MODEL_STARTDATE[0:4]),int(MODEL_STARTDATE[4:6]),int(MODEL_STARTDATE[6:8]))
        printdate = startdate-timedelta(1)
        printjday = (printdate - date(printdate.year,1,1)).days + 1
        pfirstlinenstat = "%04d" %printdate.year + "%03d" %printjday + "%05.1f" % -99.9
        tfirstlinenstat = "%04d" %printdate.year + "%03d" %printjday + "%05.1f" % -99.9 + "%05.1f" % -99.9
        for n in range(0,len(Subbasins)):
            lat = Latitudes[n]*100
            lon = Longitudes[n]*100
            Elev = Elevations[n]
            towrite = "%06d" % Subbasins[n] + ("%+05d" % lat).rjust(36) + ("%+06d" % lon).rjust(7) + ("%+05d" % Elev).rjust(6) + '\n'
            Stations_file.writelines(towrite)
            pStation_n_name = MODEL_CLIMSTATS + os.sep + "%06d" % Subbasins[n] + '.pcp'
            tStation_n_name = MODEL_CLIMSTATS + os.sep + "%06d" % Subbasins[n] + '.tmp'
            pStation_n_file = open(pStation_n_name,'w')
            tStation_n_file = open(tStation_n_name,'w')
            pStation_n_file.writelines('Precipitation Input File ' + "%06d" % Subbasins[n] + '.pcp\n')
            tStation_n_file.writelines('Temperature Input File ' + "%06d" % Subbasins[n] + '.tmp\n')
            pStation_n_file.writelines('Lati' + "%8.2f" % Latitudes[n]  + '\n')
            tStation_n_file.writelines('Lati' + "%8.2f" % Latitudes[n]  + '\n')
            pStation_n_file.writelines('Long' + "%8.2f" % Longitudes[n]  + '\n')
            tStation_n_file.writelines('Long' + "%8.2f" % Longitudes[n]  + '\n')
            pStation_n_file.writelines('Elev' + "%8.2f" % Elevations[n]  + '\n')
            tStation_n_file.writelines('Elev' + "%8.2f" % Elevations[n]  + '\n')
            pStation_n_file.writelines(pfirstlinenstat + '\n')
            tStation_n_file.writelines(tfirstlinenstat + '\n')
            pStation_n_file.close()
            tStation_n_file.close()
        Stations_file.close()

        modelfile = open(MODEL_FILEPATH + os.sep + MODEL_FILE, 'a')
        modelfile.writelines('TotalNoSubs ' + str(len(Subbasins)) + '\r\n')
        modelfile.close()

