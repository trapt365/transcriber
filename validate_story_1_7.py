#!/usr/bin/env python3
"""
Validation script for Story 1.7: Basic Transcript Export and Download Functionality

This script validates that all required components for Story 1.7 are implemented:
1. Export API endpoints
2. Frontend download interface  
3. File naming and content handling
4. Export data validation
5. Basic testing framework
"""

import os
import re
from pathlib import Path


def check_file_exists(file_path, description):
    """Check if a file exists and print status."""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (NOT FOUND)")
        return False


def check_content_in_file(file_path, patterns, description):
    """Check if specific patterns exist in a file."""
    if not os.path.exists(file_path):
        print(f"❌ {description}: {file_path} (FILE NOT FOUND)")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        missing_patterns = []
        for pattern_name, pattern in patterns.items():
            if not re.search(pattern, content, re.MULTILINE | re.DOTALL):
                missing_patterns.append(pattern_name)
        
        if missing_patterns:
            print(f"❌ {description}: Missing {', '.join(missing_patterns)}")
            return False
        else:
            print(f"✅ {description}: All required patterns found")
            return True
    
    except Exception as e:
        print(f"❌ {description}: Error reading file - {e}")
        return False


def validate_story_1_7():
    """Main validation function."""
    print("🔍 Validating Story 1.7: Basic Transcript Export and Download Functionality")
    print("=" * 80)
    
    all_checks_passed = True
    
    # 1. Check Export API Endpoints
    print("\n📡 Checking Export API Endpoints:")
    
    jobs_route_patterns = {
        'export_endpoint': r'/api/v1/jobs/<job_id>/export/<format_type>.*methods=\[\'GET\'\]',
        'export_formats_endpoint': r'/api/v1/jobs/<job_id>/export-formats.*methods=\[\'GET\'\]',
        'export_transcript_function': r'def export_transcript\(job_id, format_type\):',
        'get_export_formats_function': r'def get_export_formats\(job_id\):',
        'content_type_mapping': r'content_type_map\s*=\s*{',
        'filename_generation': r'filename\s*=\s*f["\']transcript_{job_id}_{timestamp}\.{export_format\.value}["\']',
        'response_headers': r'Content-Disposition.*attachment.*filename',
    }
    
    if not check_content_in_file('backend/app/routes/jobs.py', jobs_route_patterns, 'Export API endpoints'):
        all_checks_passed = False
    
    # 2. Check Export Service Integration
    print("\n⚙️ Checking Export Service:")
    
    export_service_patterns = {
        'export_service_import': r'from backend\.app\.services\.export_service import TranscriptExportService',
        'export_error_import': r'from backend\.app\.utils\.exceptions import ExportError',
        'export_format_import': r'from backend\.app\.models\.enums import.*ExportFormat',
    }
    
    if not check_content_in_file('backend/app/routes/jobs.py', export_service_patterns, 'Export service integration'):
        all_checks_passed = False
    
    # 3. Check Frontend Templates
    print("\n🖥️ Checking Frontend Templates:")
    
    status_template_patterns = {
        'download_modal': r'<div.*id=["\']downloadModal["\']',
        'format_cards': r'export-format-card.*data-format',
        'download_button_modal': r'data-bs-toggle=["\']modal["\'].*data-bs-target=["\']#downloadModal["\']',
        'format_selection': r'<div.*export-format-card.*data-format=["\']txt["\']',
    }
    
    if not check_content_in_file('frontend/templates/status.html', status_template_patterns, 'Status template export modal'):
        all_checks_passed = False
    
    transcript_template_patterns = {
        'download_modal': r'<div.*id=["\']downloadModal["\']',
        'download_button_modal': r'data-bs-toggle=["\']modal["\'].*data-bs-target=["\']#downloadModal["\']',
    }
    
    if not check_content_in_file('frontend/templates/transcript.html', transcript_template_patterns, 'Transcript template export modal'):
        all_checks_passed = False
    
    # 4. Check CSS Styles
    print("\n🎨 Checking CSS Styles:")
    
    css_patterns = {
        'export_format_cards': r'\.export-format-card\s*{',
        'selected_state': r'\.export-format-card\.selected\s*{',
        'disabled_state': r'\.export-format-card\.disabled\s*{',
        'download_modal': r'#downloadModal.*\.modal-body',
    }
    
    if not check_content_in_file('frontend/static/css/status.css', css_patterns, 'Export modal CSS styles'):
        all_checks_passed = False
    
    # 5. Check JavaScript Implementation
    print("\n📜 Checking JavaScript Implementation:")
    
    status_js_patterns = {
        'download_modal_init': r'initializeDownloadModal.*function',
        'format_selection_handler': r'formatCards\.forEach.*addEventListener\(["\']click["\']',
        'download_in_format': r'downloadInFormat.*function',
        'export_url_fetch': r'fetch\(exportUrl\)',
        'format_availability_check': r'checkExportAvailability.*function',
    }
    
    if not check_content_in_file('frontend/static/js/status.js', status_js_patterns, 'Status page JavaScript'):
        all_checks_passed = False
    
    transcript_js_patterns = {
        'download_modal_init': r'initializeDownloadModal.*{',
        'download_in_format': r'downloadInFormat\(format\)\s*{',
    }
    
    if not check_content_in_file('frontend/static/js/transcript.js', transcript_js_patterns, 'Transcript page JavaScript'):
        all_checks_passed = False
    
    # 6. Check Test Files
    print("\n🧪 Checking Test Implementation:")
    
    if not check_file_exists('tests/unit/test_export_endpoints.py', 'Unit tests for export endpoints'):
        all_checks_passed = False
    
    if not check_file_exists('tests/integration/test_export_workflow.py', 'Integration tests for export workflow'):
        all_checks_passed = False
    
    unit_test_patterns = {
        'test_export_success': r'def test_export_transcript_success',
        'test_job_not_found': r'def test_export_transcript_job_not_found',
        'test_invalid_format': r'def test_export_transcript_invalid_format',
        'test_content_types': r'def test_content_type_mapping',
        'test_filename': r'def test_filename_generation',
        'test_utf8': r'def test_utf8_encoding',
    }
    
    if not check_content_in_file('tests/unit/test_export_endpoints.py', unit_test_patterns, 'Unit test coverage'):
        all_checks_passed = False
    
    integration_test_patterns = {
        'test_service_integration': r'def test_export_service_integration',
        'test_validation_failures': r'def test_export_validation_failures',
        'test_utf8_cyrillic': r'def test_utf8_handling_cyrillic',
        'test_end_to_end': r'def test_end_to_end_export_api',
    }
    
    if not check_content_in_file('tests/integration/test_export_workflow.py', integration_test_patterns, 'Integration test coverage'):
        all_checks_passed = False
    
    # 7. Check Export Service Functionality
    print("\n🔧 Checking Export Service Implementation:")
    
    export_service_exists = check_file_exists('backend/app/services/export_service.py', 'Export service implementation')
    
    if export_service_exists:
        service_patterns = {
            'all_formats_supported': r'ExportFormat\.JSON.*ExportFormat\.TXT.*ExportFormat\.SRT.*ExportFormat\.VTT.*ExportFormat\.CSV',
            'validation_method': r'def validate_export_data',
            'export_stats': r'def get_export_stats',
            'json_export': r'def _export_json',
            'txt_export': r'def _export_txt',
            'srt_export': r'def _export_srt',
            'vtt_export': r'def _export_vtt',
            'csv_export': r'def _export_csv',
        }
        
        if not check_content_in_file('backend/app/services/export_service.py', service_patterns, 'Export service methods'):
            all_checks_passed = False
    else:
        all_checks_passed = False
    
    # 8. Final Summary
    print("\n" + "=" * 80)
    if all_checks_passed:
        print("🎉 SUCCESS: All Story 1.7 components are implemented!")
        print("\n✨ Implementation Summary:")
        print("• Export API endpoints with proper content types and headers")
        print("• Frontend download modal with format selection")
        print("• CSS styling for export interface")
        print("• JavaScript handling for download workflow")
        print("• Comprehensive test coverage")
        print("• Full export service integration")
        print("\n🚀 Story 1.7 is ready for testing and deployment!")
        return True
    else:
        print("❌ VALIDATION FAILED: Some components are missing or incomplete")
        print("\n🔧 Please review the failed checks above and complete the implementation.")
        return False


if __name__ == '__main__':
    success = validate_story_1_7()
    exit(0 if success else 1)