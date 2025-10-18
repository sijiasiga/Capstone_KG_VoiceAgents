"""
Code Mapping Database Query Module
Provides functions to look up medical codes and validate them.
"""

import sqlite3
import os
from typing import Optional, List, Dict

class CodeMappingDB:
    """Interface to query the code mapping database."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to the code_mapping.db file. 
                    If None, looks in Database/code_mapping.db
        """
        if db_path is None:
            # Default to Database/code_mapping.db relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(current_dir, 'Database', 'code_mapping.db')
        
        self.db_path = db_path
        
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Code mapping database not found at: {self.db_path}")
    
    def _get_connection(self):
        """Create and return a database connection."""
        return sqlite3.connect(self.db_path)
    
    def lookup_cpt(self, code: str) -> Optional[Dict[str, str]]:
        """
        Look up a CPT code.
        
        Args:
            code: CPT code (e.g., "43644")
            
        Returns:
            Dictionary with code info, or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT code, description, category, status
            FROM cpt_codes WHERE code = ?
        ''', (code,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'code': result[0],
                'description': result[1],
                'category': result[2],
                'status': result[3]
            }
        return None
    
    def lookup_icd10_procedure(self, code: str) -> Optional[Dict[str, str]]:
        """
        Look up an ICD-10 procedure code.
        
        Args:
            code: ICD-10 procedure code (e.g., "0DV60CZ")
            
        Returns:
            Dictionary with code info, or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT code, description, category, status
            FROM icd10_procedure_codes WHERE code = ?
        ''', (code,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'code': result[0],
                'description': result[1],
                'category': result[2],
                'status': result[3]
            }
        return None
    
    def lookup_icd10_diagnosis(self, code: str) -> Optional[Dict[str, str]]:
        """
        Look up an ICD-10 diagnosis code.
        
        Args:
            code: ICD-10 diagnosis code (e.g., "E66.01")
            
        Returns:
            Dictionary with code info, or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT code, description, category, status
            FROM icd10_diagnosis_codes WHERE code = ?
        ''', (code,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'code': result[0],
                'description': result[1],
                'category': result[2],
                'status': result[3]
            }
        return None
    
    def get_approved_codes_for_policy(self, policy_id: str, code_type: str = None) -> List[str]:
        """
        Get all approved codes for a policy.
        
        Args:
            policy_id: Policy ID (e.g., "CG-SURG-83")
            code_type: Optional filter by code type ("CPT", "ICD10PROC", "ICD10DIAG")
            
        Returns:
            List of approved code strings
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if code_type:
            cursor.execute('''
                SELECT code FROM policy_code_mapping
                WHERE policy_id = ? AND code_type = ? AND requirement_type LIKE '%approved%'
            ''', (policy_id, code_type))
        else:
            cursor.execute('''
                SELECT code FROM policy_code_mapping
                WHERE policy_id = ? AND requirement_type LIKE '%approved%'
            ''', (policy_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in results]
    
    def is_code_approved_for_policy(self, policy_id: str, code: str, code_type: str = None) -> bool:
        """
        Check if a code is approved for a policy.
        
        Args:
            policy_id: Policy ID (e.g., "CG-SURG-83")
            code: Code to check
            code_type: Optional code type for faster lookup
            
        Returns:
            True if approved, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if code_type:
            cursor.execute('''
                SELECT 1 FROM policy_code_mapping
                WHERE policy_id = ? AND code = ? AND code_type = ? 
                AND requirement_type LIKE '%approved%'
            ''', (policy_id, code, code_type))
        else:
            cursor.execute('''
                SELECT 1 FROM policy_code_mapping
                WHERE policy_id = ? AND code = ? 
                AND requirement_type LIKE '%approved%'
            ''', (policy_id, code))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    
    def validate_code(self, code: str, code_type: str = None) -> bool:
        """
        Check if a code exists in the database.
        
        Args:
            code: Code to validate
            code_type: Type hint ("CPT", "ICD10PROC", "ICD10DIAG") - optional
            
        Returns:
            True if code exists, False otherwise
        """
        if code_type == 'CPT':
            return self.lookup_cpt(code) is not None
        elif code_type == 'ICD10PROC':
            return self.lookup_icd10_procedure(code) is not None
        elif code_type == 'ICD10DIAG':
            return self.lookup_icd10_diagnosis(code) is not None
        else:
            # Try all three
            return (self.lookup_cpt(code) is not None or 
                   self.lookup_icd10_procedure(code) is not None or
                   self.lookup_icd10_diagnosis(code) is not None)
    
    def get_code_description(self, code: str, code_type: str = None) -> Optional[str]:
        """
        Get the description for a code.
        
        Args:
            code: Code to look up
            code_type: Type hint for faster lookup
            
        Returns:
            Description string, or None if not found
        """
        if code_type == 'CPT':
            info = self.lookup_cpt(code)
        elif code_type == 'ICD10PROC':
            info = self.lookup_icd10_procedure(code)
        elif code_type == 'ICD10DIAG':
            info = self.lookup_icd10_diagnosis(code)
        else:
            # Try all three
            info = (self.lookup_cpt(code) or 
                   self.lookup_icd10_procedure(code) or
                   self.lookup_icd10_diagnosis(code))
        
        return info['description'] if info else None


# Convenience function for quick lookups
def lookup_code(code: str, code_type: str = None) -> Optional[str]:
    """
    Quick lookup function for code descriptions.
    
    Args:
        code: Code to look up
        code_type: Optional type hint
        
    Returns:
        Description string or None
    """
    try:
        db = CodeMappingDB()
        return db.get_code_description(code, code_type)
    except Exception as e:
        print(f"Error looking up code {code}: {e}")
        return None