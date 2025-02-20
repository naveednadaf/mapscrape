import os
import pandas as pd
import requests
from dotenv import load_dotenv
import logging
import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import json
from datetime import datetime

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
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.search_url = 'https://places.googleapis.com/v1/places:searchText'
        self.details_url = 'https://places.googleapis.com/v1/places/'
        self.headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': self.api_key,
        }
        
    def _get_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception as e:
            logging.error(f"Error parsing URL {url}: {str(e)}")
            return None

    def _compare_websites(self, website1: str, website2: str) -> bool:
        """Compare two website URLs by their domain"""
        try:
            domain1 = self._get_domain(website1)
            domain2 = self._get_domain(website2)
            return domain1 and domain2 and domain1 == domain2
        except Exception as e:
            logging.error(f"Error comparing websites: {str(e)}")
            return False

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
    
    def _get_operating_hours(self, hours: dict) -> tuple:
        """Extract weekday closing time and weekend operation status"""
        if not hours or 'periods' not in hours:
            return None, None
        
        weekday_close = None
        saturday_open = False
        sunday_open = False
        
        # Get weekday closing time (using Monday-Friday)
        for day in range(1, 6):  # Monday is 1, Friday is 5
            for period in hours['periods']:
                if period.get('open', {}).get('day') == day and 'close' in period:
                    close = period['close']
                    weekday_close = f"{close['hour']:02d}:{close['minute']:02d}"
                    break
            if weekday_close:  # If we found a closing time, stop checking other days
                break
        
        # Check weekend operation
        for period in hours['periods']:
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

    def _make_search_request(self, query: str) -> dict:
        """Make a search request to Google Places API"""
        url = "https://places.googleapis.com/v1/places:searchText"
        
        headers = {
            **self.headers,
            'X-Goog-FieldMask': 'places.id,places.displayName,places.formattedAddress,places.websiteUri,'
                               'places.rating,places.userRatingCount,places.businessStatus,'
                               'places.regularOpeningHours,places.internationalPhoneNumber,places.primaryType'
        }
        
        data = {
            "textQuery": query,
            "languageCode": "en"
        }
        
        logging.debug(f"Making API request to {url}")
        response = requests.post(url, headers=headers, json=data)
        logging.debug(f"API Response status: {response.status_code}")
        logging.debug(f"Search API Response: {response.text}")
        
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"API request failed: {response.text}")
            return {}

    def process_csv(self, filename: str, test_mode: bool = False):
        """Process the CSV file and enrich with Google Places data"""
        try:
            df = pd.read_csv(filename)
            logging.info(f"Loaded CSV file with {len(df)} rows")
            
            if test_mode:
                logging.info("Test mode: Processing first 5 rows only")
                df = df.head()
            
            # Initialize new columns
            new_columns = [
                'google_maps_name',
                'address',
                'phone',
                'rating',
                'review_count',
                'google_maps_website',
                'website_matched',
                'business_status',
                'weekday_closing',
                'weekend_status',
                'primary_type'
            ]
            
            for col in new_columns:
                df[col] = None
            
            for index, row in df.iterrows():
                query = f"{row['organization_name']} {row['city']} USA"
                
                search_result = self._make_search_request(query)
                if not search_result or 'places' not in search_result:
                    continue
                
                place = search_result['places'][0]
                if not place:
                    continue
                
                # Extract place details
                place_name = place.get('displayName', {}).get('text', '')
                address = place.get('formattedAddress', '')
                phone = place.get('internationalPhoneNumber', '')
                rating = place.get('rating', '')
                review_count = place.get('userRatingCount', '')
                website = place.get('websiteUri', '')
                business_status = place.get('businessStatus', '')
                primary_type = place.get('primaryType', '')
                
                # Get operating hours
                weekday_close, weekend_status = self._get_operating_hours(place.get('regularOpeningHours', {}))
                
                # Update DataFrame
                df.at[index, 'google_maps_name'] = place_name
                df.at[index, 'address'] = address
                df.at[index, 'phone'] = phone
                df.at[index, 'rating'] = rating
                df.at[index, 'review_count'] = review_count
                df.at[index, 'google_maps_website'] = website
                df.at[index, 'website_matched'] = self._compare_websites(row['organization_website_url'], website)
                df.at[index, 'business_status'] = business_status
                df.at[index, 'weekday_closing'] = weekday_close
                df.at[index, 'weekend_status'] = weekend_status
                df.at[index, 'primary_type'] = primary_type
                
                print(f"\nFound match for: {row['organization_name']}")
                print(f"Address: {address}")
                print(f"Phone: {phone}")
                print(f"Rating: {rating} ({review_count} reviews)")
                print(f"Website: {website}")
                print(f"CSV Website: {row['organization_website_url']}")
                print(f"Website Matched: {df.at[index, 'website_matched']}")
                print(f"Business Status: {business_status}")
                print(f"Weekdays Closing: {weekday_close}")
                print(f"Weekend: {weekend_status}")
                print(f"Primary Type: {primary_type}")
                print("-" * 80)
            
            # Save enhanced CSV
            output_file = 'enhanced_' + os.path.basename(filename)
            try:
                df.to_csv(output_file, index=False)
                logging.info(f"Enhanced data saved to {output_file}")
            except PermissionError:
                alt_output_file = 'enhanced_data_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.csv'
                df.to_csv(alt_output_file, index=False)
                logging.info(f"Enhanced data saved to alternate file: {alt_output_file}")
            
        except Exception as e:
            logging.error(f"Error processing CSV file: {str(e)}")
            raise

def main():
    try:
        load_dotenv()
        api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        if not api_key:
            raise ValueError("Google Maps API key not found in .env file")
        
        enhancer = MapsEnhancer(api_key)
        enhancer.process_csv('dataset.csv', test_mode=True)
    except Exception as e:
        logging.error(f"Application error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
