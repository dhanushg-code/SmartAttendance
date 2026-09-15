import sys

def main():
    seed_file = r"c:\Users\hp\SmartAttendance\scripts\seed_demo.py"
    with open(seed_file, 'r', encoding='utf-8') as f:
        seed_content = f.read()

    start_str = "students_data = ["
    end_str = "        for reg_no, name, sec in students_data:"
    
    start_idx = seed_content.find(start_str)
    end_idx = seed_content.find(end_str)
    
    if start_idx != -1 and end_idx != -1:
        current_list = seed_content[start_idx:end_idx]
        
        # Remove the closing bracket and add new ones
        new_students = [
            ("110325104055", "MIDHULESH S", "Year 2 - Sec B"),
            ("110325104056", "MOHAMED JARULLAH S", "Year 2 - Sec B"),
            ("110325104057", "MUDDULURU KEERTHANA", "Year 2 - Sec B"),
            ("110324104001", "AADARSHINI V", "Year 3 - Sec A"),
            ("110324104002", "AJAY V", "Year 3 - Sec A"),
            ("110324104003", "ANISH S", "Year 3 - Sec A"),
            ("110324104061", "NAVEEN K R", "Year 3 - Sec B"),
            ("110324104062", "NIRMALRAJ D", "Year 3 - Sec B"),
            ("110324104063", "NISHANTHINI M", "Year 3 - Sec B"),
            ("110323104001", "ABINAYA K", "Year 4 - Sec A"),
            ("110323104002", "ABINAYA R", "Year 4 - Sec A"),
            ("110323104003", "ABINAYA SP", "Year 4 - Sec A"),
            ("110323104061", "HARINI M", "Year 4 - Sec B"),
            ("110323104062", "MOHAN R", "Year 4 - Sec B"),
            ("110323104063", "MONICA U", "Year 4 - Sec B"),
        ]
        
        # Trim the "        ]\n        " from current_list
        current_list = current_list.rstrip()
        if current_list.endswith(']'):
            current_list = current_list[:-1].rstrip()
            
        new_list_str = current_list + ",\n"
        
        for i, s in enumerate(new_students):
            new_list_str += f'            ("{s[0]}", "{s[1]}", "{s[2]}")'
            if i < len(new_students) - 1:
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
