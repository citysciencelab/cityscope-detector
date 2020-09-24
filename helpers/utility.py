import json
import os

def get_folder_path():
    """
    gets the local folder
    return is as a string with '/' at the ednd
    """
    loc = str(os.path.realpath(
        os.path.join(os.getcwd()))) +"/"# .dirname(__file__)))) + '/'
    return loc

def parse_file(file, field):
    """
    get data from JSON settings files.

    Args:

    Returns the desired field
    """

    # open json file
    with open(file) as json_data:
        jd = json.load(json_data)

        # return item for this field
        return jd[field]
