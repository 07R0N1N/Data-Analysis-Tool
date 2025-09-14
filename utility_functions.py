import streamlit as st
import pandas as pd
from comparison_logic import create_missing_facilities_excel

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def read_excel_file(file, sheet_name=None):
    """Read Excel file and return DataFrame"""
    try:
        if sheet_name:
            df = pd.read_excel(file, sheet_name=sheet_name)
        else:
            df = pd.read_excel(file)
        return df, None
    except Exception as e:
        return None, str(e)

def get_excel_sheets(file):
    """Get list of sheet names from Excel file"""
    try:
        excel_file = pd.ExcelFile(file)
        return excel_file.sheet_names, None
    except Exception as e:
        return None, str(e)

def identify_file_types(file1, file2, df1, df2):
    """Identify which file is raw data (larger) and which is ingestion (smaller)"""
    file1_size = file1.size
    file2_size = file2.size
    
    # Determine based on file size and row count
    if file1_size > file2_size:
        return {
            'raw_data': {'file': file1, 'df': df1, 'name': file1.name, 'type': 'Raw Data File'},
            'ingestion': {'file': file2, 'df': df2, 'name': file2.name, 'type': 'Ingestion File'}
        }
    else:
        return {
            'raw_data': {'file': file2, 'df': df2, 'name': file2.name, 'type': 'Raw Data File'},
            'ingestion': {'file': file1, 'df': df1, 'name': file1.name, 'type': 'Ingestion File'}
        }

def display_comparison_results(results):
    """Display detailed comparison results"""
    st.subheader("📈 Detailed Analysis")
    
    # Resource Type and File Type Information
    st.subheader("🔍 Resource Type Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        resource_type = results.get('resource_type', 'Unknown')
        st.metric("Identified Resource Type", resource_type)
        
    with col2:
        ingestion_type = results.get('ingestion_file_type', 'Unknown')
        st.metric("Ingestion File Type", ingestion_type)
    
    # Facility Name Comparison
    st.subheader("🏥 Facility Name Analysis")
    facility_data = results.get('facility_comparison', {})
    
    if 'error' in facility_data:
        st.error(f"❌ {facility_data['error']}")
    else:
        # Facility metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Raw Data Facilities", facility_data.get('raw_facilities_count', 0))
        with col2:
            st.metric("Ingestion Facilities", facility_data.get('ingestion_facilities_count', 0))
        with col3:
            st.metric("Common Facilities", facility_data.get('common_facilities_count', 0))
        with col4:
            missing_count = facility_data.get('missing_in_raw_count', 0)
            st.metric("Missing in Raw Data", missing_count, delta=f"-{missing_count}" if missing_count > 0 else None)
        
        # Missing facilities details
        missing_facilities = facility_data.get('missing_in_raw', [])
        if missing_facilities:
            st.warning(f"⚠️ Found {len(missing_facilities)} facilities in ingestion file that are NOT in raw data:")
            
            # Display missing facilities
            missing_df = pd.DataFrame({
                'Missing Facilities': missing_facilities,
                'Status': 'Not Found in Raw Data'
            })
            st.dataframe(missing_df, use_container_width=True)
            
            # Download button for missing facilities
            excel_data = create_missing_facilities_excel(missing_facilities)
            if excel_data:
                st.download_button(
                    label="📥 Download Missing Facilities Excel",
                    data=excel_data,
                    file_name="missing_facilities.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.success("✅ All facilities in ingestion file are present in raw data!")
    
    # Resource-specific comparison results
    resource_comparison = results.get('resource_comparison')
    if resource_comparison:
        st.subheader("🔬 Resource-Specific Analysis")
        
        if 'error' in resource_comparison:
            st.error(f"❌ {resource_comparison['error']}")
        else:
            st.info(f"**Resource Type:** {resource_comparison.get('resource_type', 'Unknown')}")
            st.info(f"**Ingestion Type:** {resource_comparison.get('ingestion_type', 'Unknown')}")
            st.info(f"**Status:** {resource_comparison.get('comparison_status', 'Unknown')}")
            
            # Display detailed comparison results
            mapping = resource_comparison.get('mapping', {})
            if mapping and 'error' not in mapping:
                # Show summary metrics
                st.write("**Comparison Summary:**")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Ingestion Rows", mapping.get('total_ingestion_rows', 0))
                with col2:
                    st.metric("Matched Rows", mapping.get('matched_rows', 0))
                with col3:
                    st.metric("Quantity Matches", mapping.get('quantity_matches', 0))
                with col4:
                    st.metric("Quantity Mismatches", mapping.get('quantity_mismatches', 0))
                
                # Show detailed comparison results
                comparison_results = mapping.get('comparison_results', [])
                if comparison_results:
                    st.subheader("📊 Detailed Comparison Results")
                    
                    # Create DataFrame for display
                    results_df = pd.DataFrame(comparison_results)
                    
                    # Display the results table
                    st.dataframe(results_df, use_container_width=True)
                    
                    # Show mismatches and no matches separately
                    mismatches = results_df[results_df['match_status'] == 'Mismatch']
                    no_matches = results_df[results_df['match_status'] == 'No Match in Raw Data']
                    
                    if not mismatches.empty:
                        st.warning(f"⚠️ Found {len(mismatches)} quantity mismatches:")
                        st.dataframe(mismatches, use_container_width=True)
                    
                    if not no_matches.empty:
                        st.error(f"❌ Found {len(no_matches)} rows in ingestion that don't exist in raw data:")
                        st.dataframe(no_matches, use_container_width=True)
