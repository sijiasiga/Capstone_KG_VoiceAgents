
PROMPT="prompts/Evaluation/data_dictionary_judge_prompt.txt"
PROMPT="prompts/Evaluation/patient_extraction_judge_prompt.txt"
PROMPT="prompts/Evaluation/policy_condition_judge_prompt.txt"
DOC="Run_Time_Policy/LCD_37360/Policy_LCD_37360.txt"
DATA_DIC="Run_Time_Policy/LCD_37360/Data_dictionary_LCD_37360.json"
GENERATED="Run_Time_Policy/LCD_37360/Policy_LCD_37360.json"

python prompt_generator.py \
  --prompt $PROMPT \
  --original-document $DOC \
  --data-dictionary $DATA_DIC \
  --extracted-dd $GENERATED \
  --extracted-json $GENERATED \
  --output Evaluation/
