
PROMPT="prompts/Evaluation/data_dictionary_judge_prompt_cot.txt"
# PROMPT="prompts/Evaluation/patient_extraction_judge_prompt_cot.txt"
# PROMPT="prompts/Evaluation/policy_condition_judge_prompt_cot.txt"
# PROMPT="prompts/Evaluation/data_dictionary_judge_prompt_zero.txt"
# PROMPT="prompts/Evaluation/patient_extraction_judge_prompt_zero.txt"
# PROMPT="prompts/Evaluation/policy_condition_judge_prompt_zero.txt"
DOC="Run_Time_Policy/LCD_37360/Policy_LCD_37360.txt"
DOC_PAT="Run_Time_Patient/Patient_L37360001_Policy_LCD_37360/L37360_Record_001.txt"
PAT="Run_Time_Patient/Patient_L37360001_Policy_LCD_37360/Patient_data_L37360_001.json"
DATA="Run_Time_Policy/LCD_37360/Data_dictionary_LCD_37360.json"
COND="Run_Time_Policy/LCD_37360/Policy_LCD_37360.json"

python prompt_generator.py \
  --prompt $PROMPT \
  --original-document $DOC \
  --original-patient $DOC_PAT \
  --extracted-patient $PAT \
  --extracted-dd $DATA \
  --extracted-policy $COND \
  --output Evaluation/LCD_37360/
