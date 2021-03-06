import pickle
import app_config
import os
import torch
import math
from coil import Coil, derive_current


def make_outputs(n: int) -> torch.FloatTensor:
    """
    Make a numpy array of 6-dimension vector: (x, y, z, up_x, up_y, up_z).

    :param n: The number of items in the array.

    :return: An array of vectors.
    """
    if n <= 0:
        raise IndexError('The number of samples must exceed zero.')

    precision = int(math.ceil((n ** (1 / 6))))
    positions = []
    for x in range(precision + 1):
        for y in range(precision + 1):
            for z in range(precision + 1):
                positions.append([x, y, z])
    positions = positions[1:len(positions) - 1]
    positions.append((precision, precision, precision))
    positions = torch.FloatTensor(positions) / precision

    t = (positions - 0.5) * app_config.PREF_SPACE_SIZE
    for tt in t:
        print(tt)
    print(t.shape)

    data = []
    for pos in positions:
        for direction in positions:
            up = (direction - 0.5) * 2.0
            norm = torch.dot(up, up)
            datum = torch.cat([(pos - 0.5) * app_config.PREF_SPACE_SIZE, up / norm], dim=0).tolist()
            data.append(datum)

    print(torch.FloatTensor(data).shape)

    return torch.FloatTensor(data)


def generate_train_set(n: int,
                       first_order_coil: Coil,
                       second_order_coil: Coil,
                       delta_volt_per_seconds: float) -> list:
    """
    Randomly generate data set in case of a coil derives current
    to three other coils that orthogonally aligned in 3-dimensional space.

    :param n: The number of samples in data set.
    :param first_order_coil: The first-order coil that derives current.
    :param second_order_coil: The second-order coil derived by the first-order coil.
    :param delta_volt_per_seconds: The change of voltage in a second in volts.

    :return: The generated data set.
    """
    if n <= 0:
        raise IndexError('The number of samples must exceed zero.')

    # Deepcopy the first-order coil to translate and rotate.
    first = first_order_coil.__copy__()

    # Deepcopy the second-order coil in each three orthogonal directions.
    coil_x = Coil(second_order_coil.area, second_order_coil.num_wind, up_vector=torch.FloatTensor([1, 0, 0]))
    coil_y = Coil(second_order_coil.area, second_order_coil.num_wind, up_vector=torch.FloatTensor([0, 1, 0]))
    coil_z = Coil(second_order_coil.area, second_order_coil.num_wind, up_vector=torch.FloatTensor([0, 0, 1]))

    # Randomly generate the sample in range:
    inputs, outputs = [], make_outputs(n)
    for datum in outputs:
        first.position = datum[:3]
        first.up_vector = datum[3:]

        # Derive the three second-order coils and calculates the current.
        derived_x = -derive_current(first, coil_x, delta_voltage=delta_volt_per_seconds, delta_time=1)
        derived_y = -derive_current(first, coil_y, delta_voltage=delta_volt_per_seconds, delta_time=1)
        derived_z = -derive_current(first, coil_z, delta_voltage=delta_volt_per_seconds, delta_time=1)

        # Derived current as input
        inputs.append((derived_x, derived_y, derived_z))

    return [torch.FloatTensor(inputs), outputs]


def load_train_test_set() -> list:
    """
    Load train set and test set from the file.

    :return: The read data set as a list.
    """
    if not os.path.exists(app_config.PATH_DATA):
        raise FileNotFoundError('File doesn\'t exist:', app_config.PATH_DATA)

    with open(app_config.PATH_DATA, 'rb') as data_file:
        return pickle.load(data_file)
