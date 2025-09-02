Laundromat Market Opportunity Analyzer

This Python script performs a detailed market analysis to identify promising locations for a new laundromat in Cobb County, Georgia. It combines demographic data from the U.S. Census Bureau with business data from the Google Maps API to calculate a unique "Opportunity Score" for every census tract in the county.

The analysis pinpoints areas with favorable conditions for a laundry service, such as a high percentage of renters, lower median household income, high population density, and a low number of existing laundromats nearby.
Features

    Multi-threaded Data Fetching: Simultaneously retrieves data from the U.S. Census and Google Maps APIs for improved speed.

    Advanced Demographic Analysis: Gathers data on total population, renter-occupied households, and median household income to build a detailed profile of each area.

    Proximity-Based Competition Analysis: Instead of just counting laundromats within a tract, it identifies competitors within a realistic 1-mile buffer zone for a more accurate view of market saturation.

    Weighted Opportunity Score: Calculates a normalized score (0-100) for each census tract based on a weighted formula, making it easy to rank and compare locations.

    Rich Data Visualization: Generates a high-quality heatmap of Cobb County, where tracts are color-coded from yellow (low opportunity) to red (high opportunity) for an immediate visual understanding of market gaps.

    Detailed Reporting: Outputs the top 15 most promising locations to the console and saves a full, detailed analysis of all census tracts to a CSV file.

    Robust Error Handling: Includes checks for common issues like invalid API keys or missing files to guide the user.

How It Works

The script operates in four main steps:

    Fetch Data (in parallel):

        U.S. Census API: Retrieves tract-level data for total population, renter-occupied units, and median household income.

        Google Maps Places API: Searches for all businesses categorized as "laundromat" within Cobb County and fetches their geographic coordinates.

    Perform Geospatial Analysis:

        Loads a TIGER/Line shapefile for Georgia to get the geographic boundaries of each census tract.

        Merges the demographic data with the tract geometries.

        Creates a 1-mile buffer around each tract and performs a spatial join to count how many existing laundromats serve that area.

    Calculate Opportunity Score:

        For each census tract, it normalizes and scores four key factors:

            Renter Percentage: Higher is better.

            Median Household Income: Lower is better.

            Nearby Laundromats: Fewer is better.

            Population Density: Higher is better.

        It then calculates a final weighted score to rank each tract's potential.

    Generate Outputs:

        Prints a summary table of the top 15 locations to the console.

        Saves the complete dataset to a CSV file.

        Saves the color-coded opportunity map as a PNG image file.

Setup and Installation
1. Prerequisites

    Python 3.8 or newer.

    pip (Python package installer).

2. Install Required Libraries

Open your terminal or command prompt and run the following command to install all necessary Python packages:
code Bash
IGNORE_WHEN_COPYING_START
IGNORE_WHEN_COPYING_END

    
pip install pandas geopandas matplotlib census googlemaps

  

3. Acquire API Keys and Data

You will need to get three things:

    U.S. Census Bureau API Key:

        Request a free key from the Census Bureau's API request page. It will be sent to you via email.

    Google Maps API Key:

        Go to the Google Cloud Platform Console.

        Create a new project and enable the Places API.

        Create an API key. Note: You may need to enable billing on your Google Cloud account, but the Places API has a generous free tier.

    Census Tract Shapefile:

        Go to the Census Bureau's TIGER/Line Shapefiles page.

        Select the most recent year and choose "Census Tracts" as the layer type.

        Select "Georgia" and download the zip file.

        Unzip the file into a folder in your project directory (e.g., a folder named tract).

4. Configure the Script

Open the Python script (laundromat_analyzer.py) in an editor and update the following variables in the CONFIGURATION section at the top of the file:
code Python
IGNORE_WHEN_COPYING_START
IGNORE_WHEN_COPYING_END

    
# 1. U.S. Census Bureau API Key
CENSUS_API_KEY = "your_40_character_census_api_key_here"

# 2. Google Maps API Key (with "Places API" enabled)
GOOGLE_MAPS_API_KEY = "your_google_maps_api_key_here"

# 3. Path to the unzipped Georgia census tract .shp file
GEORGIA_TRACT_SHAPEFILE_PATH = "path/to/your/tl_2024_13_tract.shp"

  

Usage

Once the script is configured, run it from your terminal:
code Bash
IGNORE_WHEN_COPYING_START
IGNORE_WHEN_COPYING_END

    
python laundromat_analyzer.py

  

The script will print its progress to the console and, upon completion, you will find the output files in the same directory.
Output

After running, the script will produce three outputs:

    Console Output: A formatted table displaying the top 15 census tracts with the highest opportunity scores.
    code Code

    IGNORE_WHEN_COPYING_START
    IGNORE_WHEN_COPYING_END

        
    --- Top 15 Census Tracts by Opportunity Score ---
    # ... table with tract_name, opportunity_score, renter_percentage, etc. ...

      

    CSV Report (laundromat_opportunity_analysis_cobb_county.csv): A detailed CSV file containing the full analysis and calculated scores for all census tracts in Cobb County.

    Map Image (opportunity_map.png): A high-resolution PNG image showing a map of Cobb County, with each census tract color-coded according to its opportunity score.

<!-- It's good practice to include a placeholder or actual image of the output map -->
Security Notice

Warning: The API keys in the script are treated like passwords. Do not commit them to a public repository (like GitHub). For personal use, hardcoding them is acceptable, but for any shared project, you should use environment variables or a secrets management system to protect them. It is recommended to regenerate your keys if they are ever exposed.
