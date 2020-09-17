def check_3d(file):
    crop = file.specifiers.get('crop')
    irrigation = file.specifiers.get('irrigation')
    pft = file.specifiers.get('pft')

    file.variable_name = file.specifiers.get('variable')
    if crop:
        file.variable_name = file.variable_name + '-' + file.specifiers.get('crop')
    if irrigation:
        file.variable_name = file.variable_name + '-' + file.specifiers.get('irrigation')
    if pft:
        file.variable_name = file.variable_name + '-' + file.specifiers.get('pft')

    variable = file.dataset.variables.get(file.variable_name)
    dim_len = len(variable.dimensions)

    # detect 2d or 3d data
    if dim_len == 3:
        file.is_2d = True
    elif dim_len == 4:
        file.is_3d = True
        file.dim_vertical = variable.dimensions[1]

