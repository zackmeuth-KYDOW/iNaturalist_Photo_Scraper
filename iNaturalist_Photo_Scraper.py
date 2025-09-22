import requests
import os
import time
import csv
import json
import re

# --- CONFIGURATION ---
# Set the name of the base folder where all scientific name folders will be created.
BASE_OUTPUT_DIR = "inaturalist_photos"
# --- END CONFIGURATION ---


def get_observation_data_from_csv(filepath):
    """
    Reads a CSV, finds the 'url' and 'scientific_name' columns by their headers,
    and returns a list of dictionaries containing the data.
    """
    observation_data = []
    try:
        # Use 'utf-8-sig' to handle potential BOM (Byte Order Mark) from Excel exports
        with open(filepath, mode='r', newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            try:
                # Read header, trim whitespace, and convert to lowercase for robust matching
                header = [h.strip().lower() for h in next(reader)]
            except StopIteration:
                print("❌ ERROR: The CSV file is empty.")
                return None

            # Find the column index for 'url' and 'scientific_name'
            try:
                url_col_index = header.index('url')
                name_col_index = header.index('scientific_name')
            except ValueError as e:
                print(f"❌ ERROR: Missing required column in CSV: {e}. Please ensure columns 'url' and 'scientific_name' exist.")
                return None
            
            # Process remaining rows
            for row in reader:
                # Ensure row has enough columns to prevent index errors
                if row and len(row) > max(url_col_index, name_col_index):
                    url = row[url_col_index].strip()
                    scientific_name = row[name_col_index].strip()
                    # Add to list only if the url and scientific name are not empty
                    if url.startswith("http") and scientific_name:
                        observation_data.append({
                            "url": url,
                            "scientific_name": scientific_name
                        })

    except FileNotFoundError:
        print(f"❌ ERROR: The file was not found at the path: {filepath}")
        return None
    except Exception as e:
        print(f"❌ ERROR: An error occurred while reading the CSV file: {e}")
        return None
        
    return observation_data


def download_inaturalist_photos_api(observation_data, base_output_dir):
    """
    Downloads photos using the API, organizing them into folders
    named after their scientific name.
    """
    if not observation_data:
        print("No valid data was found in the CSV to process.")
        return

    # Create the base output directory if it doesn't exist.
    if not os.path.exists(base_output_dir):
        os.makedirs(base_output_dir)
        print(f"Created base directory: '{base_output_dir}'")

    print(f"\nFound {len(observation_data)} observations to process.")
    
    for obs in observation_data:
        url = obs['url']
        scientific_name = obs['scientific_name']

        try:
            observation_id = url.strip('/').split('/')[-1]
            if not observation_id.isdigit():
                print(f"\n⚠️ Skipping invalid URL format: {url}")
                continue
            
            # Sanitize the scientific name to create a valid folder name
            # Replaces spaces with underscores and removes characters not allowed in filenames
            sanitized_name = re.sub(r'[\\/*?:"<>|]', "", scientific_name).replace(' ', '_')
            if not sanitized_name:
                sanitized_name = f"observation_{observation_id}" # Fallback name

            # Create the specific folder for this species inside the base directory
            species_folder_path = os.path.join(base_output_dir, sanitized_name)
            if not os.path.exists(species_folder_path):
                os.makedirs(species_folder_path)

            print(f"\nProcessing Obs ID: {observation_id} for '{scientific_name}'...")

            api_url = f"https://api.inaturalist.org/v1/observations/{observation_id}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()

            data = response.json()

            if not data or 'results' not in data or not data['results']:
                print(f"  --> No data returned from API for observation {observation_id}.")
                continue
            
            observation_details = data['results'][0]
            
            if 'photos' not in observation_details or not observation_details['photos']:
                 print(f"  --> No photos found for observation {observation_id}.")
                 continue
            
            photos = observation_details['photos']
            print(f"  Found {len(photos)} photo(s). Saving to '{species_folder_path}'")

            for i, photo in enumerate(photos):
                img_url = photo['url'].replace('square', 'large')
                filename = f"{observation_id}_{i+1}.jpg"
                filepath = os.path.join(species_folder_path, filename)

                print(f"  Downloading {filename}...")
                img_response = requests.get(img_url)
                img_response.raise_for_status()

                with open(filepath, 'wb') as f:
                    f.write(img_response.content)
            
            time.sleep(1)

        except requests.exceptions.HTTPError as e:
            print(f"  --> HTTP Error for {url}: {e}")
        except requests.exceptions.RequestException as e:
            print(f"  --> Network error for {url}: {e}")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  --> Could not parse API response for {url}. Error: {e}")
        except Exception as e:
            print(f"  --> An unexpected error occurred for {url}: {e}")

    print("\n✅ Download process complete!")


# --- Main execution block ---
if __name__ == "__main__":
    csv_path = input("Please enter the full path to your .csv file: ")

    if not os.path.exists(csv_path):
        print(f"❌ ERROR: No file exists at the path you provided.")
    else:
        # Get the observation data (URL and scientific name) from the CSV
        obs_data = get_observation_data_from_csv(csv_path)
        if obs_data:
            # Pass the data and the base directory to the download function
            download_inaturalist_photos_api(obs_data, BASE_OUTPUT_DIR)