# -*- coding: utf-8 -*-

# Copyright © 2018 PyHelp Project Contributors
# https://github.com/jnsebgosselin/pyhelp
#
# This file is part of PyHelp.
# Licensed under the terms of the GNU General Public License.


# ---- Standard Library Imports

import os
import os.path as osp
from multiprocessing import Pool
import multiprocessing as mp
import time
import csv
import calendar

# ---- Third Party imports

import numpy as np

# ---- Local Libraries Imports

from pyhelp import HELP3O


# ---- Run HELP

def run_help_singlecell(item):
    """Run HELP for a single cell."""
    cellname, outparam = item
    if not osp.exists(outparam[5]):
        HELP3O.run_simulation(*outparam)
    results = read_monthly_help_output(outparam[5])
    os.remove(outparam[5])
    return (cellname, results)


def run_help_allcells(cellparams, ncore=None):
    """Run HELP in batch for multiple cells."""
    output = {}
    ncore = max(mp.cpu_count() if ncore is None else ncore, 1)
    tstart = time.clock()
    calcul_progress = 0
    N = len(cellparams)
    pool = Pool(ncore)
    for cell in pool.imap_unordered(run_help_singlecell, cellparams.items()):
        output[cell[0]] = cell[1]
        calcul_progress += 1
        progress_pct = calcul_progress/N*100
        tpassed = time.clock() - tstart
        tremain = (100-progress_pct)*tpassed/progress_pct/60
        print('\r%0.1f%% (%0.1f min remaining)' % (progress_pct, tremain),
              end='')
    calcul_time = (time.clock() - tstart)
    print('\nCalculation time: %0.2fs\n' % calcul_time)

    return output


# ---- Read HELP output

def read_monthly_help_output(filename):
    """
    Read the monthly output from .OUT HELP file and return the data as
    numpy arrays stored in a dictionary.
    """
    with open(filename, 'r') as csvfile:
        csvread = list(csv.reader(csvfile))

    arr_years = []
    vstack_precip = []
    vstack_runoff = []
    vstack_evapo = []
    vstack_subrunoff = []
    vstack_percol = []
    vstack_rechg = []

    year = None
    i = 0
    while True:
        if i+1 >= len(csvread):
            break
        if len(csvread[i]) == 0:
            i += 1
            continue

        line = csvread[i][0]
        if 'MONTHLY TOTALS' in line:
            year = int(line.split()[-1])
            arr_years.append(year)
            subrunoff = None
            percol = None
            while True:
                i += 1
                if len(csvread[i]) == 0:
                    continue
                line = csvread[i][0]
                if '**********' in line:
                    break
                if len(csvread[i+1]) == 0:
                    continue

                nline = csvread[i+1][0]
                if 'PRECIPITATION' in line:
                    precip = line.split()[-6:] + nline.split()[-6:]
                elif 'RUNOFF' in line:
                    runoff = line.split()[-6:] + nline.split()[-6:]
                elif 'EVAPOTRANSPIRATION' in line:
                    evapo = line.split()[-6:] + nline.split()[-6:]
                elif 'LATERAL DRAINAGE' in line and subrunoff is None:
                    subrunoff = line.split()[-6:] + nline.split()[-6:]
                elif 'PERCOLATION' in line:
                    if percol is None:
                        percol = line.split()[-6:] + nline.split()[-6:]
                    rechg = line.split()[-6:] + nline.split()[-6:]
            vstack_precip.append(np.array(precip).astype('float32'))
            vstack_runoff.append(np.array(runoff).astype('float32'))
            vstack_evapo.append(np.array(evapo).astype('float32'))
            vstack_rechg.append(np.array(rechg).astype('float32'))
            vstack_percol.append(np.array(percol).astype('float32'))
            if subrunoff is None:
                vstack_subrunoff.append(np.zeros(12).astype('float32'))
            else:
                vstack_subrunoff.append(np.array(subrunoff).astype('float32'))
        elif 'FINAL WATER STORAGE' in line:
            break

        i += 1

    data = {'years': np.array(arr_years).astype('uint16'),
            'rain': np.vstack(vstack_precip),
            'runoff': np.vstack(vstack_runoff),
            'evapo': np.vstack(vstack_evapo),
            'sub-runoff': np.vstack(vstack_subrunoff),
            'percolation': np.vstack(vstack_percol),
            'recharge': np.vstack(vstack_rechg)}
    return data


def read_daily_help_output(filename):
    """
    Read the daily output from .OUT HELP file and return the data as
    numpy arrays stored in a dictionary.
    """
    with open(filename, 'r') as csvfile:
        csvread = list(csv.reader(csvfile))

    nlay = None
    arr_years = []
    arr_days = []
    arr_rain = []
    arr_ru = []
    arr_et = []
    arr_ezone = []
    arr_headfirst = []
    arr_drainfirst = []
    arr_leakfirst = []
    arr_leaklast = []

    year = None
    nlay = nsub = None
    for i, line in enumerate(csvread):
        if line:
            line = line[0]
            if 'TOTAL NUMBER OF LAYERS' in line:
                nlay = int(line.split()[-1])
            elif 'TOTAL NUMBER OF SUBPROFILES' in line:
                nsub = int(line.split()[-1])
            if 'DAILY OUTPUT FOR YEAR' in line:
                year = int(line.split()[-1])
                days_in_year = 366 if calendar.isleap(year) else 365
            elif year is not None:
                try:
                    day = int(line[2:5])
                    rain = float(line[13:19])
                    ru = float(line[19:26])
                    et = float(line[26:33])
                    ezone = float(line[33:41])
                    headfirst = float(line[41:51])
                    drainfirst = float(line[51:61])
                    leakfirst = float(line[61:71])
                    leaklast = float(line[-10:])
                except ValueError:
                    pass
                else:
                    arr_years.append(year)
                    arr_days.append(day)
                    arr_rain.append(rain)
                    arr_ru.append(ru)
                    arr_et.append(et)
                    arr_ezone.append(ezone)
                    arr_headfirst.append(headfirst)
                    arr_drainfirst.append(drainfirst)
                    arr_leakfirst.append(leakfirst)
                    arr_leaklast.append(leaklast)
                    if day == days_in_year:
                        year = None

    dataf = {'years': np.array(arr_years).astype('uint16'),
             'days': np.array(arr_days).astype('uint16'),
             'rain': np.array(arr_rain).astype('float32'),
             'runoff': np.array(arr_ru).astype('float32'),
             'et': np.array(arr_et).astype('float32'),
             'ezone': np.array(arr_ezone).astype('float32'),
             'head first': np.array(arr_headfirst).astype('float32'),
             'drain first': np.array(arr_drainfirst).astype('float32'),
             'leak first': np.array(arr_leakfirst).astype('float32'),
             'leak last': np.array(arr_leaklast).astype('float32')
             }
    return dataf
