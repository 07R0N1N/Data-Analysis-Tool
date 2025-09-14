import streamlit as st
import pandas as pd
from comparison_logic import (
    compare_dataframes,
    analyze_data_quality,
    identify_resource_type,
    create_duplicate_rows_excel
)
from utility_functions import (
    read_excel_file,
    get_excel_sheets,
    identify_file_types,
    display_comparison_results
)

def main():
    # Page configuration
    st.set_page_config(
        page_title="Excel Data Comparison Tool",
        layout="wide"
    )

    # Title and description
    st.title("Excel Data Comparison Tool")
    st.markdown("Upload two Excel files to compare and analyze their differences")

    # Sidebar for file uploads
    st.sidebar.header("📁 Upload Files")

    # File upload widgets
    file1 = st.sidebar.file_uploader(
        "Upload First Excel File",
        type=['xlsx', 'xls'],
        key="file1"
    )

    file2 = st.sidebar.file_uploader(
        "Upload Second Excel File", 
        type=['xlsx', 'xls'],
        key="file2"
    )

    # Main content area
    if file1 is not None and file2 is not None:
        st.success("✅ Both files uploaded successfully!")

        # Try to read the files
        df1, error1 = read_excel_file(file1)
        df2, error2 = read_excel_file(file2)
        
        if error1:
            st.error(f"❌ Error reading File 1: {error1}")
            return
            
        if error2:
            st.error(f"❌ Error reading File 2: {error2}")
            return
        
        # Identify file types (raw data vs ingestion)
        file_types = identify_file_types(file1, file2, df1, df2)
        
        # Display file type identification
        st.subheader("📋 File Type Identification")
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"**Raw Data File:** {file_types['raw_data']['name']}")
            st.write(f"Size: {file_types['raw_data']['file'].size:,} bytes")
            
        with col2:
            st.info(f"**Ingestion File:** {file_types['ingestion']['name']}")
            st.write(f"Size: {file_types['ingestion']['file'].size:,} bytes")
        
        # Handle multiple sheets in raw data file
        raw_data_file = file_types['raw_data']['file']
        ingestion_file = file_types['ingestion']['file']
        
        # Get sheets from raw data file
        raw_sheets, sheet_error = get_excel_sheets(raw_data_file)
        if sheet_error:
            st.error(f"❌ Error reading sheets from raw data file: {sheet_error}")
            return
        
        # Get sheets from ingestion file
        ingestion_sheets, sheet_error = get_excel_sheets(ingestion_file)
        if sheet_error:
            st.error(f"❌ Error reading sheets from ingestion file: {sheet_error}")
            return
        
        # Display sheet information
        st.subheader("📊 Sheet Information")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Raw Data Sheets:** {len(raw_sheets)}")
            st.write(f"Sheets: {', '.join(raw_sheets)}")
            
        with col2:
            st.write(f"**Ingestion Sheets:** {len(ingestion_sheets)}")
            st.write(f"Sheets: {', '.join(ingestion_sheets)}")
        
        # Read appropriate sheets for comparison
        ingestion_first_sheet = ingestion_sheets[0] if ingestion_sheets else None
        
        if not ingestion_first_sheet:
            st.error("❌ Could not identify first sheet in ingestion file")
            return
        
        # Read ingestion sheet
        ingestion_df, error = read_excel_file(ingestion_file, ingestion_first_sheet)
        if error:
            st.error(f"❌ Error reading first sheet from ingestion: {error}")
            return
        
        # Identify resource type and get appropriate raw data sheet
        resource_type = identify_resource_type(ingestion_df)
        
        # Map resource types to their corresponding sheet names in raw data
        resource_sheet_mapping = {
            'GHG Emissions': 'GHG Emissions',
            'Water': 'Water',  # Will be added when Water resource type is implemented
            'Waste': 'Waste',  # Will be added when Waste resource type is implemented
            'Activity Metrics': 'Activity Metrics'  # Will be added when Activity Metrics resource type is implemented
        }
        
        if resource_type in resource_sheet_mapping:
            expected_sheet = resource_sheet_mapping[resource_type]
            if expected_sheet in raw_sheets:
                raw_data_sheet = expected_sheet
            else:
                st.error(f"❌ {expected_sheet} sheet not found in raw data file")
                st.write(f"Available sheets: {', '.join(raw_sheets)}")
                return
        else:
            # For unknown resource types, use first sheet as fallback
            raw_data_sheet = raw_sheets[0] if raw_sheets else None
            if not raw_data_sheet:
                st.error("❌ Could not identify first sheet in raw data file")
                return
            st.warning(f"⚠️ Unknown resource type '{resource_type}', using first sheet: {raw_data_sheet}")
        
        # Read raw data sheet
        raw_df, error = read_excel_file(raw_data_file, raw_data_sheet)
        if error:
            st.error(f"❌ Error reading {raw_data_sheet} sheet from raw data: {error}")
            return
        
        # Display sheet previews
        st.subheader("📋 Sheet Previews")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Raw Data - {raw_data_sheet} Sheet**")
            st.dataframe(raw_df.head())
            st.write(f"Rows: {len(raw_df)}, Columns: {len(raw_df.columns)}")
            
        with col2:
            st.write(f"**Ingestion - {ingestion_first_sheet} Sheet**")
            st.dataframe(ingestion_df.head())
            st.write(f"Rows: {len(ingestion_df)}, Columns: {len(ingestion_df.columns)}")
        
        # Detailed comparison
        comparison_results = compare_dataframes(raw_df, ingestion_df)
        display_comparison_results(comparison_results)
        
        # Data quality analysis
        quality_data = analyze_data_quality(raw_df, ingestion_df)
        quality_issues = quality_data['quality_issues']
        duplicate_rows = quality_data['duplicate_rows']
        
        if quality_issues:
            st.subheader("⚠️ Data Quality Issues")
            for issue in quality_issues:
                st.warning(f"• {issue}")
            
            # Display duplicate rows if any
            if duplicate_rows is not None and not duplicate_rows.empty:
                st.subheader("🔄 Duplicate Rows Found")
                st.write(f"Found {len(duplicate_rows)} duplicate rows in ingestion data:")
                st.dataframe(duplicate_rows, use_container_width=True)
                
                # Download button for duplicate rows
                excel_data = create_duplicate_rows_excel(duplicate_rows)
                if excel_data:
                    st.download_button(
                        label="📥 Download Duplicate Rows Excel",
                        data=excel_data,
                        file_name="duplicate_rows.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        else:
            st.success("✅ No data quality issues detected!")
            
    else:
        st.info("👆 Please upload both Excel files using the sidebar to begin the comparison")
        
        # Show example of what the tool will do
        st.markdown("### What this tool will do:")
        st.markdown("""
        - ✅ Compare data between two Excel files
        - 📊 Generate detailed analysis and insights
        - 📈 Show statistical differences
        - 📄 Export results as Excel file
        - 🔍 Identify added, removed, and modified rows
        - 🏥 Focus on Facility Name comparisons
        - 📋 Handle multiple sheets in raw data files
        """)

if __name__ == "__main__":
    main()
