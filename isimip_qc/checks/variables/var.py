import math

import netCDF4
import numpy as np
from isimip_qc.config import settings


def check_variable(file):
    variable_name = file.specifiers.get('variable')
    variable = file.dataset.variables.get(variable_name)
    definition = settings.DEFINITIONS.get('variable', {}).get(variable_name)

    if not variable:
        file.error('Variable %s is missing.', variable_name)
    elif not definition:
        file.error('Definition for variable %s is missing.', variable_name)
    else:
        # check file name and NetCDF variable to match each other
        if variable.name != variable_name:
            file.error('File name variable (%s) does not match internal variable name (%s).', variable_name, variable.name)

        # check dtype
        if variable.dtype != 'float32':
            file.warn('%s.dtype="%s" should be "float32".', variable_name, variable.dtype)

        # check chunking
        chunking = variable.chunking()
        if chunking[0] != 1 or chunking[-2] != 360 or chunking[-1] != 720:
            file.warn('%s.chunking=%s should be [1, ... , 360, 720].', variable_name, chunking)
        else:
            file.info('Variable chunking looks good (%s)', chunking)

        # check dimensions
        definition_dimensions = tuple(definition.get('dimensions', []))
        if file.is_2d:
            default_dimensions = ('time', 'lat', 'lon')
        elif file.is_3d:
            default_dimensions = ('time', 'depth', 'lat', 'lon')

        if definition_dimensions:
            if variable.dimensions not in [definition_dimensions, default_dimensions]:
                file.error('%s dimension %s must be %s or %s.', variable_name, variable.dimensions, definition_dimensions, default_dimensions)
        else:
            if variable.dimensions != default_dimensions:
                file.error('%s dimension %s must be %s.', variable_name, variable.dimensions, default_dimensions)

        # check variable units
        units = definition.get('units')
        if units is not None:
            try:
                if variable.units != units:
                    file.error('%s.units=%s should be %s.', variable_name, variable.units, units)
                else:
                    file.info('Variable unit matches protocol definition (%s)', variable.units)
            except AttributeError:
                file.error('%s.units is missing. Should be "%s".', variable_name, units)
        else:
            file.warn('No units information on %s in definition.', variable_name)

        # check _FillValue and missing_value
        for name in ['_FillValue', 'missing_value']:
            try:
                attr = variable.getncattr(name)
                if not math.isclose(attr, 1e+20, rel_tol=1e-6):
                    file.error('Missing values for variable "%s": %s=%s but should be 1e+20.', variable_name, name, attr)
                else:
                    file.info('Missing value attribute "%s" is properly set.', name)
            except AttributeError:
                file.error('Missing value attribute "%s" for variable "%s" is missing. Should be set to 1e+20.', name, variable_name)

        # check valid range
        if settings.MINMAX:
            valid_min = definition.get('valid_min')
            valid_max = definition.get('valid_max')
            if (valid_min is not None) and (valid_min is not None):
                file.info("Checking values for valid minimum and maximum range defined in the protocol. This could take some time...")
                lat = file.dataset.variables.get('lat')
                lon = file.dataset.variables.get('lon')
                time = file.dataset.variables.get('time')

                too_low = np.argwhere(variable[:] < valid_min)
                too_high = np.argwhere(variable[:] > valid_max)

                time = file.dataset.variables.get('time')
                time_resolution = file.specifiers.get('time_step')

                try:
                    time_units = time.units
                except AttributeError:
                    pass

                if time_resolution == 'daily':
                    try:
                        time_calendar = time.calendar
                    except AttributeError:
                        pass
                if time_resolution in ['monthly', 'annual']:
                    time_calendar = '360_day'

                if too_low.size:
                    file.error('%i values are lower than the valid minimum (%.2E).', too_low.shape[0], valid_min)
                    if settings.LOG_LEVEL == 'INFO':
                        file.info('%i lowest values are :', min(settings.MINMAX, too_low.shape[0]))

                        too_low_list = []
                        for index in too_low[0:too_low.shape[0]]:
                            too_low_list.append([tuple(index), variable[tuple(index)].data.tolist()])
                        too_low_sorted = sorted(too_low_list, key=lambda value: value[1], reverse=False)
                        for i in range(0, min(settings.MINMAX, too_low.shape[0])):
                            if file.is_2d:
                                file.info('date: %s, lat/lon: %4.2f/%4.2f, value: %E',
                                          netCDF4.num2date(time[too_low_sorted[i][0][0]], time_units, time_calendar),
                                          lat[too_low_sorted[i][0][-2]],
                                          lon[too_low_sorted[i][0][-1]],
                                          too_low_sorted[i][1])
                            elif file.is_3d:
                                file.info('date: %s, lat/lon: %4.2f/%4.2f, depth: %s, value: %E',
                                          netCDF4.num2date(time[too_low_sorted[i][0][0]], time_units, time_calendar),
                                          too_low_sorted[i][0][-3],
                                          lat[too_low_sorted[i][0][-2]],
                                          lon[too_low_sorted[i][0][-1]],
                                          too_low_sorted[i][1])

                if too_high.size:
                    file.error('%i values are higher than the valid maximum (%.2E).', too_high.shape[0], valid_max)
                    if settings.LOG_LEVEL == 'INFO':
                        file.info('%i highest values are :', min(settings.MINMAX, too_high.shape[0]))

                        too_high_list = []
                        for index in too_high[0:too_high.shape[0]]:
                            too_high_list.append([tuple(index), variable[tuple(index)].data.tolist()])
                        too_high_sorted = sorted(too_high_list, key=lambda value: value[1], reverse=True)
                        for i in range(0, min(settings.MINMAX, too_high.shape[0])):
                            if file.is_2d:
                                file.info('date: %s, lat/lon: %4.2f/%4.2f, value: %E',
                                          netCDF4.num2date(time[too_high_sorted[i][0][0]], time_units, time_calendar),
                                          lat[too_high_sorted[i][0][-2]],
                                          lon[too_high_sorted[i][0][-1]],
                                          too_high_sorted[i][1])
                            elif file.is_3d:
                                file.info('date: %s, lat/lon: %4.2f/%4.2f, depth: %s, value: %E',
                                          netCDF4.num2date(time[too_high_sorted[i][0][0]], time_units, time_calendar),
                                          too_high_sorted[i][0][-3],
                                          lat[too_high_sorted[i][0][-2]],
                                          lon[too_high_sorted[i][0][-1]],
                                          too_high_sorted[i][1])

                if not too_low.shape and not too_high.shape:
                    file.info('Values are within valid range (%.2E to %.2E).', valid_min, valid_max)

            else:
                file.info('No min and/or max definition found for variable "%s".', variable_name)