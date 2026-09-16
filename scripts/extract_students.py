import json
import re

def main():
    transcript_path = r"C:\Users\hp\.gemini\antigravity-ide\brain\0a0d8708-fcff-4b1c-a1bc-71a8e0d6e115\.system_generated\logs\transcript_full.jsonl"
    students = []
    
    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            if '"type":"USER_INPUT"' in line and '==Start of PDF==' in line:
                data = json.loads(line)
                content = data.get('content', '')
                
                # Regex to match: <number> <register_no> <Name (can have spaces)> <Year X - Sec Y> Promoted
                pattern = re.compile(r'^\d+\s+(\d{12})\s+(.*?)\s+(Year\s+\d+\s+-\s+Sec\s+[A-Z])\s+Promoted$', re.MULTILINE)
                for match in pattern.finditer(content):
                    reg_no = match.group(1)
                    name = match.group(2).strip()
                    sec = match.group(3).strip()
                    students.append((reg_no, name, sec))
                
                break

    print(f"Extracted {len(students)} students")
    
    # Write to seed_demo.py
    seed_file = r"c:\Users\hp\SmartAttendance\scripts\seed_demo.py"
    with open(seed_file, 'r', encoding='utf-8') as f:
        seed_content = f.read()

    # Find where students_data is defined
    start_str = "students_data = ["
    end_str = "        for reg_no, name, sec in students_data:"
    
    start_idx = seed_content.find(start_str)
    end_idx = seed_content.find(end_str)
    
    if start_idx != -1 and end_idx != -1:
        new_list_str = "students_data = [\n"
        for i, s in enumerate(students):
            new_list_str += f'            ("{s[0]}", "{s[1]}", "{s[2]}")'
            if i < len(students) - 1:
                new_list_str += ",\n"
            else:
                new_list_str += "\n        ]\n        "
                
        new_content = seed_content[:start_idx] + new_list_str + seed_content[end_idx:]
        with open(seed_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Updated seed_demo.py successfully")
    else:
        print("Could not find students_data block in seed_demo.py")

if __name__ == '__main__':
    main()
