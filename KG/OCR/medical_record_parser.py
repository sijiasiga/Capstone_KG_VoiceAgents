#!/usr/bin/env python3
"""
Medical Record Parser
Automatically extracts structured data from OCR-extracted medical records.

"""

import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

class MedicalRecordParser:
    """Parse medical records and extract structured patient data."""
    
    def __init__(self, text: str):
        self.text = text
        self.text_lower = text.lower()
    
    def parse(self) -> Dict[str, Any]:
        """Parse medical record and return structured patient data."""
        
        patient_data = {
            "patient_id": self.extract_patient_id(),
            "patient_age": self.extract_age(),
            "patient_bmi": self.extract_bmi(),
            "comorbidity_flag": self.check_comorbidities(),
            "weight_loss_program_history": self.check_weight_loss_program(),
            "conservative_therapy_attempt": self.check_conservative_therapy(),
            "preop_medical_clearance": self.check_medical_clearance(),
            "preop_psych_clearance": self.check_psych_clearance(),
            "preop_education_completed": self.check_preop_education(),
            "treatment_plan_documented": self.check_treatment_plan(),
            "procedure_code_CPT": self.extract_procedure_code(),
            "procedure_code_ICD10PCS": self.extract_icd10_procedure(),
            "diagnosis_code_ICD10": self.extract_diagnosis_code()
        }
        
        return patient_data
    
    def extract_patient_id(self) -> str:
        """Extract patient MRN/ID."""
        # Look for MRN pattern
        patterns = [
            r'MRN[:\s]+(\d{4}-\d{4}-\d{3})',  # MRN: 8472-2025-445
            r'MRN[:\s]+(\d+)',  # MRN: 12345
            r'Patient ID[:\s]+(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                # Extract just the numeric portion
                mrn = match.group(1).replace('-', '')[:10]
                return mrn
        
        return "unknown"
    
    def extract_age(self) -> int:
        """Extract patient age."""
        # Look for explicit age
        patterns = [
            r'(\d{2})\s*years?\s*old',  # 47 years old
            r'Age[:\s]+(\d{2})',  # Age: 47
            r'(\d{2})M\s',  # 47M
            r'(\d{2})yo',  # 47yo
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                age = int(match.group(1))
                if 18 <= age <= 100:  # Sanity check
                    return age
        
        # Try to calculate from DOB
        dob_match = re.search(r'DOB[:\s]+(\d{2})/(\d{2})/(\d{4})', self.text, re.IGNORECASE)
        if dob_match:
            month, day, year = map(int, dob_match.groups())
            current_year = datetime.now().year
            age = current_year - year
            if 18 <= age <= 100:
                return age
        
        return 0  # Default if not found
    
    def extract_bmi(self) -> float:
        """Extract BMI value."""
        # Look for BMI pattern
        patterns = [
            r'BMI[:\s]+(\d+\.?\d*)',  # BMI: 42.4
            r'BMI[:\s]+(\d+)',  # BMI: 42
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                bmi = float(match.group(1))
                if 15 <= bmi <= 80:  # Sanity check
                    return bmi
        
        return 0.0  # Default if not found
    
    def check_comorbidities(self) -> bool:
        """Check for obesity-related comorbidities."""
        comorbidity_keywords = [
            'diabetes', 'diabetic', 'hyperglycemia', 'A1C', 'HbA1c',
            'hypertension', 'high blood pressure', 'HTN',
            'sleep apnea', 'obstructive sleep', 'CPAP',
            'cardiovascular disease', 'cardiac', 'heart disease',
            'cardiomyopathy', 'LVH', 'ventricular hypertrophy',
            'pickwickian', 'fatty liver', 'hepatic steatosis', 'NAFLD'
        ]
        
        for keyword in comorbidity_keywords:
            if keyword.lower() in self.text_lower:
                return True
        
        return False
    
    def check_weight_loss_program(self) -> bool:
        """Check for documented weight loss program participation."""
        program_keywords = [
            'weight loss program', 'weight management program',
            'medically supervised', 'nutritionist', 'dietitian',
            'nutrition counseling', 'behavioral modification',
            'weight watchers', 'jenny craig'
        ]
        
        # Look for duration mentions (6+ months)
        duration_patterns = [
            r'(\d+)\s*months?\s*(program|supervised|counseling|visits)',
            r'program.*?(\d+)\s*months?',
            r'supervised.*?(\d+)\s*months?'
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, self.text_lower)
            if match:
                months = int(match.group(1))
                if months >= 6:
                    return True
        
        # Check for program keywords
        for keyword in program_keywords:
            if keyword in self.text_lower:
                return True
        
        return False
    
    def check_conservative_therapy(self) -> bool:
        """Check for conservative medical therapy attempts."""
        therapy_keywords = [
            'conservative therapy', 'conservative medical therapy',
            'diet and exercise', 'behavioral modification',
            'meal plan', 'calorie', 'lifestyle modification',
            'weight loss attempt', 'tried to lose weight',
            'diet program', 'exercise program'
        ]
        
        for keyword in therapy_keywords:
            if keyword in self.text_lower:
                return True
        
        # If weight loss program is documented, conservative therapy is implied
        if self.check_weight_loss_program():
            return True
        
        return False
    
    def check_medical_clearance(self) -> bool:
        """Check for pre-operative medical clearance."""
        clearance_keywords = [
            'cleared for surgery',
            'medical clearance',
            'cardiology.*clear',
            'cardiac clearance',
            'medically cleared'
        ]
        
        for keyword in clearance_keywords:
            if re.search(keyword, self.text_lower):
                return True
        
        # Look for specific clearance notes
        if re.search(r'(cardiology|cardiac|medical).*?(clear|approved)', self.text_lower):
            return True
        
        return False
    
    def check_psych_clearance(self) -> bool:
        """Check for pre-operative psychological clearance."""
        psych_keywords = [
            'psychological clearance',
            'psych clearance',
            'psychology.*clear',
            'mental health.*clear',
            'psychological assessment.*clear',
            'cleared for bariatric surgery from psychological'
        ]
        
        for keyword in psych_keywords:
            if re.search(keyword, self.text_lower):
                return True
        
        return False
    
    def check_preop_education(self) -> bool:
        """Check for pre-operative education completion."""
        education_keywords = [
            'pre-operative education',
            'preoperative education',
            'patient education',
            'educated on risks',
            'education.*complet',
            'patient.*understanding',
            'verbalizes understanding'
        ]
        
        for keyword in education_keywords:
            if re.search(keyword, self.text_lower):
                return True
        
        return False
    
    def check_treatment_plan(self) -> bool:
        """Check for documented treatment plan."""
        plan_keywords = [
            'treatment plan',
            'plan:',
            'assessment.*plan',
            'surgical plan',
            'recommendations:'
        ]
        
        for keyword in plan_keywords:
            if re.search(keyword, self.text_lower):
                return True
        
        return False
    
    def extract_procedure_code(self) -> str:
        """Extract CPT procedure code."""
        # Common bariatric surgery procedures and their codes
        procedure_mapping = {
            'roux-en-y': '43846',  # Most common
            'gastric bypass': '43846',
            'sleeve gastrectomy': '43775',
            'gastric band': '43770',
            'adjustable gastric': '43770',
            'biliopancreatic diversion': '43845',
            'duodenal switch': '43845'
        }
        
        # Look for explicit CPT code in text
        cpt_match = re.search(r'CPT[:\s]+(\d{5})', self.text, re.IGNORECASE)
        if cpt_match:
            return cpt_match.group(1)
        
        # Infer from procedure description
        for procedure, code in procedure_mapping.items():
            if procedure in self.text_lower:
                return code
        
        return "43846"  # Default to Roux-en-Y (most common)
    
    def extract_icd10_procedure(self) -> str:
        """Extract ICD-10 procedure code."""
        # Look for explicit ICD-10-PCS code
        icd_patterns = [
            r'ICD-?10-?PCS[:\s]+([0-9A-Z]{7})',
            r'procedure code[:\s]+([0-9A-Z]{7})',
        ]
        
        for pattern in icd_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Map CPT to common ICD-10-PCS
        cpt_to_icd10 = {
            '43846': '0D160ZA',  # Gastric bypass to jejunum
            '43775': '0DB64Z3',  # Sleeve gastrectomy
            '43770': '0DV60CZ',  # Gastric band placement
            '43845': '0D160ZB'   # Biliopancreatic diversion
        }
        
        cpt_code = self.extract_procedure_code()
        return cpt_to_icd10.get(cpt_code, '0D160ZA')
    
    def extract_diagnosis_code(self) -> str:
        """Extract ICD-10 diagnosis code."""
        # Look for explicit ICD-10 diagnosis code
        icd_patterns = [
            r'ICD-?10[:\s]+([A-Z]\d{2}\.?\d{0,2})',
            r'diagnosis code[:\s]+([A-Z]\d{2}\.?\d{0,2})',
        ]
        
        for pattern in icd_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                code = match.group(1)
                # Ensure format is correct (add period if missing)
                if '.' not in code and len(code) > 3:
                    code = code[:3] + '.' + code[3:]
                return code
        
        # Infer from diagnosis description
        diagnosis_mapping = {
            'morbid obesity': 'E66.01',
            'severe obesity': 'E66.01',
            'class 3 obesity': 'E66.01',
            'obesity.*excess calories': 'E66.01',
            'drug-induced obesity': 'E66.1',
            'obesity.*alveolar hypoventilation': 'E66.2',
            'pickwickian': 'E66.2'
        }
        
        for diagnosis, code in diagnosis_mapping.items():
            if re.search(diagnosis, self.text_lower):
                return code
        
        return "E66.01"  # Default to morbid obesity


def parse_medical_record_file(input_file: str, output_dir: str = None) -> Dict[str, Any]:
    """
    Parse a medical record text file and generate structured JSON.
    
    Args:
        input_file: Path to OCR-extracted text file
        output_dir: Directory to save output JSON (optional, defaults to input file directory)
    
    Returns:
        Parsed patient data dictionary
    """
    # Read input file
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Parse medical record
    parser = MedicalRecordParser(text)
    patient_data = parser.parse()
    
    # Use input file directory as default output directory
    if output_dir is None:
        output_dir = Path(input_file).parent
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    patient_id = patient_data['patient_id']
    output_file = output_dir / f"Patient_data_dictionary_{patient_id}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(patient_data, f, indent=2)
    
    print(f"✅ Parsed medical record saved to: {output_file}")
    
    return patient_data


def main():
    parser = argparse.ArgumentParser(
        description='Parse medical records and extract structured patient data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python medical_record_parser.py MR_2.txt
  python medical_record_parser.py MR_2.txt --output-dir ../test1/Patient_data_dictionary
  python medical_record_parser.py MR_2.txt -o ../test1/Patient_data_dictionary --verbose
        """
    )
    
    parser.add_argument('input_file', help='OCR-extracted medical record text file')
    parser.add_argument('--output-dir', '-o', help='Output directory for JSON file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Print extracted data')
    
    args = parser.parse_args()
    
    # Check input file exists
    if not Path(args.input_file).exists():
        print(f"❌ Error: File not found: {args.input_file}")
        return 1
    
    print(f"📄 Parsing medical record: {args.input_file}")
    
    # Parse medical record
    patient_data = parse_medical_record_file(args.input_file, args.output_dir)
    
    # Print summary
    print("\n📊 Extracted Patient Data:")
    print(f"   Patient ID: {patient_data['patient_id']}")
    print(f"   Age: {patient_data['patient_age']}")
    print(f"   BMI: {patient_data['patient_bmi']}")
    print(f"   Comorbidities: {'Yes' if patient_data['comorbidity_flag'] else 'No'}")
    print(f"   Weight Loss Program: {'Yes' if patient_data['weight_loss_program_history'] else 'No'}")
    print(f"   Medical Clearance: {'Yes' if patient_data['preop_medical_clearance'] else 'No'}")
    print(f"   Psych Clearance: {'Yes' if patient_data['preop_psych_clearance'] else 'No'}")
    print(f"   Procedure Code: {patient_data['procedure_code_CPT']}")
    print(f"   Diagnosis Code: {patient_data['diagnosis_code_ICD10']}")
    
    if args.verbose:
        print("\n📝 Full JSON:")
        print(json.dumps(patient_data, indent=2))
    
    print("\n✅ Parsing complete!")
    return 0


if __name__ == "__main__":
    exit(main())