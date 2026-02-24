import re
from typing import Dict, Any

class RegexCleaner:
    def parse_aadhaar(self, text: str, full_text_lines: list) -> Dict[str, Any]:
        data = {
            "document_type": "Aadhaar Card",
        }
        aadhaar_match = re.search(r"\b(\d{4}\s\d{4}\s\d{4})\b", text)
        if aadhaar_match:
            data["aadhaar_number"] = aadhaar_match.group(1)
            
        dob_match = re.search(r"\b(\d{2}[\/\-]\d{2}[\/\-]\d{4})\b", text)
        if dob_match:
            data["dob"] = dob_match.group(1).replace("/", "-")
            
        if "dob" not in data:
             yob_match = re.search(r"Year of Birth\s*[:\-]?\s*(\d{4})", text, re.IGNORECASE)
             if yob_match:
                 data["dob"] = f"{yob_match.group(1)}-01-01"
        
        if re.search(r"\b(Male|MALE)\b", text):
            data["gender"] = "Male"
        elif re.search(r"\b(Female|FEMALE)\b", text):
            data["gender"] = "Female"
            
        lines = [line.strip() for line in full_text_lines if line.strip()]
        for line in lines:
             if any(x in line.lower() for x in ["govt", "india", "unique", "authorit", "enrollment", "help", "www", "dob", "year", "male", "female"]):
                 continue
             if re.match(r"^[A-Z][a-z]+(\s[A-Z][a-z]+)+$", line) or re.match(r"^[A-Z\s]+$", line):
                 if len(line.split()) < 2: continue
                 data["name"] = line.title()
                 break
        return data

    def parse_pan(self, text: str, full_text_lines: list) -> Dict[str, Any]:
        data = {
            "document_type": "PAN Card",
        }
        pan_pattern = re.compile(r"[A-Z]{5}[0-9]{4}[A-Z]")
        pan_match = pan_pattern.search(text)
        if pan_match:
            data["pan_number"] = pan_match.group(0)

        dob_pattern = re.compile(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b")
        dob_match = dob_pattern.search(text)
        if dob_match:
            data["dob"] = dob_match.group(1).replace('/', '-')
        
        lines = [line.strip() for line in full_text_lines if line.strip()]
        found_name = False
        found_fname = False
        
        for i, line in enumerate(lines):
            if "Father" in line or "Mother" in line:
                if i + 1 < len(lines):
                    candidate = lines[i+1]
                    if not any(x in candidate for x in ["Number", "Card", "Signature", "Date", "DOB"]):
                         data["father_name"] = candidate
                         found_fname = True
                continue
            
            if "Name" in line and "Father" not in line and "Mother" not in line:
                if i + 1 < len(lines):
                    candidate = lines[i+1]
                    if not any(x in candidate for x in ["Number", "Card", "Father", "Mother"]):
                        data["name"] = candidate
                        found_name = True
        return data
        
    def extract_marksheet_details(self, text: str, lines: list) -> Dict[str, Any]:
        # Copied verbatim from previous extractor to prevent regressions
        data = {
            "document_type": "Marksheet",
            "university_name": "Unknown",
            "college_name": "Unknown",
            "student_name": "Unknown",
            "university_seat_number": "Unknown",
            "semester": "Unknown",
            "subjects": [],
            "semester_2": [], 
            "semester_1": [], 
            "remarks": {"P": "Pass", "F": "Fail", "A": "Absent", "W": "Withheld", "X": "Not Eligible"}
        }
        uni_match = re.search(r"(Visvesvaraya\s+Technological\s+University|VTU|Anna\s+University)", text, re.IGNORECASE)
        if uni_match:
            data["university_name"] = uni_match.group(1).title()
            
        usn_match = re.search(r"\b([1-4][A-Z]{2}\d{2}[A-Z]{2,6}\d{1,3})\b", text)
        if usn_match:
            data["university_seat_number"] = usn_match.group(1).upper()
            
        for line in lines:
            if "Name" in line and ":" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    clean_name = parts[1].strip()
                    if clean_name and not any(x in clean_name.lower() for x in ["usn", "semester", "result"]):
                        data["student_name"] = clean_name.title()
                        break

        all_semesters_map = {"1": [], "2": [], "3": [], "4": [], "5": [], "6": [], "7": [], "8": []}
        latest_sem = 0
        current_semester = None
        state = 'LOOKING_FOR_CODE'
        current_subject = {}
        name_buffer = []
        marks_buffer = []
        
        sem_header_pattern = re.compile(r"Semester\s*[:\-]?\s*(\d+)", re.IGNORECASE)
        code_pattern = re.compile(r"^[A-Z0-9]{5,8}$")
        
        for line in lines:
            clean_line = line.strip()
            if not clean_line: continue
            
            sem_match = sem_header_pattern.search(clean_line)
            if sem_match:
                sem_val = sem_match.group(1)
                current_semester = sem_val
                if int(sem_val) > latest_sem:
                    latest_sem = int(sem_val)
                state = 'LOOKING_FOR_CODE'
                current_subject = {}
                name_buffer = []
                marks_buffer = []
                continue

            if state == 'LOOKING_FOR_CODE':
                if "Code" in clean_line or "Subject" in clean_line: continue
                parts = clean_line.split()
                if len(parts) == 1 and code_pattern.match(parts[0]):
                    current_subject['subject_code'] = parts[0]
                    state = 'BUILDING_NAME'
                    name_buffer = []

            elif state == 'BUILDING_NAME':
                if clean_line.isdigit():
                    marks_buffer = [clean_line]
                    current_subject['subject_name'] = " ".join(name_buffer).strip()
                    state = 'LOOKING_FOR_MARKS'
                elif re.match(r"^\d+$", clean_line):
                     marks_buffer = [clean_line]
                     current_subject['subject_name'] = " ".join(name_buffer).strip()
                     state = 'LOOKING_FOR_MARKS'
                else:
                    if clean_line.lower() in ["internal", "external", "total", "result", "grade"]: continue
                    name_buffer.append(clean_line)
            
            elif state == 'LOOKING_FOR_MARKS':
                if clean_line.isdigit():
                    marks_buffer.append(clean_line)
                elif clean_line.upper() in ["A", "X", "-"]:
                     marks_buffer.append("0" if clean_line == "-" else clean_line)
                elif re.match(r"^[PFAWX]$", clean_line.upper()) or clean_line.upper() in ["PASS", "FAIL"]:
                     state = 'LOOKING_FOR_RESULT'
                     res = clean_line.upper()
                     if res in ["PASS", "FAIL"]: res = res[0]
                     
                     if len(marks_buffer) >= 3:
                        current_subject['internal_marks'] = marks_buffer[-3]
                        current_subject['external_marks'] = marks_buffer[-2]
                        current_subject['total'] = marks_buffer[-1]
                        current_subject['result'] = res
                        if current_semester: all_semesters_map.get(current_semester, []).append(current_subject)
                        state = 'LOOKING_FOR_CODE'
                        current_subject = {}
                        name_buffer = []
                        marks_buffer = []

            elif state == 'LOOKING_FOR_RESULT':
                res = clean_line.upper()
                if res in ["P", "F", "A", "W", "X", "PASS", "FAIL"]:
                    if res in ["PASS", "FAIL"]: res = res[0]
                    if len(marks_buffer) >= 3:
                        current_subject['internal_marks'] = marks_buffer[-3]
                        current_subject['external_marks'] = marks_buffer[-2]
                        current_subject['total'] = marks_buffer[-1]
                        current_subject['result'] = res
                        if current_semester: all_semesters_map.get(current_semester, []).append(current_subject)
                    state = 'LOOKING_FOR_CODE'
                    current_subject = {}
                    name_buffer = []
                    marks_buffer = []

        data["semester"] = str(latest_sem) if latest_sem > 0 else "Unknown"
        if latest_sem > 0:
            data["subjects"] = all_semesters_map.get(str(latest_sem), [])
            if int(latest_sem) > 1:
                sem_2 = all_semesters_map.get("2", [])
                if sem_2: data["semester_2"] = sem_2
                sem_1 = all_semesters_map.get("1", [])
                if sem_1: data["semester_1"] = sem_1
        return data

    def extract_document(self, raw_text: str, lines: list) -> Dict[str, Any]:
        """Tries to parse document parameters from arbitrary text. Returns dict of keys."""
        base_data = {}
        if re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", raw_text) or "MALE" in raw_text.upper() or "FEMALE" in raw_text.upper():
             if re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", raw_text):
                 base_data = self.parse_aadhaar(raw_text, lines)
        
        if not base_data.get("document_type") and re.search(r"[A-Z]{5}\d{4}[A-Z]", raw_text):
             base_data = self.parse_pan(raw_text, lines)
             
        if not base_data.get("document_type") and ( "UNIVERSITY" in raw_text.upper() or "MARKS" in raw_text.upper() or "RESULT" in raw_text.upper()):
             base_data = self.extract_marksheet_details(raw_text, lines)
        
        # Simple extraction for DL/Passport/VoterID logic would go here, falling back to Donut usually
        if not base_data.get("document_type"):
            base_data["document_type"] = "Unknown"
            
        return base_data
