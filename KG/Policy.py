class Policy:
    def __init__(self, name, guideline_number=None, description=None, raw_text=None):
        self.name = name
        self.guideline_number = guideline_number
        self.description = description
        self.raw_text = raw_text           # store original policy text
        self.restrictions = []             # list of dicts

    def add_restriction(self, condition, rule, codes=None, logic="OR"):
        self.restrictions.append({
            "condition": condition,   # natural language condition
            "rule": rule,             # computable SQL-like logic
            "codes": codes or [],    # CPT/ICD codes
            "logic": logic           # logical operator
        })

    # def to_sql(self):
    #     if not self.restrictions:
    #         return ""
    #     sql_clauses = [f"({r['rule']})" for r in self.restrictions]
    #     # default join is OR, but can be extended per restriction["logic"]
    #     return " OR ".join(sql_clauses)

    def to_dict(self):
        return {
            "name": self.name,
            "guideline_number": self.guideline_number,
            "description": self.description,
            "raw_text": self.raw_text,
            "restrictions": self.restrictions
        }

    @classmethod
    def from_dict(cls, data):
        policy = cls(
            name=data.get("name"),
            guideline_number=data.get("guideline_number"),
            description=data.get("description"),
            raw_text=data.get("raw_text")
        )
        for r in data.get("restrictions", []):
            policy.add_restriction(
                condition=r["condition"],
                rule=r["rule"],
                codes=r.get("codes", []),
                logic=r.get("logic", "OR")
            )
        return policy


# Factory function to create the bariatric surgery policy matching policies.json
def create_bariatric_surgery_policy() -> Policy:
    """Create the bariatric surgery policy with all restrictions"""
    policy = Policy(
        name="Bariatric Surgery and Other Treatments for Clinically Severe Obesity",
        guideline_number="CG-SURG-83",
        description="Policy for surgical and other treatments for clinically severe obesity, including criteria for medically necessary bariatric surgery, reoperation, revision, and not medically necessary procedures.",
        raw_text="Gastric bypass and gastric restrictive procedures are considered medically necessary when all of the following criteria are met: Individual is age 18 years or older; the recommended surgery is one of certain procedures; a BMI of 40 or greater, or 35 or greater with an obesity-related comorbid condition; documentation of weight loss program, prior failed conservative therapy, pre-operative medical & mental health evaluations & education; plus a treatment plan. Reoperations or revisions are medically necessary under certain criteria. Not medically necessary when criteria are not met or for specific non-covered procedures."
    )
    
    # Add all restrictions
    policy.add_restriction(
        condition="Age ≥ 18",
        rule="patient_age >= 18",
        codes=[],
        logic="AND"
    )
    
    policy.add_restriction(
        condition="Procedure is one of eligible bariatric types",
        rule="procedure_code in eligible_bariatric_procedure_codes",
        codes=["43644", "43645", "43770", "43771", "43772", "43773", "43774", "43775", "43842", "43843", "43845", "43846", "43847", "43848", "43886", "43887", "43888"],
        logic="AND"
    )
    
    policy.add_restriction(
        condition="BMI ≥ 40 OR BMI ≥ 35 with comorbidity",
        rule="(patient_bmi >= 40) OR (patient_bmi >= 35 AND comorbidity_flag = 1)",
        codes=[],
        logic="AND"
    )
    
    policy.add_restriction(
        condition="Past participation in a weight loss program",
        rule="weight_loss_program_flag = True",
        codes=[],
        logic="AND"
    )
    
    policy.add_restriction(
        condition="Inadequate weight loss despite conservative medical therapy",
        rule="conservative_therapy_flag = True",
        codes=[],
        logic="AND"
    )
    
    policy.add_restriction(
        condition="Pre-operative medical and mental health evaluations and clearances",
        rule="medical_evaluation_flag = True AND mental_health_evaluation_flag = True",
        codes=[],
        logic="AND"
    )
    
    policy.add_restriction(
        condition="Pre-operative education on risks, benefits, expectations and long-term follow-up",
        rule="preoperative_education_flag = True",
        codes=[],
        logic="AND"
    )
    
    policy.add_restriction(
        condition="Treatment plan addresses pre- and post-operative needs",
        rule="treatment_plan_flag = True",
        codes=[],
        logic="AND"
    )
    
    return policy


def generate_policies() -> list:
    """Generate the policies list in the target JSON format"""
    policy = create_bariatric_surgery_policy()
    return [policy.to_dict()]