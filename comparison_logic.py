import pandas as pd
import io
from datetime import datetime

# =============================================================================
# COMPARISON LOGIC FUNCTIONS
# =============================================================================

def compare_facility_names(raw_data_df, ingestion_df):
    """Compare Facility Name columns between raw data and ingestion files"""
    try:
        # Check if Facility Name column exists in raw data file
        if 'Facility Name' not in raw_data_df.columns:
            return {'error': 'Facility Name column not found in raw data file'}
        
        # Check for facility column in ingestion file (can be 'Facility Name' or 'Facility')
        ingestion_facility_col = None
        if 'Facility Name' in ingestion_df.columns:
            ingestion_facility_col = 'Facility Name'
        elif 'Facility' in ingestion_df.columns:
            ingestion_facility_col = 'Facility'
        else:
            return {'error': 'Neither Facility Name nor Facility column found in ingestion file'}
        
        # Get unique facility names from both files
        raw_facilities = set(raw_data_df['Facility Name'].dropna())
        ingestion_facilities = set(ingestion_df[ingestion_facility_col].dropna())
        
        # Find missing facilities
        missing_in_raw = ingestion_facilities - raw_facilities
        missing_in_ingestion = raw_facilities - ingestion_facilities
        
        return {
            'raw_facilities_count': len(raw_facilities),
            'ingestion_facilities_count': len(ingestion_facilities),
            'common_facilities_count': len(raw_facilities & ingestion_facilities),
            'missing_in_raw': list(missing_in_raw),
            'missing_in_ingestion': list(missing_in_ingestion),
            'missing_in_raw_count': len(missing_in_raw),
            'missing_in_ingestion_count': len(missing_in_ingestion)
        }
    except Exception as e:
        return {'error': f'Error comparing facility names: {str(e)}'}

def create_missing_facilities_excel(missing_facilities, filename="missing_facilities.xlsx"):
    """Create Excel file with missing facilities list"""
    try:
        # Create DataFrame with missing facilities
        df = pd.DataFrame({
            'Missing Facilities': missing_facilities,
            'Status': 'Not Found in Raw Data'
        })
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Missing Facilities', index=False)
            
            # Get the workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Missing Facilities']
            
            # Add some formatting
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            # Write header
            worksheet.write('A1', 'Missing Facilities', header_format)
            worksheet.write('B1', 'Status', header_format)
            
            # Set column widths
            worksheet.set_column('A:A', 30)
            worksheet.set_column('B:B', 20)
        
        output.seek(0)
        return output.getvalue()
    except Exception as e:
        return None

def compare_dataframes(raw_data_df, ingestion_df):
    """Compare raw data and ingestion DataFrames and return analysis results"""
    # Basic comparison info
    basic_info = {
        'raw_data_rows': len(raw_data_df),
        'ingestion_rows': len(ingestion_df),
        'raw_data_cols': len(raw_data_df.columns),
        'ingestion_cols': len(ingestion_df.columns),
        'common_columns': list(set(raw_data_df.columns) & set(ingestion_df.columns)),
        'raw_data_only_columns': list(set(raw_data_df.columns) - set(ingestion_df.columns)),
        'ingestion_only_columns': list(set(ingestion_df.columns) - set(raw_data_df.columns)),
        'row_difference': len(raw_data_df) - len(ingestion_df),
        'missing_in_ingestion': len(raw_data_df) - len(ingestion_df) if len(raw_data_df) > len(ingestion_df) else 0
    }
    
    # Facility name comparison
    facility_comparison = compare_facility_names(raw_data_df, ingestion_df)
    
    # Resource type identification
    resource_type = identify_resource_type(ingestion_df)
    ingestion_file_type = identify_ingestion_file_type(ingestion_df)
    
    # Resource-specific comparison (currently only GHG Emissions)
    resource_comparison = None
    if resource_type == 'GHG Emissions':
        resource_comparison = compare_ghg_emissions_data(raw_data_df, ingestion_df, ingestion_file_type)
    
    # Combine results
    result = {**basic_info, 'facility_comparison': facility_comparison}
    result['resource_type'] = resource_type
    result['ingestion_file_type'] = ingestion_file_type
    if resource_comparison:
        result['resource_comparison'] = resource_comparison
    
    return result

def create_duplicate_rows_excel(duplicate_df, filename="duplicate_rows.xlsx"):
    """Create Excel file with duplicate rows list"""
    try:
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            duplicate_df.to_excel(writer, sheet_name='Duplicate Rows', index=False)
            
            # Get the workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Duplicate Rows']
            
            # Add some formatting
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#FFE6E6',  # Light red background for duplicates
                'border': 1
            })
            
            # Write header with formatting
            for col_num, column in enumerate(duplicate_df.columns):
                worksheet.write(0, col_num, column, header_format)
            
            # Set column widths
            for col_num, column in enumerate(duplicate_df.columns):
                worksheet.set_column(col_num, col_num, 20)
        
        output.seek(0)
        return output.getvalue()
    except Exception as e:
        return None

def analyze_data_quality(raw_data_df, ingestion_df):
    """Analyze data quality issues in ingestion data only"""
    quality_issues = []
    duplicate_rows = None
    
    # Identify ingestion file type to determine which columns to check
    ingestion_type = identify_ingestion_file_type(ingestion_df)
    
    if ingestion_type == 'Monthly Data in Rows':
        # For Type 1: Check all columns except Quantity for null values
        columns_to_check = [col for col in ingestion_df.columns if col != 'Quantity']
        
        # Check for null values in all columns except Quantity
        for col in columns_to_check:
            null_count = ingestion_df[col].isnull().sum()
            if null_count > 0:
                quality_issues.append(f"Ingestion data has {null_count} null values in '{col}' column")
        
        # Check for duplicates (all columns except Quantity)
        duplicate_columns = [col for col in ingestion_df.columns if col != 'Quantity']
        duplicates = ingestion_df.duplicated(subset=duplicate_columns).sum()
        if duplicates > 0:
            quality_issues.append(f"Ingestion data has {duplicates} duplicate rows (same values in all columns except Quantity)")
            # Get the actual duplicate rows
            duplicate_rows = ingestion_df[ingestion_df.duplicated(subset=duplicate_columns, keep=False)]
    
    elif ingestion_type == 'Monthly Data in Columns':
        # For Type 2: Check all columns except month columns for null values
        # Month columns are like Apr-24, May-24, etc.
        month_columns = [col for col in ingestion_df.columns if any(month in col for month in ['Apr-24', 'May-24', 'Jun-24', 'Jul-24', 'Aug-24', 'Sep-24', 'Oct-24', 'Nov-24', 'Dec-24', 'Jan-25', 'Feb-25'])]
        columns_to_check = [col for col in ingestion_df.columns if col not in month_columns]
        
        # Check for null values in all columns except month columns
        for col in columns_to_check:
            null_count = ingestion_df[col].isnull().sum()
            if null_count > 0:
                quality_issues.append(f"Ingestion data has {null_count} null values in '{col}' column")
        
        # Check for duplicates (all columns except month columns)
        duplicate_columns = [col for col in ingestion_df.columns if col not in month_columns]
        duplicates = ingestion_df.duplicated(subset=duplicate_columns).sum()
        if duplicates > 0:
            quality_issues.append(f"Ingestion data has {duplicates} duplicate rows (same values in all columns except month columns)")
            # Get the actual duplicate rows
            duplicate_rows = ingestion_df[ingestion_df.duplicated(subset=duplicate_columns, keep=False)]
    
    else:
        # For unknown types, check all columns for null values
        for col in ingestion_df.columns:
            null_count = ingestion_df[col].isnull().sum()
            if null_count > 0:
                quality_issues.append(f"Ingestion data has {null_count} null values in '{col}' column")
        
        # Check for complete duplicates
        duplicates = ingestion_df.duplicated().sum()
        if duplicates > 0:
            quality_issues.append(f"Ingestion data has {duplicates} completely duplicate rows")
            # Get the actual duplicate rows
            duplicate_rows = ingestion_df[ingestion_df.duplicated(keep=False)]
    
    return {
        'quality_issues': quality_issues,
        'duplicate_rows': duplicate_rows
    }

def find_data_discrepancies(raw_data_df, ingestion_df):
    """Find specific data discrepancies between files"""
    discrepancies = []
    
    # This function can be expanded to find specific data differences
    # For now, it's a placeholder for future complex comparison logic
    
    return discrepancies

def identify_resource_type(ingestion_df):
    """Identify resource type based on column indicators in ingestion file"""
    try:
        # Check for GHG Emissions indicator (Scope column)
        if 'Scope' in ingestion_df.columns:
            return 'GHG Emissions'
        
        # Add other resource type indicators here as needed
        # if 'Water' in ingestion_df.columns:
        #     return 'Water'
        # if 'Waste' in ingestion_df.columns:
        #     return 'Waste'
        # if 'Activity' in ingestion_df.columns:
        #     return 'Activity Metrics'
        
        return 'Unknown'
    except Exception as e:
        return f'Error identifying resource type: {str(e)}'

def identify_ingestion_file_type(ingestion_df):
    """Identify the type of ingestion file based on column structure"""
    try:
        columns = list(ingestion_df.columns)
        
        # Monthly Data in Rows: Facility Name/Facility, Scope, Activity Type, Month, Year, Quantity, Unit, Resource Name
        type1_indicators = ['Scope', 'Activity Type', 'Month', 'Year', 'Quantity', 'Unit', 'Resource Name']
        
        # Monthly Data in Columns: Facility Name/Facility, Scope, Activity Type, Resource, Apr-24, May-24, Jun-24, Jul-24, Aug-24, Sep-24, Oct-24, Nov-24, Dec-24, Jan-25, Feb-25, Units
        type2_indicators = ['Scope', 'Activity Type', 'Resource', 'Units']
        
        # Check for facility column (either Facility Name or Facility)
        has_facility = 'Facility Name' in columns or 'Facility' in columns
        
        # Check for Monthly Data in Rows (monthly data with Month/Year columns)
        if has_facility and all(col in columns for col in type1_indicators):
            return 'Monthly Data in Rows'
        
        # Check for Monthly Data in Columns (monthly columns structure)
        if has_facility and all(col in columns for col in type2_indicators):
            # Check if there are month columns (Apr-24, May-24, etc.)
            month_columns = [col for col in columns if any(month in col for month in ['Apr-24', 'May-24', 'Jun-24', 'Jul-24', 'Aug-24', 'Sep-24', 'Oct-24', 'Nov-24', 'Dec-24', 'Jan-25', 'Feb-25'])]
            if len(month_columns) >= 3:  # At least 3 month columns
                return 'Monthly Data in Columns'
        
        return 'Unknown'
    except Exception as e:
        return f'Error identifying ingestion file type: {str(e)}'

def map_ghg_emissions_data(raw_data_df, ingestion_df, ingestion_type):
    """Map GHG Emissions data points between raw data and ingestion files"""
    try:
        if ingestion_type == 'Monthly Data in Rows':
            # For Monthly Data in Rows, we need to match on: Facility Name, Resource Name, Month, Year
            # and compare Quantity values
            
            # Get the facility column name for ingestion (could be 'Facility Name' or 'Facility')
            ingestion_facility_col = 'Facility Name' if 'Facility Name' in ingestion_df.columns else 'Facility'
            
            # Create comparison results
            comparison_results = []
            matched_rows = 0
            unmatched_ingestion_rows = 0
            quantity_matches = 0
            quantity_mismatches = 0
            
            # Iterate through each row in ingestion file
            for idx, ingestion_row in ingestion_df.iterrows():
                facility_name = ingestion_row[ingestion_facility_col]
                resource_name = ingestion_row['Resource Name']
                month = ingestion_row['Month']
                year = ingestion_row['Year']
                ingestion_quantity = ingestion_row['Quantity']
                
                # Find matching row in raw data
                raw_match = raw_data_df[
                    (raw_data_df['Facility Name'] == facility_name) &
                    (raw_data_df['Resource Name'] == resource_name) &
                    (raw_data_df['Month'] == month) &
                    (raw_data_df['Year'] == year)
                ]
                
                if not raw_match.empty:
                    matched_rows += 1
                    raw_quantity = raw_match.iloc[0]['Quantity']
                    
                    # Compare quantities
                    if raw_quantity == ingestion_quantity:
                        quantity_matches += 1
                        match_status = 'Match'
                    else:
                        quantity_mismatches += 1
                        match_status = 'Mismatch'
                    
                    comparison_results.append({
                        'facility_name': facility_name,
                        'resource_name': resource_name,
                        'month': month,
                        'year': year,
                        'raw_quantity': raw_quantity,
                        'ingestion_quantity': ingestion_quantity,
                        'difference': raw_quantity - ingestion_quantity,
                        'match_status': match_status
                    })
                else:
                    unmatched_ingestion_rows += 1
                    comparison_results.append({
                        'facility_name': facility_name,
                        'resource_name': resource_name,
                        'month': month,
                        'year': year,
                        'raw_quantity': None,
                        'ingestion_quantity': ingestion_quantity,
                        'difference': None,
                        'match_status': 'No Match in Raw Data'
                    })
            
            return {
                'ingestion_type': 'Monthly Data in Rows',
                'total_ingestion_rows': len(ingestion_df),
                'matched_rows': matched_rows,
                'unmatched_rows': unmatched_ingestion_rows,
                'quantity_matches': quantity_matches,
                'quantity_mismatches': quantity_mismatches,
                'comparison_results': comparison_results
            }
            
        elif ingestion_type == 'Monthly Data in Columns':
            # Monthly Data in Columns implementation will be added later
            return {
                'ingestion_type': 'Monthly Data in Columns',
                'status': 'Monthly Data in Columns mapping ready for implementation'
            }
        else:
            return {'error': f'Unknown ingestion file type: {ingestion_type}'}
            
    except Exception as e:
        return {'error': f'Error mapping GHG emissions data: {str(e)}'}

def compare_ghg_emissions_data(raw_data_df, ingestion_df, ingestion_type):
    """Compare GHG Emissions data points between raw data and ingestion files"""
    try:
        # Perform the actual comparison
        mapping_result = map_ghg_emissions_data(raw_data_df, ingestion_df, ingestion_type)
        if 'error' in mapping_result:
            return mapping_result
        
        return {
            'resource_type': 'GHG Emissions',
            'ingestion_type': ingestion_type,
            'comparison_status': 'Completed',
            'mapping': mapping_result
        }
        
    except Exception as e:
        return {'error': f'Error comparing GHG emissions data: {str(e)}'}

def generate_comparison_report(raw_data_df, ingestion_df):
    """Generate comprehensive comparison report"""
    report = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'basic_comparison': compare_dataframes(raw_data_df, ingestion_df),
        'data_quality_issues': analyze_data_quality(raw_data_df, ingestion_df),
        'discrepancies': find_data_discrepancies(raw_data_df, ingestion_df)
    }
    
    return report
