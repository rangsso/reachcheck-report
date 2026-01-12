import argparse
import sys
import os

# Add the current directory to sys.path to allow imports if running from root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from collector import DataCollector
from analyzer import Analyzer
from report import ReportGenerator

def main():
    parser = argparse.ArgumentParser(description="ReachCheck MVP - AI Exposure Report Generator")
    parser.add_argument("--store", type=str, required=True, help="Name of the store to analyze")
    parser.add_argument("--output", type=str, default="report.pdf", help="Output filename")
    
    args = parser.parse_args()
    store_name = args.store
    
    print(f"[*] Starting analysis for: {store_name}")
    
    # 1. Collect Data (Mock)
    collector = DataCollector()
    print("[-] Collecting data...")
    store_info = collector.collect(store_name)
    analysis_result = collector.mock_analysis(store_info)
    
    # 2. Analyze (Refine)
    analyzer = Analyzer()
    print("[-] Analyzing data...")
    report_data = analyzer.process(store_info, analysis_result)
    
    # 3. Generate Report
    generator = ReportGenerator()
    print("[-] Generating PDF report...")
    output_path = generator.generate(report_data, filename=args.output)
    
    print(f"[+] Report generated successfully: {output_path}")

if __name__ == "__main__":
    main()
