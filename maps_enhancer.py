import os
import pandas as pd
import requests
from dotenv import load_dotenv
import logging
import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import json

# Set up logging with debug level
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('maps_enhancer.log'),
        logging.StreamHandler()
    ]
)

class MapsEnhancer:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Get API key
        self.api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        if not self.api_key:
            raise ValueError("Google Maps API key not found in .env file")
        
        # API endpoint
        self.places_api_url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
        
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL without www and common prefixes"""
        if not url:
            return ""
        try:
            # Add http:// if no protocol specified
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
            
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception as e:
            logging.error(f"Error parsing URL {url}: {str(e)}")
            return ""
    
    def _clean_org_name(self, org_name: str) -> str:
        """Clean up organization name"""
        org_name = org_name.strip()
        # Remove common business suffixes
        suffixes = r'\s*(LLC|Inc|Corporation|Corp|Ltd|Limited|Co|Company|Group|Holdings|Services)\.?\s*$'
        org_name = re.sub(suffixes, '', org_name, flags=re.IGNORECASE)
        # Remove special characters
        org_name = re.sub(r'[^\w\s-]', ' ', org_name)
        # Remove extra whitespace
        org_name = ' '.join(org_name.split())
        return org_name
    
    def _compare_websites(self, website1: str, website2: str) -> bool:
        """Compare two website URLs by their domain"""
        try:
            domain1 = self._get_domain(website1)
            domain2 = self._get_domain(website2)
            return domain1 and domain2 and domain1 == domain2
        except Exception as e:
            logging.error(f"Error comparing websites: {str(e)}")
            return False

    def _get_operating_hours(self, opening_hours: dict) -> tuple:
        """Extract weekday closing time and weekend operation status"""
        if not opening_hours or 'periods' not in opening_hours:
            return None, None
        
        # Initialize variables
        weekday_close = None
        saturday_open = False
        sunday_open = False
        
        # Get weekday closing time (using Monday-Friday)
        for day in range(1, 6):  # Monday is 1, Friday is 5
            for period in opening_hours['periods']:
                if period.get('open', {}).get('day') == day and 'close' in period:
                    close_time = period['close']['time']
                    weekday_close = f"{close_time[:2]}:{close_time[2:]}"
                    break
            if weekday_close:  # If we found a closing time, stop checking other days
                break
        
        # Check weekend operation
        for period in opening_hours['periods']:
            if period.get('open', {}).get('day') == 6:  # Saturday
                saturday_open = True
            elif period.get('open', {}).get('day') == 0:  # Sunday
                sunday_open = True
        
        # Determine weekend status
        if saturday_open and sunday_open:
            weekend_status = "Operational"
        elif saturday_open:
            weekend_status = "Sat"
        elif sunday_open:
            weekend_status = "Sun"
        else:
            weekend_status = "Not Operational"
        
        return weekday_close, weekend_status

    def search_place(self, org_name: str, location: str, target_url: str) -> Optional[Dict[str, Any]]:
        """
        Search for a place using organization name and location using the Places API.
        Returns the matched place details or None if no match found.
        """
        try:
            # Clean organization name
            org_name = self._clean_org_name(org_name)
            
            # Create search query
            search_query = f"{org_name} {location} USA".strip()
            logging.debug(f"Search query: {search_query}")
            
            # Prepare request parameters
            params = {
                'query': search_query,
                'key': self.api_key
            }
            
            # Make API request
            logging.debug(f"Making API request to {self.places_api_url}")
            response = requests.get(self.places_api_url, params=params)
            logging.debug(f"API Response status: {response.status_code}")
            
            if response.status_code != 200:
                logging.error(f"API request failed: {response.text}")
                return None
            
            # Parse response
            result = response.json()
            logging.debug(f"Search API Response: {json.dumps(result, indent=2)}")
            
            if result.get('status') != 'OK' or not result.get('results'):
                logging.warning(f"No places found for query: {search_query}")
                return None
            
            # Get the first result
            place = result['results'][0]
            logging.info(f"Found place: {place.get('name')} with place_id: {place.get('place_id')}")
            
            # Get place details
            details_url = 'https://maps.googleapis.com/maps/api/place/details/json'
            details_params = {
                'place_id': place['place_id'],
                'key': self.api_key,
                'fields': 'name,formatted_phone_number,formatted_address,website,rating,user_ratings_total,reviews,opening_hours,business_status'
            }
            
            details_response = requests.get(details_url, params=details_params)
            if details_response.status_code == 200:
                details_result = details_response.json()
                logging.debug(f"Details API Response: {json.dumps(details_result, indent=2)}")
                if details_result.get('status') == 'OK':
                    place.update(details_result.get('result', {}))
                    return place
            
            return place
            
        except Exception as e:
            logging.error(f"Error searching for place {org_name}: {str(e)}")
            return None
    
    def process_csv(self, input_file: str, test_mode: bool = True):
        """
        Process the input CSV file and enhance it with Google Maps data.
        test_mode: If True, only process first 5 rows
        """
        try:
            # Read CSV file
            df = pd.read_csv(input_file)
            logging.info(f"Loaded CSV file with {len(df)} rows")
            
            # If in test mode, only process first 5 rows
            if test_mode:
                df = df.head(5)
                logging.info("Test mode: Processing first 5 rows only")
            
            # Initialize new columns
            new_columns = [
                'google_maps_link',
                'place_id',
                'formatted_address',
                'phone_number',
                'rating',
                'user_ratings_total',
                'website',
                'business_status',
                'weekday_closing',
                'weekend_status',
                'website_matched'
            ]
            for col in new_columns:
                df[col] = None
            
            # Process each row
            for idx, row in df.iterrows():
                org_name = row.get('organization_name', '')
                city = row.get('city', '')
                state = row.get('state', '')
                csv_website = row.get('organization_website_url', '')
                
                if pd.isna(org_name) or not org_name:
                    logging.warning(f"Skipping row {idx}: No organization name")
                    continue
                
                # Use city if available, otherwise use state
                location = city if pd.notna(city) and city else state
                if pd.isna(location) or not location:
                    logging.warning(f"Skipping row {idx}: No city or state available")
                    continue
                
                # Search for place
                place = self.search_place(org_name, location, csv_website)
                if place:
                    # Get operating hours
                    weekday_close, weekend_status = self._get_operating_hours(place.get('opening_hours', {}))
                    
                    # Compare websites
                    place_website = place.get('website', '')
                    website_matched = self._compare_websites(csv_website, place_website) if csv_website and place_website else False
                    
                    # Update DataFrame
                    df.at[idx, 'google_maps_link'] = f"https://www.google.com/maps/place/?q=place_id:{place['place_id']}"
                    df.at[idx, 'place_id'] = place['place_id']
                    df.at[idx, 'formatted_address'] = place.get('formatted_address')
                    df.at[idx, 'phone_number'] = place.get('formatted_phone_number')
                    df.at[idx, 'rating'] = place.get('rating')
                    df.at[idx, 'user_ratings_total'] = place.get('user_ratings_total')
                    df.at[idx, 'website'] = place_website
                    df.at[idx, 'business_status'] = place.get('business_status')
                    df.at[idx, 'weekday_closing'] = weekday_close
                    df.at[idx, 'weekend_status'] = weekend_status
                    df.at[idx, 'website_matched'] = website_matched
                    
                    # Print detailed information for this match
                    print(f"\nFound match for: {org_name}")
                    print(f"Place Name: {place.get('name')}")
                    print(f"Address: {place.get('formatted_address')}")
                    print(f"Phone: {place.get('formatted_phone_number')}")
                    print(f"Rating: {place.get('rating')} ({place.get('user_ratings_total')} reviews)")
                    print(f"Website: {place_website}")
                    print(f"CSV Website: {csv_website}")
                    print(f"Website Matched: {'Yes' if website_matched else 'No'}")
                    print(f"Business Status: {place.get('business_status')}")
                    print(f"Weekdays Closing: {weekday_close if weekday_close else 'Unknown'}")
                    print(f"Weekend: {weekend_status}")
                    print("-" * 80)
            
            # Save enhanced CSV
            output_file = 'enhanced_' + os.path.basename(input_file)
            df.to_csv(output_file, index=False)
            logging.info(f"Enhanced data saved to {output_file}")
            
        except Exception as e:
            logging.error(f"Error processing CSV file: {str(e)}")
            raise

def main():
    try:
        enhancer = MapsEnhancer()
        enhancer.process_csv('dataset.csv', test_mode=True)
    except Exception as e:
        logging.error(f"Application error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
