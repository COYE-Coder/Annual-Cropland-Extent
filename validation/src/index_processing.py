"""
This script provides functions for processing and validating land use in a directory of TIFF files.
Users can iterate over a set of image chips to determine the landcover type in the center of each chip.

The script includes the following main components:
1. Image processing functions: Functions for processing and validating land use in a directory of TIFF files.
2. Miscellaneous file management functions: Functions for creating and updating CSV files to store the processed data.
3. Directory and file management functions: Functions for creating date-based directories and writing data to CSV files.

Usage:
- Use the `process_directory` function to process a directory of TIFF files for land use validation.
- Use the `process_index` function to process a specific index within the directory and validate the landcover type.
- Use the `create_date_directory` function to create a date-based directory for storing the processed data.
- Use the `write_csv_to_master` function to write the processed data to a master CSV file.

Note: Make sure to provide the necessary arguments when calling the functions, such as the directory path,
geo_lookup dictionary, and CSV file paths.
"""

import os
import glob
import random
from datetime import datetime

import pandas as pd
import rasterio
import matplotlib.pyplot as plt
import numpy as np
from IPython.display import clear_output, display
import geemap
import ee
from rasterio.windows import Window

from .pass_image_collection import get_index_image, get_landsat_image
from .config import geolookup_list



# Image processing functions

def process_index(file_index: int, coords: list, geo_lookup: dict, directory: str,
                  completed_indices: list, existing_df: pd.DataFrame, year: int,
                  csv_file_path: str) -> tuple:
    """
    Processes a specific index within the directory and validates the landcover type.

    Args:
        file_index: The index of the file to process.
        coords: The geographic coordinates associated with the file index.
        geo_lookup: A dictionary mapping file indices to geographic coordinates.
        directory: The directory containing the TIFF files.
        completed_indices: A list of indices that have already been processed.
        existing_df: The existing DataFrame containing the processed data.
        year: The year associated with the file index.
        csv_file_path: The path to the CSV file where the results will be stored.

    Returns:
        A tuple containing a boolean indicating if processing is complete and the updated DataFrame.
    """
    user_input = ''
    note = ''

    print(f"Displaying file index {file_index} at {coords} in year {year}")

    window_size = (100, 100)  # The size of the window you want to display
    zoom_factor = 0.8  # The zoom factor (less than 1 to zoom in)

    # Create a figure with subplots
    fig, axs = plt.subplots(1, 3, dpi=100, figsize=(15, 15))

    # Iterate over the TIFF files associated with this index
    for i, suffix in enumerate(['falsecolor', 'index', 'truecolor']):
        filename = f'tile_{str(file_index).zfill(5)}_{year}_{suffix}.tif'

        if os.path.exists(os.path.join(directory, filename)):
            # Open the TIFF file
            with rasterio.open(os.path.join(directory, filename)) as src:
                # Calculate the center of the image
                center_x, center_y = src.width // 2, src.height // 2

                # Calculate the window bounds, centered around the image center
                half_win_width = (window_size[0] * zoom_factor) // 2
                half_win_height = (window_size[1] * zoom_factor) // 2
                win_x = center_x - half_win_width
                win_y = center_y - half_win_height
                win_width = 2 * half_win_width
                win_height = 2 * half_win_height

                # Define the window to read
                window = Window(win_x, win_y, win_width, win_height)

                # Read the data from the window
                img = src.read(window=window)

                # Stack bands together if necessary
                if img.ndim > 2:
                    img = np.dstack(img)

                img = img / np.max(img)

                # Display the image in the subplot
                axs[i].imshow(img)
                axs[i].set_title(suffix)
                # Plot the red dot at the center of the window
                red_dot_x = half_win_width
                red_dot_y = half_win_height
                axs[i].plot(red_dot_x, red_dot_y, 'ro')

                # After all images are processed but before plt.show()
                plt.tight_layout()

    # Show the figure with all subplots
    plt.show()

    # Keep asking until the user provides a valid landcover response or wants to go back
    while user_input not in ['ur', 'ag', 'na', 'exit', 'ag_u', 'ag_e']:
        user_input = input(f"What type of landcover is this for index {file_index}? \n (ur/ag/na/map/back/note/exit): ")

        if user_input == 'map':
            print("Displaying the map...")
            # Get the image
            index_image = get_index_image(year)
            landsat_image = get_landsat_image(year)

            # Create a map centered at the point
            m = geemap.Map(center=coords[::-1], zoom=11)

            # Define the region to display
            region = ee.Geometry.Point(coords).buffer(1024 * 30).bounds()

            # Add a high resolution basemap for extra information
            # Because we want to know the landcover at a given year, take this with a grain of salt
            m.add_basemap('HYBRID')

            # Add the images to the map
            m.addLayer(landsat_image.clip(region), {'bands': ['red', 'green', 'blue'], 'min': 0, 'max': 1}, 'TRUE COLOR')
            m.addLayer(landsat_image.clip(region), {'bands': ['nir', 'red', 'green'], 'min': 0, 'max': 1}, 'RED / BROWN FALSE COLOR IMAGE')
            m.addLayer(index_image.clip(region), {'bands': ['grayscale', 'ag_filter', 'savi'], 'gamma': 0.37}, 'GREEN / BLUE INDEX IMAGE')

            # Add a marker at the point
            m.addLayer(ee.Geometry.Point(coords), {'color': 'red'}, 'Point')

            # Add layer control
            m.addLayerControl()

            # Display the map
            display(m)

        elif user_input == 'note':
            # Prompt the user to enter their note
            note = input("Please enter your note: ")
            print(f"Note added for index {file_index}: {note}")

        if user_input == 'back':
            return False, existing_df  # Signal to go back

        if user_input == 'exit':
            print('======================================================')
            print('Exiting the program. Thank you for your service')
            print(r"""
               ****     ****
             **    ** **    **
            *       ***       *
            *      , ___,     *
            *      {O,o}     *
             *     |)__)    *
               *   -"-"   *
                 *       *
                    ***
                     *
            Owl be seeing you later!
            """)
            print('======================================================')
            print('======================================================')
            return None, existing_df

    file_index_year = f"{file_index}_{year}"
    # Update the DataFrame and CSV file
    if file_index_year in completed_indices:
        file_index = file_index_year.split('_')[0]
        # Update the existing entry
        existing_df.loc[existing_df['index'] == file_index, ['landcover', 'year', 'note']] = [user_input, year, note]
    else:
        # Add a new entry
        new_entry = {'index': file_index, 'coordinates': coords, 'landcover': user_input, 'year': year, 'note': note}
        existing_df = existing_df.append(new_entry, ignore_index=True)

    existing_df.to_csv(csv_file_path, index=False)
    clear_output(wait=True)
    return True, existing_df  # Return both the signal that processing is complete and the updated DataFrame


def process_directory(directory: str, geo_lookup: dict, csv_file_path: str = None,
                      master_csv_path: str = None) -> pd.DataFrame:
    """
    Processes a directory of TIFF files for land use validation.

    Args:
        directory: The directory containing the TIFF files.
        geo_lookup: A dictionary mapping file indices to geographic coordinates.
        csv_file_path: Optional; the path to the CSV file where results are stored.
        master_csv_path: Optional; the path to the master CSV file where all results are stored.

    Returns:
        The DataFrame containing the processed data.
    """

    # Set default CSV file path if not provided
    if csv_file_path is None:
        csv_file_path = os.path.join(directory, 'test_output.csv')

    # Ensure the CSV file exists
    if not os.path.exists(csv_file_path):
        df = pd.DataFrame(columns=['index', 'coordinates', 'landcover', 'year', 'note'])
        df.to_csv(csv_file_path, index=False)

    # Ensure the master CSV file exists
    if not os.path.exists(master_csv_path):
        master_df_empty = pd.DataFrame(columns=['index', 'coordinates', 'landcover', 'year', 'note', '_date'])
        master_df_empty.to_csv(master_csv_path, index=False)

    if master_csv_path:
        master_df = pd.read_csv(master_csv_path)

    existing_df = pd.read_csv(csv_file_path)
    completed_indices = [f'{x}_{y}' for x, y in zip(master_df['index'], master_df['year'])]

    # Get list of TIFF files in the directory
    files = [os.path.basename(x) for x in glob.glob(os.path.join(directory, '*.tif'))]

    # Extract unique identifiers
    # Because each unique ID corresponds to three different files,
    # we have to examine only the files that are unique
    unique_files = {}
    for file in files:
        # Extracting the identifier as 'tile_ID_YEAR'
        identifier = '_'.join(file.split('_')[:3])
        if identifier not in unique_files:
            unique_files[identifier] = file

    # Get a list of the unique files
    unique_file_list = list(unique_files.values())

    for filename in unique_file_list:
        print(f"Processing {filename}")
    # Shuffle the list
    random.shuffle(unique_file_list)

    user_input = ''  # Initialize user_input outside the loop

    for filename in unique_file_list:
        file_index = int(filename.split('_')[1])
        file_index_year = f"{filename.split('_')[1]}_{filename.split('_')[2]}"
        print(f'STARTING FILE INDEX {file_index}')

        year = filename.split('_')[2]
        coords = geo_lookup[file_index]

        # Skip indices that have already been completed unless we're going back to them
        if file_index_year not in completed_indices or user_input == 'back':
            clear_output(wait=True)

            process_result, existing_df = process_index(file_index, coords, geo_lookup, directory,
                                                        completed_indices, existing_df, int(year),
                                                        csv_file_path)
            completed_indices.append(file_index_year)

            if process_result is False:
                # If process_index returns False, the user wants to go back
                go_back_index_year = completed_indices[-1]
                try:
                    go_back_index = int(go_back_index_year.split('_')[0])
                    go_back_year = int(go_back_index_year.split('_')[1])
                    go_back_coords = geo_lookup[go_back_index]  # Retrieve the coordinates for the previous file index

                    completed_indices.remove(go_back_index_year)
                    existing_df = existing_df[existing_df['index'] != go_back_index]
                    process_result, existing_df = process_index(go_back_index, go_back_coords, geo_lookup, directory,
                                                                completed_indices, existing_df, go_back_year,
                                                                csv_file_path)
                    existing_df.to_csv(csv_file_path, index=False)
                    completed_indices.append(f'{file_index}_{year}')

                    user_input = 'done'
                except ValueError:
                    print("Invalid index. Please enter a numerical index.")
            elif process_result is None:
                print("Here is what you have accomplished this session:")
                print(existing_df)
                break
            else:
                user_input = ''  # Reset user_input for the next iteration
        else:
            continue  # Skip the completed index and continue to the next file

    # Optionally, return the DataFrame for further use
    return existing_df


# CSV file management functions

def write_csv_to_master(current_csv_path: str, master_csv_path: str) -> pd.DataFrame:
    """
    Writes the processed data from the current CSV file to the master CSV file.

    Args:
        current_csv_path: The path to the current CSV file containing the processed data.
        master_csv_path: The path to the master CSV file where all results are stored.

    Returns:
        The updated master DataFrame.
    """
    current_csv = pd.read_csv(current_csv_path)

    # Ensure the master CSV file exists
    if not os.path.exists(master_csv_path):
        df = pd.DataFrame(columns=['index', 'coordinates', 'landcover', 'year', 'note', '_date'])
        df.to_csv(master_csv_path, index=False)

    master_csv = pd.read_csv(master_csv_path)

    date = ('_').join(current_csv_path.split('/')[-2].split("_")[1:])

    current_csv['_date'] = date

    print(f"Storing results from {current_csv_path} to {master_csv_path}")

    # Deprecated in new pandas versions
    master_csv = master_csv.append(current_csv, ignore_index=True)
    master_csv.to_csv(master_csv_path, index=False)
    return master_csv


# Directory and file management functions

def create_date_directory(base_path: str, name: str) -> str:
    """
    Creates a date-based directory for storing the processed data.

    Args:
        base_path: The base path where the directory will be created.
        name: The name to be included in the directory name.

    Returns:
        The path to the created directory.
    """
    # Get the current date in YYYY-MM-DD format
    date_str = datetime.now().strftime('%Y-%m-%d')

    # Dir string
    dir_str = f'{name}_{date_str}'

    # Combine the base path with the date string to form the directory path
    dir_path = os.path.join(base_path, dir_str)

    # Create the directory if it doesn't already exist
    os.makedirs(dir_path, exist_ok=True)

    # Return the directory path
    return dir_path
