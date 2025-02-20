# Product Requirements Document (PRD) - Google Maps Lead Enhancer

## 1. Overview
The goal of this project is to develop a command-line tool that processes a CSV file containing lead data (including company name and website URL) and enhances it using data from the Google Maps API. The tool will use the company name as the primary search query via the Google Places API and use the website URL as a secondary validation check to confirm the correct location. For each lead, the tool will search up to three results until a match is found. For a matched company, it will extract the Google Maps link, closing time, weekend operating status, business category, and identify a competitor in the same area that is open 24 hours.

**Testing Strategy:**  
- **Initial Phase:** Process only the first 5 rows of the CSV file for testing purposes.  
- **Final Phase:** Once confirmed working, extend processing to all rows in the CSV file.

## 2. Key Requirements

### CSV File Ingestion
- **Input Source:**  
  - The tool will read a CSV file placed in the project folder containing at least the following columns:
    - Company Name
    - Website URL
- **Processing:**  
  - Parse the CSV using a library (e.g., Pandas) to extract and iterate through each lead.
  - **Initial Testing:** Process only the first 5 rows.
  - **Full Deployment:** Update the tool to process all rows after successful testing.

### Google Maps API Integration and Matching
- **Primary Search Query:**  
  - Use the company name as the search query in the Google Places API.
- **Secondary Validation:**  
  - Validate the search results by comparing the website URL from the CSV with the website URL (or relevant data) from the Google Maps result.
  - Evaluate up to three search results per lead:
    - If a result’s website URL matches (or is highly similar to) the CSV value, consider it a match.
    - If no match is found within three attempts, mark the lead as unmatched.

### Data Extraction from Google Maps
- **For Matched Companies:**
  - **Google Maps Link:** Extract and record the direct Google Maps URL.
  - **Closing Time:** Retrieve the closing time from the business hours.
  - **Weekend Status:** Determine whether the business is open on weekends.
  - **Business Category:** Extract the primary business category as listed.
  - **Competitor Identification:**  
    - Search for competitors in the same geographic area and business category.
    - Identify at least one competitor that is open 24 hours.
    - Record the competitor's name and Google Maps link.

### Output Generation & Error Handling
- **Enhanced CSV File:**  
  - Generate an output CSV file that includes the original columns plus the following new columns:
    - Google Maps Link
    - Closing Time
    - Weekend Open Status (Yes/No)
    - Business Category
    - 24-Hour Competitor Name
    - 24-Hour Competitor Google Maps Link
- **Error Logging:**  
  - Log any errors or records that cannot be processed or matched.
  - Ensure that API errors or missing data do not halt the entire process.

## 3. Development Roadmap

### Phase 1. **CSV Ingestion:**
   - Implement CSV reading using Pandas.
   - Configure the script to process only the first 5 rows of the CSV file.
### Phase 2. **Google Maps API Integration:**
   - Integrate with the Google Places API using the company name as the search query.
   - Retrieve up to three search results for each lead.
### Phase 3. **Matching Logic:**
   - Implement logic to validate each search result using the website URL from the CSV.
   - Determine if the result is a valid match based on URL similarity.
### Phase 4. **Data Extraction:**
   - For a matched company, extract the following details:
     - Direct Google Maps link.
     - Business closing time.
     - Weekend operating status.
     - Primary business category.
### Phase 5. **Competitor Identification:**
   - Use the business category and geographic data to search for competitors.
   - Identify at least one competitor that is open 24 hours and extract its name and Google Maps link.
### Phase 6. **Output Generation & Logging:**
   - Generate an enhanced CSV file for the 5 rows, appending the new columns.
   - Implement error handling and logging to capture any issues during processing.

### Phase 7. Full Deployment for All Rows
1. Update the CSV ingestion logic to process all rows in the CSV file.
2. Optimize performance and API usage for larger datasets.
3. Re-run the matching, data extraction, and competitor identification processes for the complete lead list.
4. Generate the final enhanced CSV file with complete data.
5. Finalize error handling and logging mechanisms.

## 4. Technical Stack Recommendations
- **Programming Language:** Python 3.9
- **CSV Processing:** Pandas library
- **Google Maps API Integration:** Google Places API using the official Python client (`googlemaps` library)
- **Logging:** Python’s built-in logging module
- **Deployment:** Run as a command-line tool on a dedicated system (self-hosted)
- **Environment:** Ubuntu-based server

## 5. Success Criteria
- **Functionality:**  
  - The tool successfully reads and processes the CSV file from the project folder.
  - For each lead, it searches using the company name and validates the result with the website URL.
  - The tool correctly evaluates up to three search results per lead and extracts the necessary details upon a match.
  - Competitor information (name and Google Maps link) is correctly identified for matched companies.
- **Testing:**  
  - During the initial phase, processing the first 5 rows produces accurate and enhanced data.
  - After testing, the tool processes all rows without significant performance issues.
- **Output:**  
  - An enhanced CSV file is generated with the new data columns appended to the original data.
- **Reliability:**  
  - The system handles errors gracefully and logs issues without stopping the process.
- **Performance:**  
  - The tool efficiently processes the CSV file while minimizing API calls by limiting the search results to three per lead.

---

This PRD outlines the development plan for enhancing a lead list using the Google Maps API, with an initial test phase processing only 5 rows and a final phase processing all rows. Please review and confirm if any adjustments are needed before proceeding with implementation.
