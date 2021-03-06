# -*- coding: utf-8 -*-

# Copyright © 2014-2018 GWHAT Project Contributors
# https://github.com/jnsebgosselin/gwhat
#
# This file is part of GWHAT (Ground-Water Hydrograph Analysis Toolbox).
# Licensed under the terms of the GNU General Public License.


# ---- Standard Library imports

import os.path as osp
import csv
import calendar
from calendar import monthrange

# ---- Third Party imports

import numpy as np
from xlrd.xldate import xldate_from_datetime_tuple


def save_content_to_csv(fname, fcontent, mode='w', delimiter=',',
                        encoding='utf8'):
    """
    Save content in a csv file with the specifications provided
    in arguments.
    """
    with open(fname, mode, encoding='utf8') as csvfile:
        writer = csv.writer(csvfile, delimiter=delimiter, lineterminator='\n')
        writer.writerows(fcontent)


# ---- Read CWEEDS Files

def read_cweeds_file(filename, format_to_daily=True):
    """
    Reads and formats data from a CWEEDS file, either version WY2 or WY3.
    Returns a dictionary, which includes a numpy array of the global
    solar irradiance in MJ/m², as well as corresponding arrays of the years,
    months, days, and hours. By default, the hourly data from the CWEEDS file
    are formated to daily values. The data are kept in a hourly format if
    format_to_daily is set to False.
    """
    # Determine if the CWEEDS file is in the WY2 or WY3 format :

    root, ext = osp.splitext(filename)
    ext = ext.replace('.', '')
    if ext not in ['WY2', 'WY3']:
        raise ValueError("%s is not a valid file extension. CWEEHDS files must"
                         " have either a WY2 or WY3 extension" % ext)

    # Open and format the data from the CWEEDS file :

    with open(filename, 'r') as f:
        reader = list(csv.reader(f))

    header_df = {}
    if ext == 'WY3':
        # We remove the header line from the data if the format is WY3.
        header_list = reader.pop(0)
        header_df['HORZ version'] = header_list[0]
        header_df['Location'] = header_list[1]
        header_df['Province'] = header_list[2]
        header_df['Country'] = header_list[3]
        header_df['Station ID'] = header_list[4]
        header_df['Latitude'] = float(header_list[5])
        header_df['Longitude'] = float(header_list[6])
        header_df['Time Zone'] = float(header_list[7])
        header_df['Elevation'] = float(header_list[8])

    char_offset = 0 if ext == 'WY2' else 2
    hourly_df = {}
    hourly_df['Years'] = np.empty(len(reader)).astype(int)
    hourly_df['Months'] = np.empty(len(reader)).astype(int)
    hourly_df['Days'] = np.empty(len(reader)).astype(int)
    hourly_df['Hours'] = np.empty(len(reader)).astype(int)
    hourly_df['Time'] = np.empty(len(reader)).astype('float64')
    # Global horizontal irradiance, kJ/m²
    hourly_df['Irradiance'] = np.empty(len(reader)).astype('float64')

    for i, line in enumerate(reader):
        hourly_df['Years'][i] = year = int(line[0][char_offset:][6:10])
        hourly_df['Months'][i] = month = int(line[0][char_offset:][10:12])
        hourly_df['Days'][i] = day = int(line[0][char_offset:][12:14])
        hourly_df['Hours'][i] = hour = int(line[0][char_offset:][14:16]) - 1
        # The global horizontal irradiance is converted from kJ/m² to MJ/m².
        hourly_df['Irradiance'][i] = float(line[0][char_offset:][20:24])/1000

        # Compute time in Excel numeric format :
        hourly_df['Time'][i] = xldate_from_datetime_tuple(
                (year, month, day, hour, 0, 0), 0)

    if format_to_daily:
        # Convert the hourly data to daily format.
        assert len(hourly_df['Irradiance']) % 24 == 0
        new_shape = (len(hourly_df['Irradiance'])//24, 24)

        daily_df = {}
        daily_df['Irradiance'] = np.sum(
                hourly_df['Irradiance'].reshape(new_shape), axis=1)
        for key in ['Years', 'Months', 'Days', 'Time']:
            daily_df[key] = hourly_df[key].reshape(new_shape)[:, 0]
        daily_df['Hours'] = np.zeros(len(daily_df['Irradiance']))

        daily_df.update(header_df)
        daily_df['Time Format'] = 'daily'
        daily_df['CWEEDS Format'] = ext
        return daily_df
    else:
        hourly_df.update(header_df)
        hourly_df['Time Format'] = 'hourly'
        hourly_df['CWEEDS Format'] = ext
        return hourly_df


def join_daily_cweeds_wy2_and_wy3(wy2_df, wy3_df):
    """
    Join a CWEEDS dataset in the wy2 format to another cweeds dataset in the
    wy3 format.
    """
    assert wy2_df['CWEEDS Format'] == 'WY2'
    assert wy3_df['CWEEDS Format'] == 'WY3'
    assert wy2_df['Time Format'] == wy3_df['Time Format']

    time_wy23 = np.hstack([wy2_df['Time'], wy3_df['Time']])
    time_wy23 = np.unique(time_wy23)
    time_wy23 = np.sort(time_wy23)

    wy23_df = {}
    wy23_df['Time Format'] = wy3_df['Time Format']
    wy23_df['CWEEDS Format'] = 'WY2+WY3'

    # Copy the header info from WY3 dataset :

    for key in ['HORZ version', 'Location', 'Province', 'Country',
                'Station ID', 'Latitude', 'Longitude', 'Time Zone',
                'Elevation']:
        wy23_df[key] = wy3_df[key]

    # Merge the two datasets :

    wy23_df['Time'] = time_wy23
    wy23_df['Years'] = np.empty(len(time_wy23)).astype(int)
    wy23_df['Months'] = np.empty(len(time_wy23)).astype(int)
    wy23_df['Days'] = np.empty(len(time_wy23)).astype(int)
    wy23_df['Hours'] = np.empty(len(time_wy23)).astype(int)
    wy23_df['Irradiance'] = np.empty(len(time_wy23)).astype('float64')

    for dataset in [wy2_df, wy3_df]:
        indexes = np.digitize(dataset['Time'], time_wy23, right=True)
        for key in ['Years', 'Months', 'Days', 'Hours', 'Irradiance']:
            wy23_df[key][indexes] = dataset[key]

    return wy23_df


# ---- Export to HELP format

def save_precip_to_HELP(filename, years, precip, city):
    """
    Formats and saves a daily precipitation time series in mm
    to the HELP format.
    """
    root, ext = osp.splitext(filename)
    filename = filename if ext == '.D4' else filename + '.D4'

    fheader = format_weather_header_for_HELP(3, 2, city)
    fdata = format_timeseries_for_HELP(years, precip, '{0:>10}', '{0:>5.1f}')
    save_content_to_csv(filename, fheader + fdata)


def save_airtemp_to_HELP(filename, years, precip, city):
    """
    Formats and saves a daily average air temperature time series in Celcius to
    the HELP format.
    """
    root, ext = osp.splitext(filename)
    filename = filename if ext == '.D7' else filename + '.D7'

    fheader = format_weather_header_for_HELP(3, 2, city)
    fdata = format_timeseries_for_HELP(years, precip, '{0:>5}', '{0:>6.1f}')
    save_content_to_csv(filename, fheader + fdata)


def save_solrad_to_HELP(filename, years, precip, city, lat):
    """
    Formats and saves a daily global solar radiation time series in MJ/m2/day
    to the HELP format.
    """
    root, ext = osp.splitext(filename)
    filename = filename if ext == '.D13' else filename + '.D13'

    fheader = format_weather_header_for_HELP(3, 2, city, lat)
    fdata = format_timeseries_for_HELP(years, precip, '{0:>5}', '{0:>6.2f}')
    save_content_to_csv(filename, fheader + fdata)


def format_weather_header_for_HELP(itype, iunits, city, lat=None):
    """
    Prepare the header for the precipitation, air temperature and
    global solar radiation input weather datafile for HELP. The format of the
    header is defined in the subroutine READIN of the HELP Fortran source code.
    """
    fheader = [['{0:>2}'.format(itype)],  # 3: data was entered by the user.
               ['{0:>2}'.format(iunits)],  # 1 for IP and 2 for SI
               ['{0:<40}'.format(city[:40])],
               ]
    if lat is not None:
        # Append the latitude if the data are solar radiation.
        fheader.append(['{0:>6.2f}'.format(lat)])
    else:
        fheader.append([])
    return fheader


def format_timeseries_for_HELP(years, data, year_format, data_format):
    fdata = []
    for year in np.unique(years):
        # Selects the data and asserts that the data are complete for
        # that year :

        indexes = np.where(years == year)[0]
        days_in_year = 366 if calendar.isleap(year) else 365
        assert len(indexes) == days_in_year

        # Adds zeros to complete de last row and reshape the data
        # in a 37 x 10 grid:

        year_data = data[indexes]
        year_data = np.hstack(
                [year_data, np.zeros(10 - len(year_data) % 10)])
        year_data = year_data.reshape(37, 10).tolist()

        # Save the data in a format compatible with HELP :

        for line_data in year_data:
            formated_line = year_format.format(year)
            for i in range(10):
                formated_line += data_format.format(line_data[i])
            fdata.append([formated_line])
    return fdata


def save_data_to_HELP_format(filename, years, data, city, lat=None):
    """Formats a time series to the HELP format."""
    root, ext = osp.splitext(filename)
    ext = ext[1:]
    if ext == 'D4':  # precipitation
        year_format = '{0:>10}'
        data_format = '{0:>5.1f}'
    elif ext == 'D7':  # air temperature
        year_format = '{0:>5}'
        data_format = '{0:>6.1f}'
    elif ext == 'D13':  # global solar radiation
        year_format = '{0:>5}'
        data_format = '{0:>6.2f}'
        if lat is None:
            raise ValueError("A value must be specified for lat.")
    else:
        raise ValueError("%s is not a valid file extension." % ext)

    # ---- Format Header

    itype = 3   # Precipitation data for {city} was entered by the user.
    iunits = 2  # 1 for IP and 2 for SI
    fcontent = [['{0:>2}'.format(itype)],
                ['{0:>2}'.format(iunits)],
                ['{0:<40}'.format(city[:40])],
                ]
    if ext == 'D13':
        # Append the latitude if the data are solar radiation.
        fcontent.append(['{0:>6.2f}'.format(lat)])
    else:
        fcontent.append([])

    # ---- Format Data

    for year in np.unique(years):
        # Selects the data and asserts that the data are complete for
        # that year :

        indexes = np.where(years == year)[0]
        days_in_year = 366 if calendar.isleap(year) else 365
        assert len(indexes) == days_in_year

        # Adds zeros to complete de last row and reshape the data
        # in a 37 x 10 grid:

        year_data = data[indexes]
        year_data = np.hstack(
                [year_data, np.zeros(10 - len(year_data) % 10)])
        year_data = year_data.reshape(37, 10).tolist()

        # Save the data in a format compatible with HELP :

        for line_data in year_data:
            formated_line = year_format.format(year)
            for i in range(10):
                formated_line += data_format.format(line_data[i])
            fcontent.append([formated_line])

    save_content_to_csv(filename, fcontent)


# ---- Base functions: monthly downscaling

def calc_monthly_sum(yy_dly, mm_dly, x_dly):
    """
    Calcul monthly cumulative values from daily values, where yy_dly are the
    years, mm_dly are the months (1 to 12), and x_dly are the daily values.
    """
    return calc_monthly(yy_dly, mm_dly, x_dly, np.sum)


def calc_monthly_mean(yy_dly, mm_dly, x_dly):
    """
    Calcul monthly mean values from daily values, where yy_dly are the
    years, mm_dly are the months (1 to 12), and x_dly are the daily values.
    """
    return calc_monthly(yy_dly, mm_dly, x_dly, np.mean)


def calc_monthly(yy_dly, mm_dly, x_dly, func):
    yy = np.unique(yy_dly)
    mm = range(1, 13)

    yy_mly = np.repeat(yy, len(mm))
    mm_mly = np.tile(mm, len(yy))
    x_mly = np.zeros(len(mm)*len(yy))

    for i in range(len(mm)*len(yy)):
        indx = np.where((yy_dly == yy_mly[i]) & (mm_dly == mm_mly[i]))[0]
        if len(indx) < monthrange(yy_mly[i], mm_mly[i])[1]:
            x_mly[i] = np.nan  # incomplete dataset for this month
        else:
            x_mly[i] = func(x_dly[indx])

    return yy_mly, mm_mly, x_mly


def calcul_monthly_normals(years, months, x_mly, yearmin=None, yearmax=None):
    """Calcul the monthly normals from monthly values."""
    if len(years) != len(months) != len(x_mly):
        raise ValueError("The dimension of the years, months, and x_mly array"
                         " must match exactly.")
    if np.min(months) < 1 or np.max(months) > 12:
        raise ValueError("Months values must be between 1 and 12.")

    # Mark as nan monthly values that are outside the year range that is
    # defined by yearmin and yearmax :
    x_mly = np.copy(x_mly)
    if yearmin is not None:
        x_mly[years < yearmin] = np.nan
    if yearmax is not None:
        x_mly[years > yearmax] = np.nan

    # Calcul the monthly normals :
    x_norm = np.zeros(12)
    for i, mm in enumerate(range(1, 13)):
        indx = np.where((months == mm) & (~np.isnan(x_mly)))[0]
        if len(indx) > 0:
            x_norm[i] = np.mean(x_mly[indx])
        else:
            x_norm[i] = np.nan

    return x_norm


# ----- Base functions: yearly downscaling

def calc_yearly_sum(yy_dly, x_dly):
    """
    Calcul yearly cumulative values from daily values, where yy_dly are the
    years and x_dly are the daily values.
    """
    return calc_yearly(yy_dly, x_dly, np.sum)


def calc_yearly_mean(yy_dly, x_dly):
    """
    Calcul yearly mean values from daily values, where yy_dly are the years
    and x_dly are the daily values.
    """
    return calc_yearly(yy_dly, x_dly, np.mean)


def calc_yearly(yy_dly, x_dly, func):
    yy_yrly = np.unique(yy_dly)
    x_yrly = np.zeros(len(yy_yrly))
    for i in range(len(yy_yrly)):
        indx = np.where(yy_dly == yy_yrly[i])[0]
        x_yrly[i] = func(x_dly[indx])

    return yy_yrly, x_yrly


# ----- Base functions: secondary variables

def calcul_rain_from_ptot(Tavg, Ptot, Tcrit=0):
    rain = np.copy(Ptot)
    rain[np.where(Tavg < Tcrit)[0]] = 0
    return rain
