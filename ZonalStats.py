"""
***************************************************************************
   ZonalStats.py
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
import math
import processing
from processing.tools import dataobjects
from processing.algs.grass.GrassUtils import GrassUtils
import numpy
from osgeo import gdal
from osgeo.gdalconst import *

def ZonalStats(Startdate, Enddate, model_folder, model_name, InVName, sb_column, subcatchmap_res, file_list, log_file, GeoAlgorithmExecutionException, corr_by_num = None, corr_by_fact = None):

    if not os.path.isfile(InVName):
        raise GeoAlgorithmExecutionException('No shapefile: \"' + InVName + '\" ')
    if file_list == []:
        raise GeoAlgorithmExecutionException('List of files is empty')

    index = -1
    Times = []
    first = True

    # Get Subbasins from shapefile and save to txt file
    layer = dataobjects.getObjectFromUri(InVName)
    extent = str(layer.extent().xMinimum())+","+str(layer.extent().xMaximum())+","+str(layer.extent().yMinimum())+","+str(layer.extent().yMaximum())
    Subbasin_filename = model_folder + os.sep + sb_column + '.txt'
    processing.runalg("grass:v.db.select",InVName,1,sb_column,False,",","","","",False,False,extent, -1, 0.0001, Subbasin_filename)

    # Read subbasins from file
    Subbasins = []
    Subbasin_file = open(Subbasin_filename,'r').readlines()
    for n in range(1,len(Subbasin_file)):
        Subbasins.append(int(Subbasin_file[n]))
    log_file.write("Subbasins: %s \n"%Subbasins)

    # Creating a list of dates (year + julian day)
    dates = []
    for n in range(0,(Enddate-Startdate).days+1):
        d = Startdate+timedelta(days=n)
        year = d.year
        day = (d-date(year,1,1)).days + 1
        dates.append(str(year) + str(day).zfill(3))

    # Initialising array for results
    resultTS = numpy.ones([len(dates),len(Subbasins)]) * -99.0

    R_Xres_old = -9999
    R_Yres_old = -9999
    R_Xleft_old = -9999
    R_Ytop_old = -9999
    R_Xsize_old = -9999
    R_Ysize_old = -9999
    # Extracting data and saving in array
    for file_name in file_list:
        f = os.path.split(file_name)[1]
        file_date = date(int(f[0:4]),int(f[4:6]),int(f[6:8]))
        year = file_date.year
        day = (file_date-date(year,1,1)).days + 1
        ind = dates.index(str(year) + str(day).zfill(3)) # index in dates list

        # Get info from raster
        dataset = gdal.Open(file_name, GA_ReadOnly)
        if dataset is None:
                raise GeoAlgorithmExecutionException('Cannot open file ' + file_name)
        R_Xsize = dataset.RasterXSize
        R_Ysize = dataset.RasterYSize
        geotransform = dataset.GetGeoTransform()
        R_Xres = float('%.3f' %geotransform[1])
        R_Yres = float('%.3f' %geotransform[5])
        R_Xleft = float('%.3f' %geotransform[0])
        R_Ytop = float('%.3f' %geotransform[3])
        R_map_array = dataset.ReadAsArray()
        b = dataset.GetRasterBand(1)
        NoDataValue = b.GetNoDataValue()
        if not dataset.GetProjection().split('DATUM["')[1][0:8] == 'WGS_1984':
            raise GeoAlgorithmExecutionException('Datafiles must be in WGS_1984 datum')
        dataset = None # Closing dataset
        b = None

        # Check is raster have same size and resolution as last processed raster, if no new coefficient maps will be created
        if (first) or (R_Xres_old != R_Xres) or (R_Yres_old != R_Yres) or (R_Xleft_old != R_Xleft) or (R_Ytop_old != R_Ytop) \
        or (R_Xsize_old != R_Xsize) or (R_Ysize_old != R_Ysize):

            log_file.write("Creating maps \n")
            # Rasterize model shapefile
            layer = dataobjects.getObjectFromUri(InVName)
            V_Xmin = math.floor(layer.extent().xMinimum())-(R_Xres/2)
            V_Xmax = math.ceil(layer.extent().xMaximum())+(R_Xres/2)
            V_Ymin = math.floor(layer.extent().yMinimum())+(R_Yres/2)
            if layer.extent().yMinimum() < V_Ymin:
                V_Ymin = math.floor(layer.extent().yMinimum())-(R_Yres/2)
            V_Ymax = math.ceil(layer.extent().yMaximum())-(R_Yres/2)
            if layer.extent().yMaximum() > V_Ymax:
                V_Ymax = math.ceil(layer.extent().yMaximum())+(R_Yres/2)
##            V_Ymin = math.floor(layer.extent().yMinimum())+(R_Yres/2)
##            V_Ymax = math.ceil(layer.extent().yMaximum())-(R_Yres/2)
            extent = str(V_Xmin)+","+str(V_Xmax)+","+str(V_Ymin)+","+str(V_Ymax)
            OutRName = model_folder + os.sep + model_name + '_Raster.tif'
            #param = {'input':InVName, 'use':0, 'column':sb_column, 'GRASS_REGION_PARAMETER':extent, 'GRASS_REGION_CELLSIZE_PARAMETER':subcatchmap_res, 'GRASS_SNAP_TOLERANCE_PARAMETER':0.01, 'GRASS_MIN_AREA_PARAMETER':0.001, 'output':OutRName}
            processing.runalg("grass:v.to.rast.attribute",InVName,0,sb_column,extent,subcatchmap_res,0.01,0.001,OutRName)

            # Get info from new raster
            dataset = gdal.Open(OutRName, GA_ReadOnly)
            if dataset is None:
                raise GeoAlgorithmExecutionException('Cannot open file ' + OutRName)
            sc = dataset.ReadAsArray()
            geotransform = dataset.GetGeoTransform()
            sc_Xres = geotransform[1]
            sc_Yres = geotransform[5]
            sc_Xleft = geotransform[0]
            sc_Ytop = geotransform[3]
            if not dataset.GetProjection().split('DATUM["')[1][0:8] == 'WGS_1984':
                raise GeoAlgorithmExecutionException('Shapefile must be in WGS_1984 datum')
            dataset = None # Closing dataset

            # Check resolution
            if (abs(sc_Xres) > abs(R_Xres)) or (abs(sc_Yres) > abs(R_Ysize)):
                raise GeoAlgorithmExecutionException('Resolution of subcatchment map must be less that raster data maps, try using a smaller subcatchment map resolution as input.')

            # Check for all subcatchments
            if not len(numpy.unique(sc))-1 == len(Subbasins):
                raise GeoAlgorithmExecutionException('Not all subcatchment are found in raster map: ' + OutRName + ', try using a smaller subcatchment map resolution as input.')

            # Create maps for each subcatchment for use in coefficients map method
            # Create array with a unique number for each pixel. Area as rastarized vector map and resolution as raster data map
            unique_array = numpy.resize(range(1,int((V_Xmax-V_Xmin)/abs(R_Xres))*int((V_Ymax-V_Ymin)/abs(R_Yres))+1),[int((V_Ymax-V_Ymin)/abs(R_Yres)),int((V_Xmax-V_Xmin)/abs(R_Xres))])
            x_factor = int(round(sc.shape[1]/float(unique_array.shape[1]))) # x resoution factor between rasterized vector and unique_array
            y_factor = int(round(sc.shape[0]/float(unique_array.shape[0]))) # y resoution factor between rasterized vector and unique_array
            unique_array_resample = numpy.zeros(sc.shape) # initializing array for resampling
            ones_array = numpy.ones([y_factor,x_factor]) # work array
            # Resampling
            # looping x
            for m in range(0,unique_array.shape[1]):
                # looping y
                for n in range(0,unique_array.shape[0]):
                    value = unique_array[n,m]
                    unique_array_resample[n*y_factor:n*y_factor+y_factor,m*x_factor:m*x_factor+x_factor] = ones_array*value

            # Creating map for each subcatchment and save in dict
            catchment_maps = {}
            for catchment in Subbasins:
                # Init maps
                temp_map = numpy.where(sc == catchment, unique_array_resample, 0.0)
                catch_size = len(numpy.nonzero(temp_map)[0])
                catchment_map =  unique_array * 0.0
                catchment_map = catchment_map.reshape(1, catchment_map.size)

                # Calculate coefficients
                for i in numpy.unique(temp_map)[1:]:
                    count = len(numpy.nonzero(numpy.where(temp_map == i, temp_map, 0.0))[0]) / float(catch_size)
##                    count = numpy.count_nonzero(numpy.where(temp_map == i, temp_map, 0.0)) / float(catch_size)
                    catchment_map[0,int(i-1)] = count

                catchment_map = catchment_map.reshape(unique_array.shape) # Coefficients map

                # Place coefficient map in array with same size as raster data map
                catchment_map_large = numpy.zeros([R_Ysize,R_Xsize])
                x_indent = int(abs((R_Xleft-sc_Xleft)/R_Xres))
                y_indent = int(abs((R_Ytop-sc_Ytop)/R_Yres))
                # looping x
                for m in range(0,catchment_map.shape[1]):
                    # looping y
                    for n in range(0,catchment_map.shape[0]):
                        catchment_map_large[y_indent+n,x_indent+m] = catchment_map[n,m]

                # Put final coefficient map in a dict with key = 'subcatch ID'
                catchment_maps[str(catchment)] = catchment_map_large

##                # Save coefficient maps to ascii files (For testing)
##                numpy.savetxt(model_folder + os.sep + str(catchment) + '.asc', catchment_maps[str(catchment)], delimiter=" ")
##                # Add .asc header to files
##                header = 'ncols         ' + str(R_Xsize) + '\n' + 'nrows         ' + str(R_Ysize) + '\n' + 'xllcorner     ' + str(R_Xleft) + '\n' \
##                            + 'yllcorner     ' + str(R_Ytop + R_Yres*R_Ysize) + '\n' + 'cellsize      ' + str(R_Xres) + '\n' + 'NODATA_value  0\n'
##                with open(model_folder + os.sep + str(catchment) + '.asc', "r+") as f:
##                    old = f.read() # read everything in the file
##                    f.seek(0) # rewind
##                    f.write(header + old) # write the new line before

            # Values for comparing next raster data map
            first = False
            R_Xres_old = R_Xres
            R_Yres_old = R_Yres
            R_Xleft_old = R_Xleft
            R_Ytop_old = R_Ytop
            R_Xsize_old = R_Xsize
            R_Ysize_old = R_Ysize

        if NoDataValue != None:
                R_map_array[R_map_array==NoDataValue]=numpy.nan

        # Extract data from raster map using coefficients maps
        for catchment in Subbasins:
            # Check for NoDataValues
            if (numpy.isnan(R_map_array[catchment_maps[str(catchment)]>0])).any():
                resultTS[ind,catchment-1] = float(-99.0)
            elif corr_by_num != None:
                value = numpy.nansum( (R_map_array+corr_by_num) * catchment_maps[str(catchment)])
                resultTS[ind,catchment-1] = float(value)
            elif corr_by_fact != None:
                value = numpy.nansum( (R_map_array*corr_by_fact) * catchment_maps[str(catchment)])
                resultTS[ind,catchment-1] = float(value)
            else:
                value = numpy.nansum(R_map_array * catchment_maps[str(catchment)])
                resultTS[ind,catchment-1] = float(value)


##        # Save results to csv file
##        numpy.savetxt(model_folder + os.sep + 'Result.csv', resultTS, delimiter=",")

    # Return results
    return dates, resultTS






