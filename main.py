
import matplotlib
matplotlib.use('Agg')

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from census import Census
import googlemaps
from googlemaps.exceptions import ApiError
import sys
import time
import concurrent.futures

# --- CONFIGURATION ---
# WARNING: It is strongly recommended to regenerate these keys after use to protect your accounts.

# 1. U.S. Census Bureau API Key
CENSUS_API_KEY = "INSERT_HERE"

# 2. Google Maps API Key (with "Places API" enabled)
GOOGLE_MAPS_API_KEY = "INSERT_HERE"

# 3. Path to the unzipped Georgia census tract .shp file
GEORGIA_TRACT_SHAPEFILE_PATH = "path/to/.shp"

# --- Constants & Analysis Parameters ---
STATE_FIPS = '13'  # FIPS code for Georgia
COUNTY_FIPS = '067'  # FIPS code for Cobb County
OUTPUT_CSV_FILE = 'laundromat_opportunity_analysis_cobb_county.csv'
OUTPUT_MAP_FILE = 'opportunity_map.png'  # Filename for the output map image
LAUNDROMAT_SEARCH_RADIUS_METERS = 1609  # 1 mile, for proximity analysis


def fetch_demographic_data(api_key, state_fips, county_fips):
    """
    Fetches comprehensive demographic data from the US Census Bureau API.
    This includes total population, renter-occupied units, and median household income.
    """
    print("-> Starting: Fetching demographic data from U.S. Census Bureau...")
    try:
        c = Census(api_key)
        # Define the variables we want from the American Community Survey (ACS) 5-Year data
        # B01003_001E: Total Population
        # B25003_003E: Renter-Occupied Housing Units
        # B19013_001E: Median Household Income
        census_variables = ('NAME', 'B01003_001E', 'B25003_003E', 'B19013_001E')

        census_data = c.acs5.get(
            census_variables,
            {'for': f'tract:*', 'in': f'state:{state_fips} county:{county_fips}'}
        )

        if not census_data:
            print("Error: No data returned from Census API. Please check your API key and FIPS codes.")
            return None

        # Convert to DataFrame and rename columns for clarity
        df = pd.DataFrame(census_data)
        df = df.rename(columns={
            "B01003_001E": "total_population",
            "B25003_003E": "renter_occupied_units",
            "B19013_001E": "median_household_income",
            "NAME": "tract_name",
            "state": "STATEFP", "county": "COUNTYFP", "tract": "TRACTCE"
        })

        # Create a unique GEOID for merging with shapefile data
        df['GEOID'] = df['STATEFP'] + df['COUNTYFP'] + df['TRACTCE']

        # Convert data types for calculation, handling potential missing values
        for col in ['total_population', 'renter_occupied_units', 'median_household_income']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        print(f"-> Success: Fetched demographics for {len(df)} census tracts.")
        return df

    except Exception as e:
        print(f"Error during Census API call: {e}")
        return None


def fetch_laundromats(api_key):
    """
    Fetches all laundromat locations within Cobb County from the Google Maps Places API.
    Handles pagination to retrieve all available results.
    """
    print("-> Starting: Fetching laundromat locations from Google Maps API...")
    try:
        gmaps = googlemaps.Client(key=api_key)
        query = "laundromat in Cobb County, GA"

        all_laundromats = []
        response = gmaps.places(query=query)

        while True:
            for place in response.get('results', []):
                loc = place.get('geometry', {}).get('location', {})
                if loc:
                    all_laundromats.append({
                        'name': place.get('name'),
                        'address': place.get('formatted_address'),
                        'lat': loc.get('lat'),
                        'lng': loc.get('lng')
                    })

            # Check for a token to get the next page of results
            next_page_token = response.get('next_page_token')
            if next_page_token:
                time.sleep(2)  # Google requires a delay before fetching the next page
                response = gmaps.places(query=query, page_token=next_page_token)
            else:
                break

        print(f"-> Success: Found {len(all_laundromats)} laundromats.")
        return pd.DataFrame(all_laundromats)

    except ApiError as e:
        print(f"Error during Google Maps API call: {e.reason}")
        print(
            "-> Please check your Google Maps API key, ensure the 'Places API' is enabled, and that billing is set up.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred with the Google Maps API: {e}")
        return None


def perform_geospatial_analysis(demographics_df, laundromats_df, shapefile_path, county_fips):
    """
    Combines all data to perform a detailed analysis and calculate an opportunity score.
    """
    print("\nStep 2/4: Performing geospatial analysis...")
    try:
        # Load the Georgia census tract shapefile
        ga_tracts_gdf = gpd.read_file(shapefile_path)
    except Exception as e:
        print(f"Fatal Error: Could not load shapefile from '{shapefile_path}'.\nPlease check the path. Details: {e}")
        return None

    # Filter for Cobb County and merge with our demographic data
    cobb_tracts_gdf = ga_tracts_gdf[ga_tracts_gdf['COUNTYFP'] == county_fips].copy()
    analysis_gdf = cobb_tracts_gdf.merge(demographics_df, on='GEOID', how='left')

    # --- Data Cleaning and Feature Engineering ---
    # Calculate renter percentage and handle division by zero
    analysis_gdf['renter_percentage'] = (analysis_gdf['renter_occupied_units'] / analysis_gdf[
        'total_population']).fillna(0) * 100

    # Calculate population density (people per square meter)
    # Project to a CRS with meters as units (like EPSG:3857) to calculate area accurately
    analysis_gdf['population_density'] = analysis_gdf['total_population'] / analysis_gdf.to_crs('EPSG:3857').area

    # --- Proximity Analysis for Laundromats ---
    if laundromats_df is not None and not laundromats_df.empty:
        # Convert laundromats to a GeoDataFrame
        laundromats_gdf = gpd.GeoDataFrame(
            laundromats_df,
            geometry=gpd.points_from_xy(laundromats_df.lng, laundromats_df.lat),
            crs=analysis_gdf.crs
        )

        # Create a 1-mile buffer around each census tract
        tract_buffers = analysis_gdf.copy()
        tract_buffers['geometry'] = tract_buffers.to_crs('EPSG:3857').buffer(LAUNDROMAT_SEARCH_RADIUS_METERS).to_crs(
            analysis_gdf.crs)

        # Spatially join the buffered tracts with the laundromat locations
        laundromats_nearby = gpd.sjoin(tract_buffers, laundromats_gdf, how="left", predicate="contains")

        # Count laundromats within the buffer of each tract
        laundromat_count = laundromats_nearby.groupby('GEOID').size().reset_index(name='laundromats_within_1_mile')
        analysis_gdf = analysis_gdf.merge(laundromat_count, on='GEOID', how='left')
    else:
        analysis_gdf['laundromats_within_1_mile'] = 0

    analysis_gdf['laundromats_within_1_mile'] = analysis_gdf['laundromats_within_1_mile'].fillna(0).astype(int)

    # --- Calculate the Opportunity Score ---
    # Normalize each factor to a 0-1 scale to ensure fair weighting
    analysis_gdf['renter_score'] = (analysis_gdf['renter_percentage'] / analysis_gdf['renter_percentage'].max()).fillna(
        0)
    analysis_gdf['income_score'] = (
                1 - (analysis_gdf['median_household_income'] / analysis_gdf['median_household_income'].max())).fillna(0)
    analysis_gdf['laundromat_score'] = (1 - (
                analysis_gdf['laundromats_within_1_mile'] / analysis_gdf['laundromats_within_1_mile'].max())).fillna(0)
    analysis_gdf['density_score'] = (
                analysis_gdf['population_density'] / analysis_gdf['population_density'].max()).fillna(0)

    # Define weights for each factor in the final score
    weights = {'renter': 0.40, 'laundromat': 0.30, 'income': 0.20, 'density': 0.10}

    # Calculate the weighted average score and scale it to 100
    analysis_gdf['opportunity_score'] = (
                                                analysis_gdf['renter_score'] * weights['renter'] +
                                                analysis_gdf['laundromat_score'] * weights['laundromat'] +
                                                analysis_gdf['income_score'] * weights['income'] +
                                                analysis_gdf['density_score'] * weights['density']
                                        ) * 100

    print("-> Success: Analysis complete.")
    return analysis_gdf.sort_values(by='opportunity_score', ascending=False)


def generate_results_map(analysis_gdf):
    """
    Generates and saves a map visualizing the opportunity scores.
    This function now saves the file instead of displaying it to avoid Tkinter errors.
    """
    print("Step 4/4: Generating results map...")
    fig, ax = plt.subplots(1, 1, figsize=(15, 15))

    # Plot all tracts with a color gradient based on the opportunity score
    analysis_gdf.plot(
        column='opportunity_score',
        ax=ax,
        legend=True,
        cmap='YlOrRd',  # Yellow-Orange-Red colormap
        edgecolor='black',
        linewidth=0.3,
        legend_kwds={'label': "Opportunity Score (0-100)", 'orientation': "horizontal"}
    )

    ax.set_title('Laundromat Opportunity Score for Cobb County, GA', fontsize=20)
    ax.set_xticks([])
    ax.set_yticks([])

    # Save the figure to a file instead of showing it on screen.
    plt.savefig(OUTPUT_MAP_FILE, dpi=300, bbox_inches='tight')
    print(f"-> Success: Map saved as '{OUTPUT_MAP_FILE}'. You can now open this image file.")


def main():
    """Main function to orchestrate the analysis."""

    demographics_df = None
    laundromats_df = None

    # --- Step 1: Fetch Data in Parallel using Threading ---
    print("Step 1/4: Fetching data from APIs using threading...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_census = executor.submit(fetch_demographic_data, CENSUS_API_KEY, STATE_FIPS, COUNTY_FIPS)
        future_gmaps = executor.submit(fetch_laundromats, GOOGLE_MAPS_API_KEY)
        demographics_df = future_census.result()
        laundromats_df = future_gmaps.result()

    if demographics_df is None:
        print("\nHalting execution due to failure in fetching Census data.")
        sys.exit(1)

    # --- Steps 2 & 3: Analysis and Reporting ---
    final_analysis = perform_geospatial_analysis(demographics_df, laundromats_df, GEORGIA_TRACT_SHAPEFILE_PATH,
                                                 COUNTY_FIPS)

    if final_analysis is None:
        print("\nHalting execution due to analysis failure.")
        sys.exit(1)

    print("\n--- Top 15 Census Tracts by Opportunity Score ---")
    output_cols = [
        'tract_name', 'opportunity_score', 'renter_percentage',
        'median_household_income', 'laundromats_within_1_mile', 'total_population'
    ]
    # Create a temporary dataframe for formatted printing
    display_df = final_analysis.copy()
    display_df['opportunity_score'] = display_df['opportunity_score'].map('{:,.1f}'.format)
    display_df['renter_percentage'] = display_df['renter_percentage'].map('{:,.1f}%'.format)
    display_df['median_household_income'] = display_df['median_household_income'].map('${:,.0f}'.format)
    print(display_df[output_cols].head(15).to_string())

    # Save the full, unformatted data to a CSV file
    print(f"\nStep 3/4: Saving detailed results to '{OUTPUT_CSV_FILE}'...")
    try:
        # We use the original 'final_analysis' dataframe here to save raw numbers
        final_analysis.drop(columns='geometry').to_csv(OUTPUT_CSV_FILE, index=False)
        print("-> Success: Data saved.")
    except Exception as e:
        print(f"Error saving file: {e}")

    # --- Step 4: Visualization ---
    generate_results_map(final_analysis)


if __name__ == '__main__':
    main()
